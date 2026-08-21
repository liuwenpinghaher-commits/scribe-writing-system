"""Service helpers extracted from app_impl (architecture split).

Rebound into ``app_impl`` globals via ``_rebind_services()`` for monkeypatch.
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
from queue import Empty, Full, Queue
from typing import Any, Optional

from fastapi import (
    APIRouter, BackgroundTasks, File, Form, HTTPException, Query, Request,
    UploadFile, Body, Header, Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator


def _resolve_thread_or_raise(work: str, thread: str | None):
    """P0a 零降级:thread 传了必须有效——不存在 404 / 已归档 409 / 跨 work 409。
    绝不静默回落 active(回落=串台掩盖器,作者定案「不要降级逻辑」)。
    返回线程行;未传返回 None(调用方走 active 默认,文档化参数默认非降级)。"""
    if not thread:
        return None
    _assert_work_binding(_thread_work(thread), work,
                         kind="editorial_thread", ident=thread)
    row = _store_for(work)._get_editorial_thread(thread)
    if row is None:
        raise HTTPException(status_code=404, detail={
            "code": "thread_not_found", "message": f"线程 '{thread}' 不存在"})
    if row.get("status") == "archived":
        raise HTTPException(status_code=409, detail={
            "code": "thread_archived",
            "message": "会话已归档,恢复(PATCH status=active)后再用"})
    return row


def _editor_turn_context(work: str, actor_id: str = "author",
                         thread_row: dict | None = None):
    """组装本轮主编 turn 的会话连续上下文(Task 11 产出 HermesTurnContext)。

    thread_id 取本 work 的稳定主编线程(get_or_create_editorial_thread,一 work 一连续线程);
    P0a:thread_row 给定(作者在下拉选了会话)时用该线程,跳过 get_or_create。
    conversation/previous_response 从线程行取(Hermes 会话续接锚,LRU 100 掉链常态);
    context_* 属动态 envelope 层(默认关),此处留空,开启后由 assembler 填。
    U-011:线程取数异常直接抛(fail-loud)——退化线程会让留痕落错处+历史读不到=静默失忆。"""
    from scribe3.hermes_runtime import HermesTurnContext
    w = _normalize_work(work)
    try:
        thread = thread_row or _store_for(w).get_or_create_editorial_thread(w, actor_id)
        return HermesTurnContext(
            work=w,
            thread_id=thread["thread_id"],
            conversation_id=thread.get("hermes_conversation_id") or None,
            previous_response_id=thread.get("previous_response_id") or None,
        )
    except Exception:
        # U-011(作者要 fail-loud):删"退化为 work 兜底线程"——退化后留痕落错线程、历史读不到,
        # 主编静默失忆且对话记录漂移。线程取数失败直接抛(端点 500/SSE error,前端报错)。
        logging.getLogger("scribe3").error("editorial thread 取数失败", exc_info=True)
        raise


def _context_memory_metrics(work: str = "main") -> dict:
    """Task 16-B runtime-status 指标块。绝不含原始 prompt / 秘密值——只有计数、
    分位数与布尔/短标识。诚实区分【当前有真实值】与【采集骨架待 16-C 接线】:

    真实值:cross_work_rejections(16-A)、memory_events_pending/failed(store 计数)、
      context_sessions_active(store 计数)、hermes_memory_provider。
    采样指标:retrieval_p50/p95、context_tokens_p95、stale_rejections；相关事件尚无
      样本时如实为 0/None，不表示统一内核或采集接线关闭。"""
    from scribe3 import context_cache
    metrics = dict(context_cache.metrics_snapshot())   # 检索/组装侧(当前多为 0/None)
    # 安全指标(16-A 只读快照,不复算)
    metrics["cross_work_rejections"] = get_security_metrics().get("cross_work_rejections", 0)
    # 记忆捕获管线水位(per work,与既有 memory_capture.failed_events 同库口径)。
    # U-011(作者要 fail-loud):删掉"查询失败伪装成 0"——那是把"查询挂了"喂成"0个失败事件"
    # 塞进运维仪表盘(最迷惑的假绿,恰恰发生在用来发现问题的诊断路径上)。查询失败在指标块
    # 标 memory_metrics_error(仪表盘显"查询失败"而非假0),但不 500 整个 runtime-status
    # (否则连诊断面板都没了)。
    try:
        st = _store_for(work)
        metrics["memory_events_pending"] = st.count_memory_events(status="pending")
        metrics["memory_events_failed"] = st.count_failed_memory_events()
        metrics["context_sessions_active"] = st.count_active_context_sessions()
    except Exception as e:
        logging.getLogger("scribe3").error("_context_memory_metrics 查询失败", exc_info=True)
        metrics["memory_metrics_error"] = str(e)[:120]
    # 生产记忆提供方：SurrealDB 内的自建多通道检索是唯一运行时实现。
    metrics["hermes_memory_provider"] = "scribe3_builtin"
    return metrics


def _capture_turn_memory(store, *, work: str, thread_id: str, turn_id: str,
                         text: str, chapter: int | None = None) -> None:
    """Task 9:把本轮作者意图幂等捕获成经验记忆(同步 drain)。

    best-effort:任何失败只告警,绝不阻断写作主链路(与 chat_message 落库同纪律 D-004)。
    幂等:event_id = turn:<turn_id>(同轮重放不重复记)。分类/正典红线/linked_ids 领域反查
    在 MemoryCapture 内;known_from=chapter 在此传入(限知门对捕获记忆生效,防知情倒灌)。

    产品默认 MEMORY_FABRIC 开:写路径 + 讨论路径同步捕获经验记忆/正典待审。
    仅显式关(env/DB=0)时短路——测试/运维隔离,不是产品 fallback。
    捕获异常只告警不阻断主链路(与 chat_message 同纪律);HTTP /memory/capture-turn 则 fail-loud。"""
    try:
        fabric_on = _flag_enabled("SCRIBE3_MEMORY_FABRIC_V1")  # type: ignore[name-defined]
    except NameError:
        from scribe3.api import app_impl as _core
        fabric_on = _core._flag_enabled("SCRIBE3_MEMORY_FABRIC_V1")
    if not fabric_on:
        return
    if not (text or "").strip() or not turn_id:
        return
    try:
        from scribe3.memory_capture import MemoryCapture, turn_event
        w = (work or getattr(store, "db_name", None) or "main")
        MemoryCapture(store).capture_event(turn_event(
            text=text, event_id=f"turn:{turn_id}", work=w,
            thread_id=thread_id, known_from=chapter))
    except Exception:
        logging.getLogger("scribe3").warning("记忆捕获失败(忽略,不阻断写作)", exc_info=True)


def _maybe_summarize_thread(work: str, thread_id: str, threshold: int = 12) -> dict:
    """P0b L2:线程增量摘要(补 _thread_history_for_prompt 挂账的 L2)。

    未摘要消息(ts > summarized_upto_ts)≥ threshold 才压缩:旧 summary + 新增轮次
    → 新 summary(≤1500 字;优先保留:①未决决策 ②作者偏好/否决表态 ③伏笔/设定承诺)。
    成功:set_thread_summary(+游标,清 summary_error);失败:log.error + summary_error
    (前端摘要卡红字——失败不许只躺日志,零降级可见性);旧 summary 保留,下轮重试。
    每轮流结束后由 BackgroundTasks 触发(阈值内秒退,零 LLM 成本);/maintenance 夜间兜底。
    整体防线:store 读失败也走 error 路径(log.error + summary_error 尽力标红)——摘要是
    后台增强,绝不允许它把刚结束的对话请求崩掉(BackgroundTasks 异常会炸给 TestClient/日志)。"""
    try:
        return _summarize_thread_inner(work, thread_id, threshold)
    except Exception as e:
        logging.getLogger("scribe3").error("线程摘要失败(store 层)thread=%s", thread_id,
                                           exc_info=True)
        try:
            _store_for(work).set_thread_summary_error(thread_id, str(e)[:200])
        except Exception:
            logging.getLogger("scribe3").error("summary_error 落库也失败 thread=%s", thread_id,
                                               exc_info=True)
        return {"status": "error", "error": str(e)[:200]}


def _summarize_thread_inner(work: str, thread_id: str, threshold: int) -> dict:
    st = _store_for(work)
    row = st._get_editorial_thread(thread_id)
    if row is None:
        return {"status": "missing"}
    upto = str(row.get("summarized_upto_ts") or "")
    msgs = st.list_thread_messages(thread_id, limit=1000)
    fresh = [m for m in msgs
             if m.get("role") in ("user", "assistant")
             and (m.get("text") or "").strip()
             and str(m.get("ts") or "") > upto]
    if len(fresh) < max(2, int(threshold)):
        return {"status": "skipped", "new_count": len(fresh)}
    lines, total = [], 0
    for m in fresh:
        t = (m.get("text") or "").strip().replace("\n", " ")[:300]
        line = f"{'作者' if m['role'] == 'user' else '主编'}:{t}"
        if total + len(line) > 9000:
            break
        lines.append(line)
        total += len(line)
    prev = (row.get("summary") or "").strip()
    prompt = (
        "你是写作系统的会话压缩器。把主编与作者的讨论增量压缩为持续摘要,供后续对话作早期记忆。\n"
        "硬要求:≤1200字;必须留下三类事:①未决问题(还没选的选项)②已选方向"
        "③还没做完的事(设定债/伏笔/下一笔)。去客套与过程废话;第三人称;绝不虚构未出现的内容。\n"
        f"【既有摘要(为空则忽略,否则融合)】\n{prev or '(无)'}\n\n"
        "【新增讨论】\n" + "\n".join(lines) + "\n\n只输出新摘要正文,不加任何前后缀。")
    complete_fn = _complete_fn
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete
    last_ts = str(fresh[-1].get("ts") or "")
    try:
        out = (complete_fn(prompt) or "").strip()
        if not out:
            raise RuntimeError("摘要输出为空")
        st.set_thread_summary(thread_id, out[:1500], last_ts)
        return {"status": "summarized", "new_count": len(fresh)}
    except Exception as e:
        logging.getLogger("scribe3").error("线程摘要失败 thread=%s", thread_id, exc_info=True)
        st.set_thread_summary_error(thread_id, str(e)[:200])
        return {"status": "error", "error": str(e)[:200]}


class _ChatTurnLog:
    """主编【讨论 / agentic】对话留痕的统一咽喉点(北极星任务1 沉淀环第1级;U-005 补齐)。

    背景(2026-07-15 真机实证):三条 SSE 对话路径此前只有 POST /chat/write(动稿)留痕;
    chat_stream(速答讨论)与 chat_agentic_stream(agentic 联查/审批)**从不落库**——作者
    与主编讨论设定、推敲情节、拍板决策的全过程凭空消失(《印迹》一条讨论都没留下,尽管
    当时批准写入了 15 世界规则 + 6 势力)。此类补齐,两条路共用同一个咽喉点,行为一致:

    - `__enter__`(开流前)即落 user:哪怕流中途崩,你的问话已留痕(与 chat_write 同序)。
    - `.feed(delta)` 累积 assistant 文本;`.set_response_id(rid)` 记本轮响应 id。
    - `__exit__`(正常 done / 异常 / 客户端断开触发的 GeneratorExit 都会调)落 assistant 全文;
      流断则落已累积的部分(有一个字也比凭空消失强);完全空则不落(user 已足证"问过")。

    全程 best-effort(D-004):任何一步落库失败只告警,绝不影响对话主链路(SSE 已在飞)。
    留痕存的是【主编回作者的话】——作者对话语境(主编对作者全知),不引入新泄密面,故
    **不做 for_generation 门控**(那是喂正文生成 prompt 的事,与回看历史无关)。

    记忆捕获(2026-08 修):user 落库后同步 _capture_turn_memory——讨论是设定揭示的主路径,
    此前只挂 chat/write 导致「待审正典」面板几乎恒空。捕获 best-effort,不阻断讨论。
    """

    def __init__(self, st, *, user_text: str, chapter: int, stage: str,
                 thread_id: str | None, focus: dict | None = None):
        import uuid
        self._st = st
        self._user_text = user_text
        self._chapter = chapter
        self._stage = stage
        self._thread_id = thread_id
        self._focus = focus
        self.turn_id = uuid.uuid4().hex[:12]   # 串本轮 user/assistant,防并发交错污染蒸馏
        self._buf: list[str] = []
        self._response_id = None
        self._log = logging.getLogger("scribe3")

    def feed(self, delta: str) -> None:
        if delta:
            self._buf.append(delta)

    def collected_text(self) -> str:
        return "".join(self._buf)

    def set_response_id(self, rid) -> None:
        if rid:
            self._response_id = rid

    def _persist_user(self) -> None:
        try:
            self._st.add_chat_message(
                chapter=self._chapter, stage=self._stage, role="user",
                text=self._user_text, turn=self.turn_id,
                thread_id=self._thread_id, focus=self._focus)
        except Exception:
            self._log.warning("chat_message user 落库失败(忽略)", exc_info=True)
        # 讨论路径捕获 → pending_authority_claim / memory_item(与 write 对称)
        try:
            try:
                _cap = _capture_turn_memory  # type: ignore[name-defined]
            except NameError:
                from scribe3.api.services import thread_helpers as _th
                _cap = _th._capture_turn_memory
            work = getattr(self._st, "db_name", None) or "main"
            ch = None
            try:
                if self._chapter is not None and int(self._chapter) > 0:
                    ch = int(self._chapter)
            except (TypeError, ValueError):
                ch = None
            _cap(
                self._st,
                work=work,
                thread_id=self._thread_id or f"discuss:{work}",
                turn_id=self.turn_id,
                text=self._user_text,
                chapter=ch,
            )
        except Exception:
            self._log.warning("讨论记忆捕获失败(忽略)", exc_info=True)

    def _persist_assistant(self) -> None:
        text = "".join(self._buf)
        if not text.strip():
            return   # 完全空(流开头即崩)→ 不落噪声;user 已足证"问过"
        try:
            self._st.add_chat_message(
                chapter=self._chapter, stage=self._stage, role="assistant",
                text=text, turn=self.turn_id, thread_id=self._thread_id,
                focus=self._focus, response_id=self._response_id)
        except Exception:
            self._log.warning("chat_message assistant 落库失败(忽略)", exc_info=True)

    def __enter__(self):
        self._persist_user()
        # P0a:首条 user 消息给默认标题的线程自动命名(store 侧幂等判默认标题;
        # 纯库内小查询,失败上抛不静默——同 U-011 纪律,留痕 best-effort 豁免不适用于它)。
        if self._thread_id:
            self._st.maybe_autotitle_thread(self._thread_id, self._user_text)
        return self

    def __exit__(self, exc_type, exc, tb):
        self._persist_assistant()
        return False   # 不吞异常

