"""Discussion system assembly (package C · semantic split)."""
from __future__ import annotations

import logging
from typing import Any, Optional

from scribe3.api.services.write_assemble_blocks import (  # noqa: F401
    _editor_system,
    _editor_identity_block,
)
from scribe3.api.services.write_assemble_context import (  # noqa: F401
    _editor_write_system,
    _outline_block,
    _drama_block,
    _purpose_and_lessons_write_block,
    _material_recall_block,
)

def _record_write_soft_fail(kind: str) -> None:
    from scribe3.api.services.write_assemble import record_write_soft_fail
    record_write_soft_fail(kind)

JOURNEY_LINE_MAX = 200
HAYSTACK_CHARS = 4000


def discuss_request_haystack(user_msg: str, history: list | None = None) -> str:
    """本轮问句 + 近窗至少两轮，给点名档当针。"""
    parts: list[str] = []
    if history:
        for m in list(history)[-4:]:
            if not isinstance(m, dict):
                continue
            text = (m.get("content") or m.get("text") or "").strip()
            if text:
                parts.append(text)
    um = (user_msg or "").strip()
    if um:
        parts.append(um)
    blob = "\n".join(parts)
    return blob[:HAYSTACK_CHARS]


def discuss_journey_line(st, work: str | None = None, seq: int | None = None) -> str:
    """旅程当前站 + 下一步，≤200 字。失败时写「尚未立站」。"""
    try:
        from scribe3.director import JOURNEY_STATIONS, build_workflow_snapshot
        snap = build_workflow_snapshot(st, work=work or "main", seq=seq)
        journey = snap.get("journey") or {}
        current = journey.get("current_station")
        labels = dict(JOURNEY_STATIONS)
        label = labels.get(current) or current
        nxt = snap.get("next_step") or {}
        title = str(nxt.get("title") or "").strip()
        if not current:
            line = "【旅程】尚未立站"
        elif title:
            line = f"【旅程】当前站：{label}。下一步：{title}"
        else:
            line = f"【旅程】当前站：{label}。"
    except Exception:
        line = "【旅程】尚未立站"
    return line[:JOURNEY_LINE_MAX]


def _context_pack_hint(work: str | None) -> str:
    """只点名 pack 字段，不灌戏/契约正文。"""
    try:
        from scribe3.orchestration import package_state
        pkg = package_state.get_active(work or "main") or {}
        pack = pkg.get("context_pack") or []
        names = [str(x).strip() for x in pack if str(x).strip()]
        if not names:
            return ""
        return "【取数提示】可优先查阅：" + "、".join(names[:12])
    except Exception:
        return ""


def assemble_discussion_system(
    st,
    *,
    work: str | None = None,
    chapter: int | None = None,
    user_msg: str = "",
    memory_trace_ctx: dict | None = None,
    pulse_text: str = "",
    directive_text: str = "",
    with_tools_hint: str = "",
    history: list | None = None,
    haystack: str | None = None,
) -> str:
    """B∪C：讨论路径单编译（discussion.v1），禁止写作围栏协议。

    产出与写作同源的 Envelope+Manifest；有 session 绑定时落 TurnBind。
    不调用 _capture_turn_memory。for_generation 语义：讨论全知，不走生成秘密二次门。
    """
    import logging
    import uuid
    from scribe3.context_assembler import envelope_trace_manifest, render_envelope_text
    from scribe3.context_engine import CreativeContextEngine
    from scribe3.context_models import ContextRequest, ContextSource
    from scribe3.context_assembler import estimate_tokens

    if work in (None, ""):
        work = getattr(st, "db_name", None) or "main"
    try:
        from scribe3.api.services.write_stream import (
            _write_snapshot, _get_write_retriever, _save_context_turn_bind,
        )
    except Exception:
        from scribe3.api.services import write_stream as _ws
        _write_snapshot = _ws._write_snapshot
        _get_write_retriever = _ws._get_write_retriever
        _save_context_turn_bind = _ws._save_context_turn_bind

    snap = _write_snapshot(
        st, chapter=chapter, focalizer="", phase=None, work=work,
        memory_trace_ctx=memory_trace_ctx)
    retriever = _get_write_retriever(st)
    _retrieval_out = {} if retriever is not None else None
    hay = haystack if haystack is not None else discuss_request_haystack(user_msg, history)
    query = ((user_msg or hay) or "").strip()[:200]
    supplemental: list[ContextSource] = []

    def _render(envelope):
        # 讨论身份 + 全知 banner（不入 generation 围栏协议）
        parts = [
            "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
            "【模式·讨论全知】本轮是作者/主编讨论，不是限知正文生成；"
            "可讨论设定与私密伏线，但不得输出 ⟦PROPOSAL⟧ 写作围栏或把讨论稿当作书稿定稿。\n"
            "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;"
            "紧扣下方统一上下文中的世界观与北极星,不空泛;给建议时给 2-3 个选项与代价。\n"
        ]
        env_text = render_envelope_text(envelope)
        if env_text:
            parts.append(env_text)
        from scribe3.api.services.write_assemble_blocks import _codex_segments
        named, cards, _st = _codex_segments(
            st, reveal=True, focalizer="", chapter=chapter,
            for_generation=False, request_text=hay or user_msg or "", work=work,
        )
        if named:
            parts.append(named)
        if cards:
            parts.append(cards)
        # pulse / directive 作为可审计补充段
        extra_bits = []
        journey = discuss_journey_line(st, work=work, seq=chapter)
        if journey:
            extra_bits.append(journey)
        pack_hint = _context_pack_hint(work)
        if pack_hint:
            extra_bits.append(pack_hint)
        if (pulse_text or "").strip():
            extra_bits.append(pulse_text.strip())
        if (directive_text or "").strip():
            extra_bits.append(directive_text.strip())
        if (with_tools_hint or "").strip():
            extra_bits.append(with_tools_hint.strip())
        for i, bit in enumerate(extra_bits):
            sid = f"discuss:extra:{i}"
            digest = __import__("hashlib").sha256(bit.encode("utf-8")).hexdigest()
            supplemental.append(ContextSource(
                source_id=sid,
                source_kind="procedural",
                work=str(work or "main"),
                reason="discussion_supplement",
                content_digest=digest,
            ))
            parts.append(bit)
        # 作者偏好
        try:
            pref = _author_prefs_block_safe()
            if pref:
                parts.append(pref)
        except Exception as _sf_e:
            from scribe3.soft_fail import soft_fail
            import logging as _sf_logging
            soft_fail('write_assemble_soft_15', _sf_e, logger='scribe3.write_assemble', level=_sf_logging.DEBUG)
        return "\n\n".join(p for p in parts if p), tuple(supplemental)

    context_request = ContextRequest(
        request_id=uuid.uuid4().hex,
        task_kind="discussion",
        target_ref=f"chapter:{chapter}" if chapter is not None else f"work:{work}",
        navigation_snapshot_id=snap.navigation_id,
        work=snap.work,
        chapter=chapter,
        phase=None,
        actor_role="editor",
        pov_character=None,
        # focus 含用户本轮问句；空书 global 可能薄，不强制以免误杀讨论。
        required_slots=("focus",),
        forbidden_source_kinds=(),
        policy_version="discussion.v1",
    )
    compiled = CreativeContextEngine(
        st, retriever=retriever, retrieval_out=_retrieval_out,
    ).compile(
        context_request, snap, query, "discussion", _render,
    )
    rendered = compiled.rendered_input
    # 合同：讨论系统提示不得含写作围栏协议（防误套 generation.v1 围栏段）
    if "⟦PROPOSAL scope=" in rendered or "绝对禁止输出 ⟦PROPOSAL⟧" in rendered:
        raise RuntimeError("discussion compile leaked write proposal protocol")

    _mtc = memory_trace_ctx or {}
    if _mtc.get("context_session_id") and _mtc.get("context_revision") is not None:
        _sel, _rej = [], []
        _result = (_retrieval_out or {}).get("result") if _retrieval_out is not None else None
        if _result is not None:
            try:
                from scribe3.store import build_memory_trace
                _tmp = build_memory_trace(
                    trace_id="tmp-d", work=str(work or ""), thread_id="",
                    context_session_id=str(_mtc.get("context_session_id")),
                    snapshot_revision=int(_mtc.get("context_revision")),
                    result=_result, store=st)
                _sel = list(_tmp.get("selected") or [])
                _rej = list(_tmp.get("rejected") or [])
            except Exception as _sf_e:
                from scribe3.soft_fail import soft_fail
                import logging as _sf_logging
                soft_fail('write_assemble_soft_16', _sf_e, logger='scribe3.write_assemble', level=_sf_logging.DEBUG)
        _usage = {}
        try:
            _usage = envelope_trace_manifest(compiled.envelope).get("usage_digest") or {}
        except Exception as _sf_e:
            from scribe3.soft_fail import soft_fail
            import logging as _sf_logging
            soft_fail('write_assemble_soft_17', _sf_e, logger='scribe3.write_assemble', level=_sf_logging.DEBUG)
        try:
            _save_context_turn_bind(
                st, snap=snap, envelope=compiled.envelope, work=work, ctx=_mtc,
                task_kind="discussion", path="discuss",
                manifest_id=compiled.manifest.manifest_hash,
                request_id=compiled.request.request_id,
                actual_input_hash=compiled.manifest.actual_input_hash,
                policy_version=compiled.manifest.policy_version,
                selected=_sel, rejected=_rej, query=query,
                usage_digest=_usage)
        except Exception:
            logging.getLogger("scribe3").warning(
                "discussion turn_bind 落库失败(忽略)", exc_info=True)
        if _result is not None:
            try:
                from scribe3.api.services.write_stream import _save_write_memory_trace
                _save_write_memory_trace(
                    st, snap=snap, envelope=compiled.envelope, result=_result,
                    query=query, work=work, ctx=_mtc)
            except Exception:
                logging.getLogger("scribe3").warning(
                    "discussion memory_trace 落库失败(忽略)", exc_info=True)
    # GAP-9：讨论出口 soft 限知扫描（不阻断）
    try:
        from scribe3.epistemic_guard import guard_discuss_instructions
        rendered, _soft_hits = guard_discuss_instructions(
            rendered, st, chapter=int(chapter) if chapter is not None else None,
        )
        if _soft_hits:
            logging.getLogger("scribe3").info(
                "discussion soft secret hits=%s", len(_soft_hits),
            )
    except Exception as _sf_e:
        from scribe3.soft_fail import soft_fail
        import logging as _sf_logging
        soft_fail('write_assemble_soft_18', _sf_e, logger='scribe3.write_assemble', level=_sf_logging.DEBUG)
    return rendered

