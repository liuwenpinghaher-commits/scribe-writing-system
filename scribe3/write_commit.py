"""写门控纯实现（O13 · 无 FastMCP · 可单测）。

``mcp.gating.commit_if_approved`` 委托本模块，避免 slim-host 测试拉起 mcp SDK。
``mcp.tools_write`` 用 ``args_from_tool_locals`` 把生产工具参数送入指纹。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Collection, Mapping


# 与 mcp._common.WRITE_GATED 保持同步的兜底集合（gating 会传入真源）
DEFAULT_WRITE_GATED: frozenset[str] = frozenset({
    "s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge",
    "s3_register_purpose", "s3_set_intent", "s3_patch_character", "s3_patch_codex",
    "s3_plant_promise", "s3_advance_promise", "s3_craft_rule_add",
    "s3_craft_rule_remove", "s3_add_character_relation",
    "s3_add_world_rule", "s3_patch_world_rule", "s3_add_faction",
    "s3_patch_faction", "s3_add_char_state",
    "s3_add_arc_beat", "s3_delete_arc_beat",
    "s3_set_voice_profile", "s3_add_item", "s3_patch_item",
    "s3_add_term", "s3_patch_term",
    "s3_supersede_fact", "s3_forget_knowledge",
    "s3_evolve_relation", "s3_resolve_voice_flag",
    "s3_fold_voice_flags", "s3_add_clue",
    "s3_mark_herring", "s3_touch_promise", "s3_abandon_promise",
    "s3_add_entity_relation", "s3_author_pref_add",
    "s3_add_volume", "s3_patch_volume",
    "s3_plan_volumes", "s3_plan_chapter_accounts",
    "s3_refine_volume_outline", "s3_batch_stage",
    "s3_add_arc_unit", "s3_expand_arc_window", "s3_settle_arc_event",
    "s3_add_chapter", "s3_patch_chapter_meta", "s3_refreeze_chapter",
    "s3_refreeze_volume",
    "s3_patch_play", "s3_patch_contract",
    "s3_generate_stage", "s3_save_chapter_draft",
    "s3_generate_codex", "s3_set_char_anchors",
    "s3_reorder_chapters", "s3_delete_volume",
    "s3_add_motif", "s3_patch_motif", "s3_patch_promise",
    "s3_delete_codex",
})

# tools_write 调用帧里不该进指纹的名字
_SKIP_TOOL_LOCALS: frozenset[str] = frozenset({
    "ctx", "ok", "_write", "do_write", "self", "name", "accepted",
    "summary", "st", "cg", "cg_allowed",
})


def args_from_tool_locals(frame_locals: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """从 MCP 工具函数 locals 收集可序列化参数（供审批幂等指纹）。"""
    if not frame_locals:
        return None
    collected: dict[str, Any] = {}
    for k, v in frame_locals.items():
        if k in _SKIP_TOOL_LOCALS or str(k).startswith("_"):
            continue
        if callable(v) and not isinstance(v, (str, bytes)):
            continue
        try:
            json.dumps(v, default=str)
            collected[k] = v
        except Exception:
            collected[k] = repr(v)[:200]
    return collected or None


def commit_if_approved(
    name: str,
    accepted: bool | None,
    do_write: Callable[[], object],
    *,
    args: dict | None = None,
    write_gated: Collection[str] | None = None,
) -> dict[str, Any]:
    """写门控单一落库点 + 可选审批幂等指纹。"""
    gated = frozenset(write_gated) if write_gated is not None else DEFAULT_WRITE_GATED
    fp = None
    if args is not None:
        try:
            from scribe3.approval_idempotency import (
                compute_approval_fingerprint,
                lookup_approved,
                record_approved,
            )
            fp = compute_approval_fingerprint(name, args)
            hit = lookup_approved(fp)
            if hit is not None:
                if isinstance(hit, dict):
                    out = dict(hit)
                    out.setdefault("status", "written")
                    out["idempotent_replay"] = True
                    out["fingerprint"] = fp
                    return out
                return {
                    "status": "written",
                    "tool": name,
                    "idempotent_replay": True,
                    "fingerprint": fp,
                    "result": hit,
                }
        except Exception:
            fp = None
    if name in gated and accepted is None:
        out_exp = {"status": "expired", "tool": name}
        try:
            from scribe3.approval_audit import record_approval_event
            record_approval_event(
                chain="mcp", action="commit", tool_or_pack=name, status="expired",
            )
        except Exception:
            pass
        return out_exp
    if name in gated and accepted is not True:
        try:
            from scribe3.approval_audit import record_approval_event
            record_approval_event(
                chain="mcp", action="commit", tool_or_pack=name, status="declined",
            )
        except Exception:
            pass
        return {"status": "declined", "tool": name}
    try:
        result = do_write()
    except Exception as e:
        logging.exception("commit_if_approved write failed tool=%s", name)
        try:
            from scribe3.approval_audit import record_approval_event
            record_approval_event(
                chain="mcp", action="commit", tool_or_pack=name, status="error",
                detail={"error": str(e)[:160]},
            )
        except Exception:
            pass
        return {"status": "error", "tool": name, "error": str(e)}
    if result is False:
        return {
            "status": "error",
            "tool": name,
            "error": "write returned false (no-op or missing target)",
        }
    if isinstance(result, dict):
        if result.get("error") and result.get("status") not in ("written", "ok"):
            out = {"status": "error", "tool": name}
            out.update(result)
            out["status"] = "error"
            return out
        out = {"status": "written", "tool": name}
        out.update(result)
        if fp:
            out["fingerprint"] = fp
            try:
                from scribe3.approval_idempotency import record_approved
                record_approved(fp, name, out)
            except Exception:
                pass
        if result.get("status") in ("declined", "error"):
            out["status"] = result["status"]
        else:
            out["status"] = "written"
        try:
            from scribe3.approval_audit import record_approval_event
            record_approval_event(
                chain="mcp", action="commit", tool_or_pack=name,
                status=str(out.get("status") or ""),
            )
        except Exception:
            pass
        return out
    out: dict[str, Any] = {"status": "written", "tool": name}
    if result is not None:
        out["result"] = result
    try:
        from scribe3.approval_audit import record_approval_event
        record_approval_event(
            chain="mcp", action="commit", tool_or_pack=name, status="written",
        )
    except Exception:
        pass
    if fp:
        out["fingerprint"] = fp
        try:
            from scribe3.approval_idempotency import record_approved
            record_approved(fp, name, out)
        except Exception:
            pass
    return out
