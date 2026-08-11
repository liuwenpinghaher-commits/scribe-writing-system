"""Service helpers extracted from app_impl (architecture split Phase B).

Runtime: ``app_impl._rebind_services()`` rebinds each public function into
``app_impl`` globals (monkeypatch / router rebind).  Do not call these for
side-effectful paths without going through ``scribe3.app`` / ``app_impl``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict, deque
from functools import wraps
from typing import Any, Optional

from fastapi import (
    APIRouter, BackgroundTasks, File, Form, HTTPException, Query, Request,
    UploadFile, Body, Header, Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator


# 进程内在途集合：模块自持；生产路径优先对齐 app_impl 同名集合（rebind 后单源）。
_pending_ingest: set[tuple[str, int]] = set()
_pending_ingest_lock = threading.Lock()


def _pending_pair():
    """返回 (set, lock)；优先 app_impl 全局，避免双集合去重失效。"""
    try:
        from scribe3.api import app_impl as _A
        s = getattr(_A, "_pending_ingest", None)
        lk = getattr(_A, "_pending_ingest_lock", None)
        if s is not None and lk is not None:
            return s, lk
    except Exception:
        pass
    return _pending_ingest, _pending_ingest_lock


# Note: function bodies resolve free names via rebound globals on app_impl.
def mark_chapter_ingest_status(
    st, seq: int, status: str, err: str = "", *, prose_fp: str | None = None,
) -> None:
    """单源:落 chapter.ingest_status / ingest_error(KR3 诚实回写)。

    同步 /ingest、后台 _bg_ingest、loop finalize、统一终选 apply 共用。
    status=ok 且传 prose_fp 时一并写入 ingest_prose_fp，供同正文跳过二次 purge。
    """
    import logging
    try:
        if prose_fp and status == "ok":
            try:
                st._execute_write(
                    "UPDATE type::record('chapter',$seq) SET "
                    "ingest_status=$st, ingest_error=$er, ingest_prose_fp=$fp",
                    {"seq": int(seq), "st": status, "er": (err or "")[:200], "fp": prose_fp[:32]},
                )
                return
            except Exception:
                # 老库无字段：先 DEFINE 再写
                try:
                    st._raw_query(
                        "DEFINE FIELD IF NOT EXISTS ingest_prose_fp ON chapter TYPE option<string>;"
                    )
                    st._execute_write(
                        "UPDATE type::record('chapter',$seq) SET "
                        "ingest_status=$st, ingest_error=$er, ingest_prose_fp=$fp",
                        {"seq": int(seq), "st": status, "er": (err or "")[:200], "fp": prose_fp[:32]},
                    )
                    return
                except Exception:
                    pass
        st._execute_write(
            "UPDATE type::record('chapter',$seq) SET ingest_status=$st, ingest_error=$er",
            {"seq": int(seq), "st": status, "er": (err or "")[:200]})
    except Exception as me:
        logging.getLogger("scribe3").warning(
            "ingest 状态落库失败(忽略) seq=%s status=%s: %s", seq, status, me)


def _refresh_scorecard_after_ingest(st, seq: int) -> None:
    """ingest 后刷新章 scorecard 与质量缓存(P0门审查 P2-3,单源供 /ingest、_bg_ingest、loop 共用):
    存稿时快照没有本章事件,qc_causal 停在 -1 哨兵;反哺落库后重算出真值。
    fail-soft:刷新失败只告警,不影响 ingest 结果。"""
    try:
        st.refresh_chapter_cache(seq)
        ch = st.get_chapter(seq) or {}
        prose = ch.get("prose") or ""
        if prose.strip():
            st._upsert_scorecard(st._compute_scorecard(seq, prose, ch.get("focalizer")))
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning(
            "ingest 后 scorecard 刷新失败(忽略) seq=%s: %s", seq, e)


def _bg_ingest(work: str, seq: int) -> None:
    """后台客观回写:开**独立** store 连接跑 ingest_chapter(P2-3:不复用 _store_for 的共享 ws,
    避免多后台任务跨线程交错同一连接)。异常只记日志,不影响存稿(non-fatal)。
    schema 已由端点侧 _store_for(work) 建好,此处不重复 apply。完成时(finally)清在途标记。

    PR-1: worker 侧再占共享 ingest lease,防 MCP 同步 ingest ∥ HTTP 后台双 purge。
    """
    import logging
    from scribe3.ingest import ingest_chapter
    from scribe3.ingest_lease import (
        combined_backend, new_owner, try_acquire_ingest_lease, release_ingest_lease,
    )
    from scribe3.llm import hermes_complete
    # 审计 P1-6:ingest 结果状态落 chapter——单源 mark_chapter_ingest_status
    # (同步 /ingest 同路径,防 retry 成功后 status 仍 failed、UI 角标永不消)。
    st = None
    owner = ""
    backend = None
    try:
        st = SurrealStore(ns="scribe3", db=work)
        backend = combined_backend(st)
        owner = new_owner()
        acq = try_acquire_ingest_lease(backend, work, int(seq), owner, ttl=600.0)
        if not acq.ok:
            logging.getLogger("scribe3").info(
                "后台 ingest %s 第%s章: lease_busy owner=%s", work, seq, acq.owner)
            return
        r = ingest_chapter(
            st, seq, hermes_complete, work=work,
            lease_owner=owner, lease_backend=backend,
        )
        if r.get("skipped"):
            # 终选 unified 已 apply+钉指纹:跳过 scorecard/distill 二次开销
            # 或 lease_lost_before_purge
            logging.getLogger("scribe3").info(
                "后台 ingest %s 第%s章: skip %s", work, seq, r.get("reason") or "same_prose_fp")
        elif r.get("parse_failed"):
            logging.getLogger("scribe3").warning(
                "后台 ingest %s 第%s章: LLM 回复解析失败,既有知识已保留(未 purge)", work, seq)
            mark_chapter_ingest_status(st, seq, "parse_failed",
                                       "LLM 回复解析失败,知识账本未更新")
        else:
            _refresh_scorecard_after_ingest(st, seq)   # P2-3:主链路 ingest 后哨兵转真值
            mark_chapter_ingest_status(
                st, seq, "ok", prose_fp=r.get("prose_fp") or None)
            # 北极星任务8:仅真实 apply 后蒸馏(skip 已由终选/前次路径覆盖)
            try:
                from scribe3.lesson import distill_chapter
                distill_chapter(st, seq, hermes_complete)
            except Exception as e:
                logging.getLogger("scribe3").error(
                    "后台 ingest 复盘蒸馏失败 %s 第%s章", work, seq, exc_info=True)   # U-011
    except Exception as e:
        logging.getLogger("scribe3").error("后台 ingest %s 第%s章失败", work, seq, exc_info=True)   # U-011
        if st is not None:
            mark_chapter_ingest_status(st, seq, "failed", str(e))
    finally:
        if backend is not None and owner:
            try:
                release_ingest_lease(backend, work, int(seq), owner)
            except Exception:
                pass
        pend, plock = _pending_pair()
        with plock:
            pend.discard((work, seq))
        try:
            from scribe3.chapter_lock import release_chapter_lock
            release_chapter_lock("ingest", work, int(seq))
        except Exception:
            pass
        if st is not None:
            try:
                st.close()
            except Exception as ce:
                logging.getLogger("scribe3").warning(
                    "后台 ingest 独立连接关闭失败 %s 第%s章: %s", work, seq, ce)


def _enqueue_ingest_raw(background: BackgroundTasks, work: str, seq: int) -> bool:
    """底层排队：统一 chapter_lock(ingest) + 进程内去重 set + BackgroundTasks。

    策略层请走 schedule_ingest。锁失败 → 视为已在途（False）。
    """
    key = (work, seq)
    # P2 residual：ingest 与 loop/repair 同一 chapter_lock 表面
    try:
        from scribe3.chapter_lock import acquire_chapter_lock
        clr = acquire_chapter_lock("ingest", work, int(seq))
        if not clr.ok:
            return False
    except Exception:
        pass
    pend, plock = _pending_pair()
    with plock:
        if key in pend:
            try:
                from scribe3.chapter_lock import release_chapter_lock
                release_chapter_lock("ingest", work, int(seq))
            except Exception:
                pass
            return False
        pend.add(key)
    background.add_task(_bg_ingest, work, seq)
    return True


def _enqueue_ingest(background: BackgroundTasks, work: str, seq: int) -> bool:
    """兼容入口：无 gate 时默认 pass 自动入队（旧调用方）。

    新路径请用 schedule_ingest(..., gate=...)。
    """
    return _enqueue_ingest_raw(background, work, seq)


def schedule_ingest(
    st,
    work: str,
    seq: int,
    *,
    background: BackgroundTasks | None = None,
    prose: str = "",
    gate=None,
    force: bool = False,
    source: str = "save",
    mode: str = "bg",
    confirm_token: str | None = None,
    complete_fn=None,
    max_attempts: int = 3,
    distill: bool = True,
) -> dict:
    """生产单入口（设计 run_or_enqueue）。"""
    from scribe3.ingest_policy import run_or_enqueue
    return run_or_enqueue(
        st, work, int(seq),
        mode="sync" if mode == "sync" else "bg",
        background=background,
        gate=gate,
        prose=prose,
        force=force,
        source=source,
        confirm_token=confirm_token,
        complete_fn=complete_fn,
        max_attempts=max_attempts,
        distill=distill,
    )


def _semantic_repair_violations(prose: str, quality: dict, leaks: list, discipline: dict) -> list[str]:
    """仅让与确定性证据共振的纪律标签触发整章覆写。

    LLM 单判是建议而非可逆性很低的写稿命令：这与 /post-check 的 S1 共振规则保持一致。
    无确定性对应物的 double_climax/voice_collapse 保留给作者审阅，不能据此自动改写整章。
    """
    from scribe3.critique import find_god_view
    raw = discipline.get("violations") or []
    god_kinds = {h.get("kind") for h in find_god_view(prose)}
    actionable: list[str] = []
    for violation in raw:
        if violation == "knowledge_leak" and leaks:
            actionable.append(violation)
        elif violation == "god_view" and god_kinds & {"god_spoiler", "explain_causality"}:
            actionable.append(violation)
        elif violation == "exposition_dump" and (quality.get("oversaturation") or 0) > 0:
            actionable.append(violation)
    return actionable


def _prose_stats(prose: str) -> dict:
    """轻量正文统计:{words, avg_sentence, dialog_count}。纯确定性,不打 LLM。
    - words:去空白字符数(同 save_chapter 的字数口径)。
    - avg_sentence:按句末标点切句的平均句长(字符)。
    - dialog_count:含引号的行/句计为对白(粗略,够前端展示)。"""
    import re
    words = len("".join((prose or "").split()))
    sentences = [s for s in re.split(r"[。！？!?…]+", prose or "") if s.strip()]
    avg_sentence = round(words / len(sentences), 1) if sentences else 0
    dialog_count = len(re.findall(r"[“「『][^”」』]*[”」』]", prose or ""))
    return {"words": words, "avg_sentence": avg_sentence, "dialog_count": dialog_count}

