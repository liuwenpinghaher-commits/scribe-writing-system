"""WriteProposal · 多 op 结构化提案（人批前不落库）。"""
from __future__ import annotations

import time
import uuid
from copy import deepcopy
from typing import Any, Callable


def build_write_proposal(
    package: dict[str, Any],
    ops: list[dict[str, Any]],
    *,
    summary: str = "",
) -> dict[str, Any]:
    """构造提案；ops 项: {tool, args, label?}。"""
    clean_ops = []
    allow = set((package or {}).get("write_tools") or [])
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        tool = op.get("tool") or op.get("name")
        if not tool:
            continue
        if allow and tool not in allow:
            # 仍收录但标记越权，审批层可拒
            flagged = True
        else:
            flagged = False
        clean_ops.append({
            "tool": tool,
            "args": deepcopy(op.get("args") or {}),
            "label": op.get("label") or tool,
            "out_of_allowlist": flagged,
            "status": "pending",
        })
    return {
        "id": f"prop_{uuid.uuid4().hex[:12]}",
        "work_package_id": (package or {}).get("id"),
        "domain": (package or {}).get("domain"),
        "summary": summary or f"写入提案 · {(package or {}).get('label') or ''}",
        "ops": clean_ops,
        "ui_after": (package or {}).get("ui_directive"),
        "created_at": int(time.time()),
        "status": "pending",
    }


def apply_proposal_ops(
    proposal: dict[str, Any],
    *,
    decision: str,
    executors: dict[str, Callable[..., Any]],
    selected: list[int] | None = None,
) -> dict[str, Any]:
    """批准/拒绝提案。decision=approve|reject。

    executors: tool_name -> callable(**args) 返回 store 结果。
    未批准不调用 executor。拒绝全部 marked declined。
    """
    prop = deepcopy(proposal or {})
    ops = list(prop.get("ops") or [])
    if decision != "approve":
        for op in ops:
            op["status"] = "declined"
        prop["ops"] = ops
        prop["status"] = "declined"
        prop["applied"] = []
        prop["errors"] = []
        return prop

    indices = set(selected if selected is not None else range(len(ops)))
    applied: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for i, op in enumerate(ops):
        if i not in indices:
            op["status"] = "skipped"
            continue
        if op.get("out_of_allowlist"):
            op["status"] = "error"
            op["error"] = "tool not in package allowlist"
            errors.append({"tool": op.get("tool"), "error": op["error"]})
            continue
        tool = op.get("tool")
        fn = executors.get(tool)
        if not fn:
            op["status"] = "error"
            op["error"] = f"no executor for {tool}"
            errors.append({"tool": tool, "error": op["error"]})
            continue
        try:
            result = fn(**(op.get("args") or {}))
            # 模拟 commit_if_approved：仅 executor 返回即视为已在外层门控通过
            if isinstance(result, dict) and result.get("status") == "declined":
                op["status"] = "declined"
                continue
            if isinstance(result, dict) and result.get("status") == "error":
                op["status"] = "error"
                op["error"] = result.get("error") or "error"
                errors.append({"tool": tool, "error": op["error"]})
                continue
            op["status"] = "written"
            op["result"] = result if isinstance(result, dict) else {"ok": True}
            applied.append({"tool": tool, "result": op["result"]})
        except Exception as e:
            op["status"] = "error"
            op["error"] = str(e)
            errors.append({"tool": tool, "error": str(e)})
    prop["ops"] = ops
    prop["applied"] = applied
    prop["errors"] = errors
    prop["status"] = "applied" if applied and not errors else (
        "partial" if applied else "error"
    )
    return prop
