"""ContextTurnView · 上下文检查器唯一读模型（B∪C）。

设计权威：设计文档/2026-08-09-上下文检查器-B合C最优方案.md

- available=false / availability=not_compiled_yet：不得用全 0 块冒充「无记忆」。
- available=true：八块 block_tokens + blocks[].source_count 与 envelope 对齐。
- 纯函数优先，便于无 DB 夹具测合同。
"""
from __future__ import annotations

from typing import Any

VIEW_VERSION = "context-turn-view.v1"

# 与 context_assembler.BLOCK_BUDGETS / ContextBlock 顺序对齐
BLOCK_ORDER: tuple[str, ...] = (
    "focus",
    "global",
    "canonical",
    "recent",
    "procedural",
    "reference",
    "uncertainty",
    "provenance",
)


def not_compiled_view(
    *,
    session_id: str,
    revision: int,
    reason: str = "not_retrieved_yet",
) -> dict[str, Any]:
    """诚实空态：无块 token 网格，避免假 0。"""
    return {
        "available": False,
        "availability": "not_compiled_yet",
        "reason": reason,
        "session_id": session_id,
        "snapshot_revision": int(revision),
        "view_version": VIEW_VERSION,
    }


def blocks_from_envelope(envelope) -> list[dict[str, Any]]:
    """从 ContextEnvelope 提取块级 token 与 source_ids。"""
    out: list[dict[str, Any]] = []
    by_name: dict[str, Any] = {}
    for b in getattr(envelope, "blocks", None) or []:
        name = str(getattr(b, "name", "") or "")
        sids = [str(getattr(s, "source_id", "") or "") for s in (getattr(b, "sources", None) or [])]
        sids = [x for x in sids if x]
        by_name[name] = {
            "name": name,
            "token_estimate": int(getattr(b, "token_estimate", 0) or 0),
            "source_ids": sids,
            "source_count": len(sids),
        }
    for name in BLOCK_ORDER:
        if name in by_name:
            out.append(by_name[name])
        else:
            out.append({
                "name": name,
                "token_estimate": 0,
                "source_ids": [],
                "source_count": 0,
            })
    # 附加非标准块名（若有）
    for name, row in by_name.items():
        if name not in BLOCK_ORDER:
            out.append(row)
    return out


def block_tokens_from_blocks(blocks: list[dict[str, Any]]) -> dict[str, int]:
    return {str(b.get("name")): int(b.get("token_estimate") or 0) for b in blocks if b.get("name")}


def build_turn_view(
    *,
    session_id: str,
    revision: int,
    work: str = "",
    task_kind: str = "draft",
    path: str = "write",
    envelope=None,
    manifest_id: str | None = None,
    request_id: str | None = None,
    actual_input_hash: str | None = None,
    policy_version: str | None = None,
    envelope_hash: str | None = None,
    selected: list | None = None,
    rejected: list | None = None,
    usage_digest: dict | None = None,
    query: str = "",
    synthetic_snapshot: bool = False,
) -> dict[str, Any]:
    """就绪态 View：有 envelope 时从中取块；否则 blocks 可外传入（dict 列表）。"""
    if envelope is not None:
        blocks = blocks_from_envelope(envelope)
        env_hash = envelope_hash or str(getattr(envelope, "envelope_hash", "") or "")
    else:
        blocks = []
        env_hash = envelope_hash or ""
    tokens = block_tokens_from_blocks(blocks)
    return {
        "available": True,
        "availability": "ready",
        "view_version": VIEW_VERSION,
        "work": work or "",
        "context_session_id": session_id,
        "session_id": session_id,
        "snapshot_revision": int(revision),
        "task_kind": task_kind or "draft",
        "path": path or "write",
        "manifest_id": manifest_id,
        "request_id": request_id,
        "actual_input_hash": actual_input_hash,
        "policy_version": policy_version,
        "envelope_hash": env_hash,
        "block_tokens": tokens,
        "blocks": blocks,
        "selected": list(selected or []),
        "rejected": list(rejected or []),
        "usage_digest": usage_digest or {},
        "query": query or "",
        "synthetic_snapshot": bool(synthetic_snapshot),
        # 兼容旧 Inspector：selected/rejected/block_tokens 已齐
    }


def view_from_bind_row(row: dict | None, *, session_id: str, revision: int) -> dict[str, Any]:
    """从 context_turn_bind 行还原 View；无行 → not_compiled。"""
    if not row or not isinstance(row, dict):
        return not_compiled_view(session_id=session_id, revision=revision)
    blocks = list(row.get("blocks") or [])
    if not blocks and row.get("block_tokens"):
        # 仅有 tokens 时补空源块
        bt = row.get("block_tokens") or {}
        blocks = [
            {
                "name": name,
                "token_estimate": int(bt.get(name) or 0),
                "source_ids": [],
                "source_count": 0,
            }
            for name in BLOCK_ORDER
        ]
    tokens = row.get("block_tokens") or block_tokens_from_blocks(blocks)
    return {
        "available": True,
        "availability": str(row.get("availability") or "ready"),
        "view_version": VIEW_VERSION,
        "work": str(row.get("work") or ""),
        "context_session_id": str(row.get("context_session_id") or session_id),
        "session_id": str(row.get("context_session_id") or session_id),
        "snapshot_revision": int(row.get("snapshot_revision") if row.get("snapshot_revision") is not None else revision),
        "task_kind": str(row.get("task_kind") or "draft"),
        "path": str(row.get("path") or "write"),
        "manifest_id": row.get("manifest_id"),
        "request_id": row.get("request_id"),
        "actual_input_hash": row.get("actual_input_hash"),
        "policy_version": row.get("policy_version"),
        "envelope_hash": row.get("envelope_hash") or "",
        "block_tokens": tokens,
        "blocks": blocks,
        "selected": list(row.get("selected") or []),
        "rejected": list(row.get("rejected") or []),
        "usage_digest": row.get("usage_digest") or {},
        "query": str(row.get("query") or ""),
        "synthetic_snapshot": bool(row.get("synthetic_snapshot")),
    }


def merge_memory_trace_into_view(view: dict, trace: dict | None) -> dict[str, Any]:
    """用 memory_trace 补检索明细（channels / rejected 文本理由）；不覆盖块 token。"""
    if not view.get("available") or not isinstance(trace, dict):
        return view
    out = dict(view)
    if trace.get("selected"):
        # 有检索明细时优先展示（含 text 预览）
        out["selected"] = list(trace["selected"])
    if trace.get("rejected"):
        out["rejected"] = list(trace["rejected"])
    if trace.get("channels"):
        out["channels"] = trace["channels"]
    if trace.get("query") and not out.get("query"):
        out["query"] = trace["query"]
    if trace.get("envelope_hash") and not out.get("envelope_hash"):
        out["envelope_hash"] = trace["envelope_hash"]
    return out
