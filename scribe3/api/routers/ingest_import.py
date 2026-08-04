"""Domain router (extracted from app_impl). URLs unchanged."""
from __future__ import annotations

import logging

import types
from typing import Any, Optional, List, Dict, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    Body,
    Header,
    Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

router = APIRouter(tags=['ingest_import'])


# Import app_impl constants/models used as signature defaults (late-safe for helpers).
def _import_core_defaults():
    from scribe3.api import app_impl as core
    g = globals()
    for k, v in core.__dict__.items():
        if k.startswith('__'):
            continue
        if k not in g:
            g[k] = v
try:
    _import_core_defaults()
except Exception:
    pass  # core may be partially init during first import cycle


def author_session_clip_ep(m: SessionClipIn, work: str = "main"):
    """作者私人剪藏 → 非正典素材。

    不经 REST 世界写闸(路径不在前缀清单)、不经主编 MCP 审批。
    仅允许 kind∈{snippet,note}；origin=session_clip。
    """
    body = (m.body or "").strip()
    if not body:
        raise HTTPException(status_code=422, detail="body required")
    if len(body) > 4000:
        body = body[:4000] + "…"
    kind = (m.kind or "snippet").strip()
    if kind not in _SESSION_CLIP_KINDS:
        kind = "snippet"
    title = (m.title or "").strip()
    if not title:
        one = " ".join(body.split())
        title = one if len(one) <= 48 else one[:47] + "…"
    source = (m.source or "").strip()
    if not source:
        origin_label = (m.origin_label or "选区摘录").strip() or "选区摘录"
        ch = f" · 第{m.chapter_seq}章" if m.chapter_seq is not None else ""
        scope = f" · {m.scope_label.strip()}" if (m.scope_label or "").strip() else ""
        source = f"会话摘录 · {origin_label}{ch}{scope}"
    mid = _store_for(work).add_material(
        title, body, kind, [], source,
        ref_tags=list(m.ref_tags or []), summary=m.summary,
        origin="session_clip")
    return {"ok": True, "id": mid, "title": title, "kind": kind, "source": source,
            "origin": "session_clip"}

def ingest(seq: int, work: str = "main"):
    """手动反哺设定库(前端"反哺设定库"按钮),同步跑 ingest_chapter。
    P0-1 收尾:纳入 _pending_ingest 去重护栏——与后台 _bg_ingest/_enqueue_ingest
    共用同一 (work,seq) 在途集合。同章已有 ingest 在途(后台自动或另一次手点)时拒 409,
    防手点反哺撞自动 ingest 交错造成 knows/reader_knows/char_state/motif_instance/
    promise_touch 双份或互删。自身执行期间也占位在途,故并发 _enqueue_ingest 同章会被跳过;
    完成/异常均在 finally 清标记(避免该章永久锁死)。"""
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    key = (work, seq)
    with _pending_ingest_lock:
        if key in _pending_ingest:
            raise HTTPException(status_code=409, detail="该章正在反哺中,请稍候再试")
        _pending_ingest.add(key)
    try:
        st = _store_for(work)
        r = ingest_chapter(st, seq, hermes_complete)
        if not r.get("parse_failed"):
            # 北极星任务6:手动链路结构类结算(认知类留面板人工;loop 链有完整结算)。
            # settle 在 scorecard 刷新之前——刷新要读结算后的 deltas 状态。
            try:
                from scribe3.purpose import (check_fulfillment_structural,
                                             parse_deltas, settle_purpose)
                _ds = parse_deltas((st.get_chapter(seq) or {}).get("deltas"))
                if _ds:
                    settle_purpose(st, seq, check_fulfillment_structural(st, seq, _ds))
            except Exception as e:
                logging.getLogger("scribe3").warning("/ingest 目的合同结算失败(忽略): %s", e)
            _refresh_scorecard_after_ingest(st, seq)   # P2-3:主链路 ingest 后哨兵转真值
        # 北极星任务8:章后复盘蒸馏(事件驱动挂 ingest 路径,蓝图定死不走 cron)——
        # 与知识抽取成败无关(对话的方法教训独立于 parse_failed);fail-soft 绝不拖垮 ingest。
        try:
            from scribe3.lesson import distill_chapter
            _dfn = _complete_fn
            if _dfn is None:
                from scribe3.llm import hermes_complete as _dfn
            distill_chapter(st, seq, _dfn)
        except Exception as e:
            # U-011:蒸馏失败不 raise(正文已落),但放进响应 lesson_error 让作者看见"这章教训没记住"。
            logging.getLogger("scribe3").error("/ingest 复盘蒸馏失败 seq=%s", seq, exc_info=True)
            if isinstance(r, dict):
                r["lesson_error"] = str(e)[:120]
        return r
    finally:
        with _pending_ingest_lock:
            _pending_ingest.discard(key)

def story_import(req: ImportReq, work: str = "main"):
    """story-import 逆向导入(方案B任务24,P3 战略):作者贴已发布章节 → 逐章复用现有单章
    逆向内核 ingest_chapter 反推知识账本(角色关系/伏笔触及/弧光/事件),免人工重建 bible
    即可从下一章无缝续写。

    ①逐章按 seq 升序存正文(save_chapter)+ 走 ingest_chapter(grep-back 自检已内置在
      ingest_chapter 里,自动生效,这里不重复做)。
    ②用 PipelineJournal(见 pipeline_journal.py)包裹每章:stage=f"import_ch{seq}",
      journal 文件路径见 _import_journal_path;should_skip 使已完成章在进程崩溃重启/
      重复调用本端点时被跳过,故本端点整体幂等可重入。
    ③crash-safe 取舍:某章 ingest 失败(抛异常或 parse_failed)不会"跳过继续下一章"——
      按 journal 协议,一个 Stage 中途失败视为整体没跑通,不 complete_stage,立即中止
      循环。响应选 200 + error 字段而非 4xx:失败时已完成的 imported/skipped/resume_from
      仍是调用方需要的有效进度信息,4xx 容易被调用方整体丢弃响应体,丢失这份进度。
    ④五锚逆向(build_reverse_anchor_prompt/parse_reverse_anchors,ingest.py)刻意不在这里
      接线——对每个主要角色同步串行调一次 LLM 会显著拖慢本端点,留作 import 完成后的
      可选异步步骤(TODO:后续任务按 delta 里出现过的角色排队后台调用)。
    ⑤Minor(收尾清理批):正文 save_chapter 先于知识抽取(ingest_chapter)落库,
      失败重跑会覆写该章正文(幂等覆盖)——journal 保护的是"跳过已完成章",
      不是"正文不被重写"。
    """
    from scribe3.ingest import ingest_chapter
    from scribe3.pipeline_journal import PipelineJournal

    st = _store_for(work)
    complete_fn = _complete_fn
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete

    journal = PipelineJournal(_import_journal_path(work))
    chapters = sorted(req.chapters, key=lambda c: c.seq)

    def _open_promises():
        return [p for p in st.promises_with_lifecycle() if p["status"] == "open"]

    imported = 0
    skipped = 0
    annotated_total = 0
    max_seq = 0
    for item in chapters:
        stage = f"import_ch{item.seq}"
        if journal.should_skip(stage):
            skipped += 1
            max_seq = max(max_seq, item.seq)
            continue
        journal.start_stage(stage)
        st.save_chapter(item.seq, item.prose)
        try:
            result = ingest_chapter(st, item.seq, complete_fn)
        except Exception as e:
            # 中途崩溃:journal 保持 in_progress=stage,不 complete——下次重跑本端点会
            # 从这一章重新整章跑(should_skip 对未 complete 的 stage 恒返回 False)。
            return {"imported": imported, "skipped": skipped, "resume_from": item.seq,
                    "open_promises": _open_promises(), "annotated_total": annotated_total,
                    "error": f"第 {item.seq} 章 ingest 抛异常,已中止:{e}"}
        if result.get("parse_failed"):
            return {"imported": imported, "skipped": skipped, "resume_from": item.seq,
                    "open_promises": _open_promises(), "annotated_total": annotated_total,
                    "error": f"第 {item.seq} 章知识抽取解析失败(parse_failed),已中止"}
        journal.complete_stage(stage)
        imported += 1
        annotated_total += len(result.get("annotated") or [])
        max_seq = max(max_seq, item.seq)

    return {"imported": imported, "skipped": skipped, "resume_from": max_seq + 1,
            "open_promises": _open_promises(), "annotated_total": annotated_total}

def ingest_unverified(status: str = "pending", work: str = "main"):
    return _store_for(work).list_unverified(status)

def accept_unverified_ep(uid: str, background: BackgroundTasks, work: str = "main"):
    """接受待确认角色后立即返回；重放本章知识抽取由既有后台队列完成。

    角色建立与人工裁决是作者当前操作，必须在本次请求内完成；`ingest_chapter` 会请求
    LLM，若同步执行会让“接受”按钮长时间卡住，还会把网络/模型故障伪装成裁决失败。
    先记下 pending 行对应章节，再无 LLM 地接受，最后复用 `_enqueue_ingest` 的同章去重
    护栏安排异步回填。`replay_queued=False` 代表该条不存在、无章节或该章已有回填在途。
    """
    st = _store_for(work)
    row = next((item for item in st.list_unverified("pending") if item.get("id") == uid), None)
    result = st.accept_unverified(uid)
    seq = (row or {}).get("seq")
    replay_queued = _enqueue_ingest(background, work, int(seq)) if seq is not None else False
    return {**result, "replay_queued": replay_queued}

def ignore_unverified_ep(uid: str, work: str = "main"):
    _store_for(work).ignore_unverified(uid)
    return {"ok": True}

def ignore_all_unverified_ep(status: str = "pending", work: str = "main"):
    """R2-12:批量忽略——unverified 死水(产生速率≫消化)一键清账,防账本失信号价值。
    只清指定 status(默认 pending);accepted/ignored 的决策存活是设计。"""
    st = _store_for(work)
    n = 0
    for r in st.list_unverified(status):
        try:
            st.ignore_unverified(r.get("id"))
            n += 1
        except Exception:
            pass
    return {"ignored": n}

def audit_blind_pack(work: str = "main", sample_n: int = 2, seed: int = 0,
                     per_volume: int | None = None):
    """盲评包导出(北极星任务13,秘密审计制度——防 Goodhart 的流程性防护):
    池A=被自动 regenerate 的章(loop journal 含 *_verdict_blocking,附第0稿并排、
    随机左右序,审「重写后真的更好吗」);池B=随机抽样章(seed 可复现)。
    sample_n 是**全书总抽样数**(P2门审查 P2-4:旧名 per_volume 语义失实,制度 doc
    的"每卷 2-3 章"由作者按卷分次导出或 sample_n=卷数×2 执行;旧参名兼容保留)。
    样本用盲号(不含章号;池A样本带双稿形态,天然暴露"回炉过"池别——制度 doc 已
    明示此偏离)。key 补 regen_rounds(回炉轮数,journal 计)。结论只供人读,
    **永不接入任何自动收敛判据**(宪法级);read-only 端点。"""
    if per_volume is not None:
        sample_n = per_volume
    import glob as _glob
    import json as _json
    import random
    import re as _re_mod
    _re_audit = _re_mod.compile(r"_a(\d+)_")
    st = _store_for(work)
    base = (os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR")
            or os.path.expanduser("~/.scribe3-loop-journals"))
    pool_a: set[int] = set()
    pool_a2: set[int] = set()   # 2-A:needs_human 章(三稿全拦)——检测器假阳性富矿
    regen_rounds: dict[int, int] = {}   # P2门审查 P2-4:key 补回炉轮数(制度 doc 承诺)
    blocking_dist: dict[int, dict] = {}   # 2-A:拦截原因分布(detector 计数,来自 .result.json)
    for fp in _glob.glob(os.path.join(base, work, "loop_ch*.json")):
        try:
            with open(fp, encoding="utf-8") as _fh:
                data = _json.loads(_fh.read())
            stages = data.get("stages_completed") or []
            seq_a = int(os.path.basename(fp).split("_")[1][2:])
            if any("_needs_human" in s for s in stages):
                pool_a2.add(seq_a)
            elif any("_verdict_blocking" in s for s in stages):
                pool_a.add(seq_a)
            else:
                continue
            attempts = [int(m.group(1)) for s in stages
                        for m in [_re_audit.search(s)] if m]
            regen_rounds[seq_a] = max(regen_rounds.get(seq_a, 0), max(attempts, default=0))
            try:   # 1-C#2 的旁文件有则读 detector 分布(旧 journal 没有,None 即如实)
                with open(fp + ".result.json", encoding="utf-8") as _fh2:
                    rj = _json.loads(_fh2.read())
                _cnt: dict[str, int] = {}
                for _r0 in rj.get("rounds") or []:
                    for _b in _r0.get("blocking") or []:
                        _d = str(_b.get("detector") or "?")
                        _cnt[_d] = _cnt.get(_d, 0) + 1
                if _cnt:
                    blocking_dist[seq_a] = _cnt
            except Exception:
                pass
        except Exception:
            continue
    pool_a -= pool_a2   # 同章多 journal 时 needs_human 语义优先(A 的"重写后过审"对照不成立)
    chapters = [c["seq"] for c in st.list_chapters()]
    rng = random.Random(seed)
    rest = [c for c in chapters if c not in pool_a and c not in pool_a2]
    pool_b = sorted(rng.sample(rest, min(sample_n, len(rest)))) if rest else []
    # 池A2 不要求章已落库正文(needs_human 章 prose 不落库,三稿在版本库)
    picked = ([("A", s) for s in sorted(pool_a) if s in chapters]
              + [("A2", s) for s in sorted(pool_a2)]
              + [("B", s) for s in pool_b])
    rng.shuffle(picked)
    samples, key = [], {}
    for i, (pool, seq) in enumerate(picked):
        blind_id = f"S{seed}-{i + 1:02d}"
        ch = st.get_chapter(seq) or {}
        item = {"blind_id": blind_id, "prose": ch.get("prose") or "",
                "questions": ["张力:想继续读下一章吗(1-5)?",
                              "声音:遮住人名还认得出这本书吗(1-5)?",
                              "记忆点:24 小时后还记得哪个画面?",
                              "违和:有没有机器味/被打磨过头的段落(引原文)?"]}
        if pool == "A":
            vers = [v for v in (st.list_chapter_versions(seq) or [])
                    if "loop第0稿" in (v.get("label") or "")]
            if vers:
                raw = (st.get_chapter_version(vers[0]["id"]) or {}).get("prose") or ""
                pair = [item["prose"], raw]
                rng.shuffle(pair)   # 随机左右序防位置偏置(Arena 先例)
                item["pair"] = [{"tag": f"稿{'甲乙'[k]}", "prose": p}
                                for k, p in enumerate(pair)]
                item["pair_question"] = "两稿哪份更好?自动重写是否磨掉了好东西?"
                item.pop("prose")
        elif pool == "A2":
            # 2-A:needs_human 章三稿并排(正文未落库,稿全在版本库 loop第N稿)。
            # 按轮次序不随机——A2 审的是「检测器拦得对不对」,轮次演进本身是证据
            # (自定口径,记 D-025);位置偏置防护留给池A的优劣对比场景。
            # 版本库可能存多轮 loop 的稿(label 无 run id);list_chapter_versions 新→旧,
            # 顺扫遇到重复 attempt 号即越过组边界——只取最新一组(needs_human 那次)。
            _re_draft_n = _re_mod.compile(r"loop第(\d+)稿")
            _cand, _seen_n = [], set()
            for v in (st.list_chapter_versions(seq) or []):
                _m = _re_draft_n.search(v.get("label") or "")
                if not _m:
                    continue
                _n = int(_m.group(1))
                if _n in _seen_n:
                    break
                _seen_n.add(_n)
                _cand.append((_n, v))
            _cand.sort(key=lambda t: t[0])
            item["triple"] = [
                {"tag": f"第{n}稿",
                 "prose": (st.get_chapter_version(v["id"]) or {}).get("prose") or ""}
                for n, v in _cand]
            item["triple_question"] = ("这几稿真的都不行吗?有可用稿即说明检测器过严,"
                                       "引原文说明哪一稿哪一段其实成立。")
            item.pop("prose")   # needs_human 正文未落库,不出空 prose 误导评审
        samples.append(item)
        try:
            sc = st.get_chapter_scorecard(seq) or {}
        except Exception:
            sc = {}
        key[blind_id] = {"chapter": seq, "pool": pool,
                         "regen_rounds": regen_rounds.get(seq),
                         "blocking_dist": blocking_dist.get(seq),   # 2-A:拦截原因分布
                         "ai_grade": ((sc.get("advisory_scores") or {}).get("ai_grade")
                                      or {}).get("grade"),
                         "constraints": sc.get("constraints")}
    return {"samples": samples, "key": key,
            "note": "评审时勿看 key;结论写人工文档,永不接入任何自动收敛判据(宪法)"}



def ingest_status(seq: int | None = None, work: str = "main"):
    """章 ingest 状态查询(KR3):成功/失败/解析失败可区分;失败不可伪装成功。

    - 无 seq:返回本书所有有 ingest_status 或 pending 在途的章摘要 + 失败 backlog
    - 有 seq:单章详情(含 pending 在途)
    行语义单源:finalize_gate.build_ingest_status_row
    """
    from scribe3.finalize_gate import build_ingest_status_row
    st = _store_for(work)
    pending: set = set()
    try:
        with _pending_ingest_lock:
            pending = {s for (w, s) in _pending_ingest if w == work}
    except Exception:
        pending = set()

    if seq is not None:
        ch = st.get_chapter(int(seq)) or {}
        return build_ingest_status_row(int(seq), ch, pending=(int(seq) in pending))

    rows = []
    try:
        for c in (st.chapters_lite() if hasattr(st, "chapters_lite") else st.list_chapters()) or []:
            s = c.get("seq")
            if s is None:
                continue
            full = st.get_chapter(int(s)) or c
            r = build_ingest_status_row(int(s), full, pending=(int(s) in pending))
            # 列表只保留有信号的章(状态/在途/失败),避免空书噪声
            if r["ingest_status"] not in (None, "unknown") or r["pending"]:
                rows.append(r)
            elif full.get("prose"):
                # 有正文但从未 ingest 标记 → unknown,纳入 backlog 观察
                if r["ingest_status"] == "unknown":
                    rows.append(r)
    except Exception as e:
        logging.getLogger("scribe3").warning("ingest_status 列表失败: %s", e)
    failed = [r for r in rows if r.get("failed")]
    return {
        "work": work,
        "chapters": rows,
        "failed_backlog": failed,
        "failed_count": len(failed),
        "pending_count": sum(1 for r in rows if r.get("pending")),
    }


def ingest_retry(seq: int, background: BackgroundTasks, work: str = "main"):
    """失败/未知 ingest 的显式重试(KR3):复用手动 /ingest 同步路径。

    在途 → 409;成功路径与 /ingest 相同(不把失败标成成功)。
    """
    st = _store_for(work)
    ch = st.get_chapter(seq) or {}
    if not (ch.get("prose") or "").strip():
        raise HTTPException(status_code=404, detail="chapter empty or missing")
    # 同步重试(与手点反哺同路径),保证响应含真实结果
    return ingest(seq, work=work)


def volume_review(volume_id: str | None = None, seq_from: int | None = None,
                  seq_to: int | None = None, work: str = "main"):
    """卷级伏笔超期 + 母题无回声信号(KR4,只读,无总分)。"""
    from scribe3.volume_signals import store_volume_review
    return store_volume_review(
        _store_for(work), volume_id=volume_id, seq_from=seq_from, seq_to=seq_to)


def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['author_session_clip_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'author_session_clip_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'author_session_clip_ep', _re)
    g['author_session_clip_ep'] = _re
    router.add_api_route('/author/session-clips', _re, methods=['POST'], name='author_session_clip_ep')

    _fn = g['ingest']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ingest', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ingest', _re)
    g['ingest'] = _re
    router.add_api_route('/ingest', _re, methods=['POST'], name='ingest')

    _fn = g['story_import']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'story_import', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'story_import', _re)
    g['story_import'] = _re
    router.add_api_route('/import', _re, methods=['POST'], name='story_import')

    _fn = g['ingest_unverified']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ingest_unverified', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ingest_unverified', _re)
    g['ingest_unverified'] = _re
    router.add_api_route('/ingest-unverified', _re, methods=['GET'], name='ingest_unverified')

    _fn = g['accept_unverified_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'accept_unverified_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'accept_unverified_ep', _re)
    g['accept_unverified_ep'] = _re
    router.add_api_route('/ingest-unverified/{uid}/accept', _re, methods=['POST'], name='accept_unverified_ep')

    _fn = g['ignore_unverified_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ignore_unverified_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ignore_unverified_ep', _re)
    g['ignore_unverified_ep'] = _re
    router.add_api_route('/ingest-unverified/{uid}/ignore', _re, methods=['POST'], name='ignore_unverified_ep')

    _fn = g['ignore_all_unverified_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ignore_all_unverified_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ignore_all_unverified_ep', _re)
    g['ignore_all_unverified_ep'] = _re
    router.add_api_route('/ingest-unverified/ignore-all', _re, methods=['POST'], name='ignore_all_unverified_ep')

    _fn = g['audit_blind_pack']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'audit_blind_pack', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'audit_blind_pack', _re)
    g['audit_blind_pack'] = _re
    router.add_api_route('/audit/blind-pack', _re, methods=['GET'], name='audit_blind_pack')

    _fn = g['ingest_status']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ingest_status', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ingest_status', _re)
    g['ingest_status'] = _re
    router.add_api_route('/ingest/status', _re, methods=['GET'], name='ingest_status')

    _fn = g['ingest_retry']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ingest_retry', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ingest_retry', _re)
    g['ingest_retry'] = _re
    router.add_api_route('/ingest/{seq}/retry', _re, methods=['POST'], name='ingest_retry')

    _fn = g['volume_review']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'volume_review', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'volume_review', _re)
    g['volume_review'] = _re
    router.add_api_route('/volume/review', _re, methods=['GET'], name='volume_review')

_bind_and_register()
