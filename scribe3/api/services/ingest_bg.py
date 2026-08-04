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



# Note: function bodies resolve free names via rebound globals on app_impl.
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
    schema 已由端点侧 _store_for(work) 建好,此处不重复 apply。完成时(finally)清在途标记。"""
    import logging
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    # 审计 P1-6:ingest 结果状态落 chapter(ingest_status/ingest_error)——此前失败只写
    # 服务端日志,前端零感知,知识账本悄悄落后,后续章简报/限知帧全吃陈旧数据。
    def _mark(st0, status, err=""):
        try:
            st0._execute_write(
                "UPDATE type::thing('chapter',$seq) SET ingest_status=$st, ingest_error=$er",
                {"seq": seq, "st": status, "er": (err or "")[:200]})
        except Exception as me:
            logging.getLogger("scribe3").warning("ingest 状态落库失败(忽略): %s", me)

    st = None
    try:
        st = SurrealStore(ns="scribe3", db=work)
        r = ingest_chapter(st, seq, hermes_complete)
        if r.get("parse_failed"):
            logging.getLogger("scribe3").warning(
                "后台 ingest %s 第%s章: LLM 回复解析失败,既有知识已保留(未 purge)", work, seq)
            _mark(st, "parse_failed", "LLM 回复解析失败,知识账本未更新")
        else:
            _refresh_scorecard_after_ingest(st, seq)   # P2-3:主链路 ingest 后哨兵转真值
            _mark(st, "ok")
        # 北极星任务8:后台 ingest 完成后同样触发复盘蒸馏(fail-soft)。
        try:
            from scribe3.lesson import distill_chapter
            distill_chapter(st, seq, hermes_complete)
        except Exception as e:
            logging.getLogger("scribe3").error("后台 ingest 复盘蒸馏失败 %s 第%s章", work, seq, exc_info=True)   # U-011: 教训静默没记,后台无响应面→至少 error 级日志
    except Exception as e:
        logging.getLogger("scribe3").error("后台 ingest %s 第%s章失败", work, seq, exc_info=True)   # U-011
        if st is not None:
            _mark(st, "failed", str(e))
    finally:
        with _pending_ingest_lock:
            _pending_ingest.discard((work, seq))
        if st is not None:
            try:
                st.close()
            except Exception as ce:
                logging.getLogger("scribe3").warning(
                    "后台 ingest 独立连接关闭失败 %s 第%s章: %s", work, seq, ce)


def _enqueue_ingest(background: BackgroundTasks, work: str, seq: int) -> bool:
    """排后台 ingest,同章去重(P0-1 竞态根治):同 (work,seq) 已在途/在排 → 跳过第二次排队。
    谁先排谁负责,第二个跳过——这样"存为正文"的 save-chapter + checkpoint(final) 双触发
    只会真正跑一次 ingest。返回是否真正排入(在途标记随 _bg_ingest 完成时清除)。"""
    key = (work, seq)
    with _pending_ingest_lock:
        if key in _pending_ingest:
            return False
        _pending_ingest.add(key)
    background.add_task(_bg_ingest, work, seq)
    return True


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

