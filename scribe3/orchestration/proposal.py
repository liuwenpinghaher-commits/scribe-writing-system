"""WriteProposal · 多 op 结构化提案（人批前不落库）。"""
from __future__ import annotations

import time
import uuid
from copy import deepcopy
from typing import Any, Callable


def post_approve_ui_target(
    target: dict[str, Any] | None,
    *,
    package: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """批准后硬跟焦目标：create+label → leaf；已是 leaf 原样；禁止停在 codex_new。

    HTTP apply 与 build_write_proposal 共用此函数，避免 ui_after / ui_target_after 分叉。
    """
    t = deepcopy(target) if isinstance(target, dict) else None
    if not t:
        return None
    kind = t.get("kind")
    if kind == "leaf":
        return t
    # 讨论草稿 create 在批准写库后应成为可寻址 leaf
    if kind == "create" and (t.get("label") or t.get("seed", {}).get("name")):
        lab = str(t.get("label") or t.get("seed", {}).get("name") or "").strip()
        ot = t.get("object_type") or "character"
        if not lab or lab in ("（待命名）", "character", "null"):
            return t
        return {
            "kind": "leaf",
            "entry": t.get("entry") or (
                "codex" if ot not in ("promise", "motif") else ot
            ),
            "object_type": ot,
            "id": f"role:{lab}" if ot == "character" else lab,
            "label": lab,
            "right_tab": t.get("right_tab") or "chief",
            "panel": t.get("panel"),
        }
    # 旧 ui_directive 投影（无 kind）
    if kind is None and t.get("node"):
        node = t.get("node") or {}
        ntype = node.get("type")
        if ntype in ("character", "faction", "item", "term", "world_rule", "promise", "motif"):
            lab = str(node.get("label") or node.get("ref") or "").strip()
            if lab and lab not in ("character", "faction", "null", ntype):
                return {
                    "kind": "leaf",
                    "entry": t.get("entry") or "codex",
                    "object_type": ntype,
                    "id": node.get("id") or (f"role:{lab}" if ntype == "character" else lab),
                    "label": lab,
                    "right_tab": "chief",
                }
    return t


def resolve_approve_ui_target(proposal: dict[str, Any] | None) -> dict[str, Any] | None:
    """与 orch_apply_proposal_ep 相同字段优先级：两字段归一为批准后 leaf。

    优先取显式 leaf；否则对 create 做 post_approve 提升。
    """
    prop = proposal or {}
    candidates = [
        prop.get("ui_target_after"),
        prop.get("ui_after"),
    ]
    for c in candidates:
        if isinstance(c, dict) and c.get("kind") == "leaf":
            return deepcopy(c)
    for c in candidates:
        if isinstance(c, dict):
            promoted = post_approve_ui_target(c)
            if promoted and promoted.get("kind") == "leaf":
                return promoted
            if promoted:
                return promoted
    return None


def build_write_proposal(
    package: dict[str, Any],
    ops: list[dict[str, Any]],
    *,
    summary: str = "",
    ui_after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造提案；ops 项: {tool, args, label?}。

    ui_after / ui_target_after 均为**批准后**硬跟焦目标（同一值），不得残留 create。
    """
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
    raw_after = ui_after
    if raw_after is None:
        raw_after = (package or {}).get("ui_target")
    after = post_approve_ui_target(raw_after, package=package)
    return {
        "id": f"prop_{uuid.uuid4().hex[:12]}",
        "work_package_id": (package or {}).get("id"),
        "domain": (package or {}).get("domain"),
        "summary": summary or f"写入提案 · {(package or {}).get('label') or ''}",
        "ops": clean_ops,
        "ui_after": after,
        "ui_target_after": after,  # 与 ui_after 同义；批准路径两字段一致
        "created_at": int(time.time()),
        "status": "pending",
    }


def proposal_from_discussion(
    package: dict[str, Any],
    drafts: list[dict[str, Any]] | None = None,
    *,
    summary: str = "",
) -> dict[str, Any]:
    """从 WorkPackage + SessionEntity 草稿生成多 op 写入提案（人批前不落库）。"""
    pkg = package or {}
    write_tools = list(pkg.get("write_tools") or [])
    ops: list[dict[str, Any]] = []
    domain = str(pkg.get("domain") or "")
    drafts = list(drafts or [])

    def _add(tool: str, args: dict, label: str):
        if write_tools and tool not in write_tools:
            return
        ops.append({"tool": tool, "args": args, "label": label})

    for d in drafts:
        ot = d.get("object_type") or "character"
        lab = d.get("label") or "未命名"
        fields = dict(d.get("fields") or {})
        fields.setdefault("name", lab)
        if ot == "character":
            _add(
                "s3_add_character",
                {"character_id": lab, "name": lab, **{k: v for k, v in fields.items() if k != "name"}},
                f"新建角色·{lab}",
            )
        elif ot == "faction":
            _add("s3_add_faction", {"name": lab, **fields}, f"新建势力·{lab}")
        elif ot == "item":
            _add("s3_add_item", {"name": lab, **fields}, f"新建物件·{lab}")
        elif ot == "term":
            _add("s3_add_term", {"name": lab, **fields}, f"新建术语·{lab}")
        elif ot == "world_rule":
            _add("s3_add_world_rule", {"name": lab, **fields}, f"新建世界规则·{lab}")
        elif ot == "promise":
            _add(
                "s3_plant_promise",
                {
                    "text": fields.get("text") or lab,
                    "setup_chapter": int(fields.get("setup_chapter") or pkg.get("chapter") or 1),
                },
                f"埋伏笔·{lab}",
            )
        elif ot == "motif":
            _add("s3_add_motif", {"name": lab, **fields}, f"新建母题·{lab}")

    # 无草稿时：域默认单 op 占位（仍须人批填全）
    if not ops and write_tools:
        tool = write_tools[0]
        ch = pkg.get("chapter") or 1
        if "plant_promise" in tool:
            _add(tool, {"text": "（请根据讨论填写伏笔正文）", "setup_chapter": ch}, "埋设伏笔")
        elif "chapter" in tool or "plan" in tool:
            _add(tool, {"seq": ch, "synopsis": "（请根据讨论填写大纲）"}, f"第{ch}章大纲")
        elif "character" in tool:
            focus = pkg.get("focus") or {}
            name = (focus.get("label") if isinstance(focus, dict) else None) or "（待命名）"
            _add(tool, {"character_id": name, "name": name}, f"写入角色·{name}")
        else:
            _add(tool, {}, tool)

    # 批准后 hard leaf：草稿专名 → leaf（build_write_proposal 会再归一 ui_after/ui_target_after）
    ui_after = None
    if drafts:
        d0 = drafts[0]
        lab = d0.get("label")
        ot = d0.get("object_type") or "character"
        ui_after = {
            "kind": "leaf",
            "entry": "codex" if ot not in ("promise", "motif") else ot,
            "object_type": ot,
            "id": f"role:{lab}" if ot == "character" else lab,
            "label": lab,
            "right_tab": "chief",
        }
    elif pkg.get("ui_target"):
        ui_after = deepcopy(pkg["ui_target"])

    prop = build_write_proposal(
        pkg, ops,
        summary=summary or f"根据讨论生成 · {pkg.get('label') or domain}",
        ui_after=ui_after,
    )
    prop["source"] = "from_discussion"
    prop["draft_ids"] = [d.get("draft_id") for d in drafts if d.get("draft_id")]
    # 契约：两字段必须一致（build_write_proposal 已归一）
    prop["ui_target_after"] = prop.get("ui_after")
    return prop


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
        try:
            from scribe3.settings_store import append_audit
            append_audit(
                "proposal_reject",
                actor="author",
                payload=str(prop.get("id") or "")[:80],
            )
        except Exception:
            pass
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
