"""UiTarget 代数类型 · 可寻址性 · 投影为 ui_events（唯一合法舞台目标）。

kind ∈ none|stage|category|create|leaf
leaf 必须 addressable（正典 id 或 session draft）；禁止半截 {type:character}。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from scribe3.orchestration.catalog import get_domain

# 会驱动栏 3 GET 的叶类型
LEAF_OBJECT_TYPES = frozenset({
    "character", "faction", "item", "term", "world_rule",
    "promise", "motif", "proposition",
})

_PSEUDO_IDS = frozenset({
    "", "null", "None", "none", "undefined",
    "character", "faction", "item", "term", "world_rule",
    "promise", "motif", "proposition", "角色", "设定",
})


def object_type_for_entry(entry: dict[str, Any] | None) -> str | None:
    if not entry:
        return None
    if entry.get("object_type"):
        return str(entry["object_type"])
    node = (entry.get("ui") or {}).get("node") or {}
    t = node.get("type")
    if t in LEAF_OBJECT_TYPES:
        return str(t)
    domain = str(entry.get("domain") or "")
    if domain.startswith("codex."):
        part = domain.split(".", 1)[-1]
        if part in LEAF_OBJECT_TYPES:
            return part
    if domain.startswith("promise"):
        return "promise"
    if domain.startswith("motif"):
        return "motif"
    if domain.startswith("fact") or "proposition" in domain:
        return "proposition"
    if domain.startswith("relation"):
        return "character"
    if domain.startswith("voice"):
        return "character"
    return None


def fallback_target_for_entry(entry: dict[str, Any] | None) -> dict[str, Any]:
    """无真实实体时的合法目标（category 或 stage）。"""
    if not entry:
        return {"kind": "none"}
    if entry.get("fallback_target"):
        return deepcopy(entry["fallback_target"])
    ui = entry.get("ui") or {}
    entry_key = ui.get("entry") or "manuscript"
    panel = ui.get("panel")
    phase = ui.get("phase") or entry.get("phase_hint")
    ot = object_type_for_entry(entry)
    if ot in ("character", "faction", "item", "term", "world_rule", "proposition"):
        return {
            "kind": "category",
            "entry": "codex",
            "category": ot,
            "panel": panel or f"codex_{ot}",
            "right_tab": ui.get("right_tab") or "chief",
        }
    if ot == "promise":
        return {
            "kind": "category",
            "entry": "promise",
            "category": "promise",
            "panel": panel or "promise",
            "right_tab": ui.get("right_tab") or "chief",
        }
    if ot == "motif":
        return {
            "kind": "category",
            "entry": "motif",
            "category": "motif",
            "panel": panel or "motif",
            "right_tab": ui.get("right_tab") or "chief",
        }
    if (ui.get("node") or {}).get("type") == "chapter" or str(entry.get("domain") or "").startswith(
        ("chapter.", "structure.chapter", "prose.")
    ):
        return {
            "kind": "stage",
            "entry": entry_key,
            "phase": phase,
            "panel": panel,
            "right_tab": ui.get("right_tab") or "chief",
            "needs_chapter": True,
        }
    return {
        "kind": "stage",
        "entry": entry_key,
        "phase": phase,
        "panel": panel,
        "right_tab": ui.get("right_tab") or "chief",
    }


def is_pseudo_leaf_id(oid: Any) -> bool:
    s = str(oid or "").strip()
    if not s or s in _PSEUDO_IDS:
        return True
    # role:character / role: / character:
    if ":" in s:
        local = s.split(":", 1)[-1].strip()
        if not local or local in _PSEUDO_IDS:
            return True
    return False


def is_addressable_leaf_id(
    object_type: str | None,
    oid: Any,
    *,
    draft_ids: set[str] | None = None,
    store_ids: set[str] | None = None,
) -> bool:
    """leaf 可展示：非伪 id，且（在 store 或 session draft 中，或测试放行 draft: 前缀）。"""
    if not object_type or object_type not in LEAF_OBJECT_TYPES:
        return False
    if is_pseudo_leaf_id(oid):
        return False
    s = str(oid).strip()
    local = s.split(":", 1)[-1] if ":" in s else s
    drafts = draft_ids or set()
    stores = store_ids or set()
    if s.startswith("draft:") or local.startswith("draft:"):
        return s in drafts or any(d.endswith(local) or local in d for d in drafts) or True
    if stores:
        return s in stores or local in stores or f"role:{local}" in stores
    # 无 store 探测时：有真实专名即允许 leaf 目标（创建前的「意图 leaf」仍应降级——由调用方决定）
    # 最优契约：未知 store 时仅 draft 可 leaf；正典 leaf 需 store 或 explicit allow
    return False


def build_ui_target(
    entry: dict[str, Any],
    *,
    focus: dict[str, Any] | None = None,
    chapter: int | None = None,
    draft: dict[str, Any] | None = None,
    store_ids: set[str] | None = None,
    force_leaf: bool = False,
) -> dict[str, Any]:
    """由 catalog entry + focus/draft 解析唯一 UiTarget。"""
    ui = entry.get("ui") or {}
    entry_key = ui.get("entry") or "manuscript"
    ot = object_type_for_entry(entry)
    phase = entry.get("phase_hint") or ui.get("phase")

    # 章域：有章号 → stage 带 chapter ref 的 leaf-like chapter（章是可寻址的 seq）
    if str(entry.get("domain") or "").startswith(("chapter.", "structure.chapter", "prose.")) or (
        (ui.get("node") or {}).get("type") == "chapter"
    ):
        seq = None
        if focus and focus.get("type") == "chapter" and focus.get("ref") is not None:
            seq = int(focus["ref"])
        elif chapter is not None:
            seq = int(chapter)
        if seq is not None:
            return {
                "kind": "leaf",
                "entry": entry_key,
                "object_type": "chapter",
                "id": f"ch:{seq}",
                "label": f"第{seq}章",
                "phase": phase,
                "ref": seq,
                "right_tab": ui.get("right_tab") or "chief",
                "panel": ui.get("panel"),
            }
        return fallback_target_for_entry(entry)

    # 草稿优先
    if draft and draft.get("draft_id"):
        label = draft.get("label") or draft.get("draft_id")
        return {
            "kind": "create",
            "entry": entry_key if entry_key != "manuscript" or ot in LEAF_OBJECT_TYPES else "codex",
            "object_type": draft.get("object_type") or ot or "character",
            "draft_id": draft["draft_id"],
            "label": label,
            "seed": deepcopy(draft.get("fields") or {}),
            "right_tab": ui.get("right_tab") or "chief",
            "panel": ui.get("panel"),
        }

    # focus 专名 → 尝试 leaf；不可寻址则 category
    if focus and ot:
        label = str(focus.get("label") or "").strip()
        fid = str(focus.get("id") or focus.get("ref") or "").strip()
        local = label or (fid.split(":", 1)[-1] if fid else "")
        if local and not is_pseudo_leaf_id(local) and not is_pseudo_leaf_id(fid):
            candidate = fid if fid and not is_pseudo_leaf_id(fid) else (
                f"role:{local}" if ot == "character" else local
            )
            draft_ids = set()
            if force_leaf or is_addressable_leaf_id(
                ot, candidate, store_ids=store_ids, draft_ids=draft_ids
            ):
                if store_ids is not None and not is_addressable_leaf_id(
                    ot, candidate, store_ids=store_ids, draft_ids=draft_ids
                ):
                    # 有 store 探测且不在库 → create 引导
                    return {
                        "kind": "create",
                        "entry": "codex" if ot != "promise" else "promise",
                        "object_type": ot,
                        "label": local,
                        "seed": {"name": local},
                        "right_tab": "chief",
                        "panel": ui.get("panel"),
                    }
                # 无 store 探测：有真实专名 → create（待写入）而非假 leaf GET
                if store_ids is None and not force_leaf:
                    return {
                        "kind": "create",
                        "entry": (
                            "codex" if ot in (
                                "character", "faction", "item", "term",
                                "world_rule", "proposition",
                            ) else ("promise" if ot == "promise" else "motif")
                        ),
                        "object_type": ot,
                        "label": local,
                        "seed": {"name": local},
                        "right_tab": "chief",
                        "panel": ui.get("panel"),
                    }
                return {
                    "kind": "leaf",
                    "entry": entry_key,
                    "object_type": ot,
                    "id": candidate,
                    "label": local,
                    "right_tab": ui.get("right_tab") or "chief",
                    "panel": ui.get("panel"),
                }

    return fallback_target_for_entry(entry)


def ui_target_to_directive(target: dict[str, Any] | None) -> dict[str, Any]:
    """兼容旧 ui_directive 投影。"""
    t = target or {"kind": "none"}
    kind = t.get("kind") or "none"
    right = t.get("right_tab") or "chief"
    base: dict[str, Any] = {
        "entry": t.get("entry") or "manuscript",
        "phase": t.get("phase"),
        "panel": t.get("panel"),
        "right_tab": right,
        "layout_mode": "collaboration",
        "ui_target_kind": kind,
    }
    if kind == "none":
        base["node"] = None
        return base
    if kind == "stage":
        base["node"] = None
        return base
    if kind == "category":
        cat = t.get("category") or t.get("object_type") or "character"
        if cat in ("promise", "motif"):
            base["node"] = {
                "type": f"{cat}_view" if cat == "promise" else "motif_view",
                "id": f"{cat}:browse",
                "ref": cat,
                "label": "伏笔" if cat == "promise" else "母题",
                "capability": cat,
            }
        else:
            base["node"] = {
                "type": "codex_category",
                "id": f"cat:{cat}",
                "ref": cat,
                "label": {
                    "character": "角色", "faction": "势力", "item": "物件",
                    "term": "术语", "world_rule": "世界规则", "proposition": "命题",
                }.get(cat, cat),
            }
        return base
    if kind == "create":
        ot = t.get("object_type") or "character"
        base["node"] = {
            "type": "codex_new" if ot not in ("promise", "motif") else f"{ot}_new",
            "id": f"new:{ot}",
            "ref": ot,
            "label": t.get("label") or ot,
            "draft_id": t.get("draft_id"),
            "seed": t.get("seed"),
        }
        if ot in ("character", "faction", "item", "term", "world_rule"):
            base["entry"] = "codex"
        return base
    if kind == "leaf":
        ot = t.get("object_type") or "character"
        if ot == "chapter":
            ref = t.get("ref")
            base["node"] = {
                "type": "chapter",
                "id": t.get("id") or f"ch:{ref}",
                "ref": ref,
                "label": t.get("label") or f"第{ref}章",
            }
            return base
        local = t.get("label") or str(t.get("id") or "").split(":")[-1]
        base["node"] = {
            "type": ot,
            "id": t.get("id") or local,
            "ref": local,
            "label": local,
        }
        return base
    base["node"] = None
    return base


def apply_ui_target_events(
    target: dict[str, Any] | None,
    *,
    focus_policy: str = "soft",
) -> list[dict[str, Any]]:
    """UiTarget + focus_policy → 前端事件。

    soft/none: 不发 selection（不抢栏3）；hard: 发合法 selection。
    """
    t = target or {"kind": "none"}
    kind = t.get("kind") or "none"
    policy = (focus_policy or "soft").lower()
    events: list[dict[str, Any]] = []
    right = t.get("right_tab") or "chief"
    events.append({"type": "s3-right-tab", "detail": right})

    entry = t.get("entry")
    if entry and policy != "none":
        events.append({
            "type": "s3-open-capability",
            "detail": {"capability": entry, "focus": True, "soft": policy == "soft"},
        })

    # 全量 directive 供提示条
    events.append({
        "type": "s3-ui-directive",
        "detail": {
            "ui_target": t,
            "focus_policy": policy,
            "panel": t.get("panel"),
            "entry": entry,
            "phase": t.get("phase"),
        },
    })

    if policy in ("soft", "none"):
        # soft：可选 phase 提示（章大纲讨论）但不 setSel
        if policy == "soft" and t.get("phase") and t.get("ref") is not None:
            events.append({
                "type": "s3-chapter-phase-hint",
                "detail": {"phase": t.get("phase"), "seq": t.get("ref"), "soft": True},
            })
        return events

    # hard：合法 selection
    directive = ui_target_to_directive(t)
    node = directive.get("node")
    if not node:
        return events

    ntype = node.get("type")
    if ntype == "chapter" and node.get("ref") is not None:
        seq = int(node["ref"])
        events.append({
            "type": "selection",
            "detail": {
                "mode": "node",
                "node": {
                    "id": node.get("id") or f"ch:{seq}",
                    "type": "chapter",
                    "ref": seq,
                    "label": node.get("label") or str(seq),
                },
            },
        })
        if t.get("phase"):
            events.append({
                "type": "s3-chapter-phase",
                "detail": {"phase": t["phase"], "seq": seq},
            })
        return events

    if ntype == "codex_category":
        events.append({
            "type": "selection",
            "detail": {"mode": "node", "node": dict(node)},
        })
        return events

    if ntype in ("codex_new", "promise_new", "motif_new"):
        events.append({
            "type": "selection",
            "detail": {"mode": "node", "node": dict(node)},
        })
        return events

    if ntype in ("promise_view", "motif_view"):
        events.append({
            "type": "selection",
            "detail": {"mode": "node", "node": dict(node)},
        })
        return events

    if ntype in LEAF_OBJECT_TYPES:
        # 仅 hard + 非伪 id
        if is_pseudo_leaf_id(node.get("ref") or node.get("id") or node.get("label")):
            # 降级分类
            fb = fallback_target_for_entry(get_domain(f"codex.{ntype}") or {
                "domain": f"codex.{ntype}",
                "ui": {"entry": "codex", "node": {"type": ntype}},
            })
            return apply_ui_target_events(fb, focus_policy="hard")
        events.append({
            "type": "selection",
            "detail": {
                "mode": "node",
                "node": {
                    "id": node.get("id"),
                    "type": ntype,
                    "ref": node.get("ref") or node.get("label"),
                    "label": node.get("label") or node.get("ref") or "",
                },
            },
        })
    return events


def selection_is_ghost_leaf(events: list[dict[str, Any]]) -> bool:
    """测试辅助：事件中是否含幽灵 leaf selection。"""
    for e in events or []:
        if e.get("type") != "selection":
            continue
        node = (e.get("detail") or {}).get("node") or {}
        ntype = node.get("type")
        if ntype not in LEAF_OBJECT_TYPES:
            continue
        if is_pseudo_leaf_id(node.get("ref") or node.get("id") or node.get("label")):
            return True
        if not (node.get("ref") or node.get("label")):
            return True
    return False
