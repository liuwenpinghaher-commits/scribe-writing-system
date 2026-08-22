"""正典变更闭环（理想闭环的可测内核）。

路径: 共识/正文 → Diff 主张 → ChangePack 提案 → 人批 → Apply。
L1（Codex/世界规则）禁止静默写；L2 客观账本可标记 objective 后落账。

本模块无 IO 硬依赖：测试注入 claims / InMemoryCanonStore。
LLM 抽取可外挂；确定性 ``parse_marker_claims`` 供契约测试。
"""
from __future__ import annotations

import re
import uuid
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, MutableMapping, Optional

from scribe3.canon_types import (  # EH-04: re-export for callers
    ChangeItem,
    item_requires_human_approval,
    _new_id as _types_new_id,
)

LAYERS = frozenset({"L0", "L1", "L2"})
MODULES = frozenset({
    "intent", "character", "world_rule", "relation", "knowledge",
    "fact", "faction", "item", "term", "promise", "char_state", "motif",
})
RISKS = frozenset({"low", "med", "high"})

# 【设定 L1|character|role:沈拾灯|fear|被写进灯芯|高】证据句
# 【知识 L2|knowledge|role:沈拾灯|fact:债契三夜|知道|低】
_MARKER_RE = re.compile(
    r"【(?P<label>设定|知识|意图)"
    r"\s*(?P<layer>L[012])?"
    r"\|(?P<module>[a-z_]+)"
    r"\|(?P<target>[^|]+)"
    r"(?:\|(?P<field>[^|]+))?"
    r"(?:\|(?P<after>[^|]+))?"
    r"(?:\|(?P<risk>[低中高]|low|med|high))?"
    r"】"
    r"(?P<evidence>[^【]{0,200})?",
    re.I,
)

_RISK_MAP = {"低": "low", "中": "med", "高": "high", "low": "low", "med": "med", "high": "high"}


@dataclass
class CanonClaim:
    """相对正典的一条主张（尚未成包）。"""

    layer: str
    op: str  # add | patch
    module: str
    target: str
    after: Any
    evidence: str = ""
    risk: str = "med"
    field: str | None = None
    requires_approval: bool | None = None  # None → 由 layer 推断
    confidence: float = 1.0  # 抽取置信度；启发式宜 <0.6

    def __post_init__(self) -> None:
        self.layer = (self.layer or "L1").upper()
        if self.layer not in LAYERS:
            raise ValueError(f"invalid layer {self.layer!r}")
        self.module = (self.module or "").strip()
        if self.module not in MODULES:
            raise ValueError(f"invalid module {self.module!r}")
        self.risk = _RISK_MAP.get((self.risk or "med").lower(), (self.risk or "med").lower())
        if self.risk not in RISKS:
            self.risk = "med"
        self.op = (self.op or "patch").strip()
        if self.requires_approval is None:
            self.requires_approval = item_requires_human_approval(self.layer, self.module)
        elif not item_requires_human_approval(self.layer, self.module):
            # 仅允许在 objective 模块上显式 requires_approval=False
            pass
        else:
            # 正典模块：忽略客户端 False
            self.requires_approval = True


# ChangeItem / item_requires_human_approval: see canon_types (re-exported above)


@dataclass
class ChangePack:
    id: str
    work: str
    source: str  # discussion | outline | body_confirmed | fixture
    items: list[ChangeItem] = field(default_factory=list)
    impact: dict[str, Any] = field(default_factory=dict)
    status: str = "proposed"  # proposed | partially_approved | applied | rejected

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "work": self.work,
            "source": self.source,
            "items": [i.to_dict() for i in self.items],
            "impact": self.impact,
            "status": self.status,
            "l1_count": sum(1 for i in self.items if i.layer == "L1"),
            "l2_count": sum(1 for i in self.items if i.layer == "L2"),
            "requires_approval_count": sum(1 for i in self.items if i.requires_approval),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ChangePack":
        items = [ChangeItem.from_dict(x) for x in (d.get("items") or [])]
        return cls(
            id=str(d.get("id") or _new_id("cp")),
            work=str(d.get("work") or "main"),
            source=str(d.get("source") or "fixture"),
            items=items,
            impact=dict(d.get("impact") or {}),
            status=str(d.get("status") or "proposed"),
        )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def parse_marker_claims(text: str) -> list[CanonClaim]:
    """从确定性标记语法抽取主张（测试与无 LLM 路径）。

    例: ``【设定 L1|character|role:沈拾灯|fear|被写进灯芯|高】雨巷里他怕灯芯上有自己的名。``
    """
    out: list[CanonClaim] = []
    for m in _MARKER_RE.finditer(text or ""):
        label = (m.group("label") or "").strip()
        layer = (m.group("layer") or "").upper()
        if not layer:
            layer = "L2" if label == "知识" else ("L0" if label == "意图" else "L1")
        module = (m.group("module") or "character").strip()
        target = (m.group("target") or "").strip()
        field = (m.group("field") or None)
        after = (m.group("after") or "").strip() or True
        risk_raw = (m.group("risk") or "med").strip()
        risk = _RISK_MAP.get(risk_raw, risk_raw if risk_raw in RISKS else "med")
        evidence = (m.group("evidence") or "").strip()
        # 若 field 看起来像 after（无 after 段时）
        if field and after is True and "|" not in (m.group(0) or ""):
            pass
        op = "add" if module in ("fact", "knowledge", "char_state") and not field else "patch"
        if module == "knowledge":
            # target=knower, field=proposition, after=via
            op = "add"
        out.append(CanonClaim(
            layer=layer,
            op=op,
            module=module,
            target=target,
            field=field if field not in (None, "") else None,
            after=after,
            evidence=evidence or m.group(0)[:80],
            risk=risk,
        ))
    return out


def _lookup_before(
    snapshot: Mapping[str, Any] | None,
    module: str,
    target: str,
    field: str | None,
) -> Any:
    if not snapshot:
        return None
    if module == "character":
        chars = snapshot.get("characters") or {}
        # keys may be bare or role:
        ent = chars.get(target) or chars.get(target.split(":")[-1]) or {}
        if field:
            return ent.get(field)
        return ent or None
    if module == "world_rule":
        rules = snapshot.get("world_rules") or {}
        return rules.get(target) or rules.get(target.split(":")[-1])
    if module == "intent":
        intent = snapshot.get("intent") or {}
        return intent.get(field) if field else intent
    if module == "knowledge":
        return None  # edges are additive
    return None


def build_impact(
    targets: Iterable[str],
    chapter_index: Mapping[str, list[int]] | None = None,
    inject_surfaces: list[str] | None = None,
) -> dict[str, Any]:
    """影响面：被引用章号 + 注入面。无引用时显式空列表。"""
    chapters: list[int] = []
    chapter_index = chapter_index or {}
    for t in targets:
        bare = t.split(":")[-1]
        for key in (t, bare, f"role:{bare}"):
            for seq in chapter_index.get(key) or []:
                if seq not in chapters:
                    chapters.append(seq)
    chapters.sort()
    surfaces = inject_surfaces if inject_surfaces is not None else [
        "chapter_brief", "pilot_steer", "write_assemble", "project_frame",
    ]
    return {
        "chapters": chapters,
        "inject_surfaces": list(surfaces),
        "note": "empty chapters means no prior chapter index hit (explicit empty, not omitted)",
    }


def pack_from_claims(
    claims: Iterable[CanonClaim | Mapping[str, Any]],
    *,
    work: str = "main",
    source: str = "discussion",
    canon_snapshot: Mapping[str, Any] | None = None,
    chapter_index: Mapping[str, list[int]] | None = None,
) -> ChangePack:
    """主张 → ChangePack；**不写库**。"""
    items: list[ChangeItem] = []
    targets: list[str] = []
    for raw in claims:
        c = raw if isinstance(raw, CanonClaim) else CanonClaim(
            layer=str(raw.get("layer") or "L1"),
            op=str(raw.get("op") or "patch"),
            module=str(raw.get("module") or "character"),
            target=str(raw.get("target") or ""),
            after=raw.get("after"),
            evidence=str(raw.get("evidence") or ""),
            risk=str(raw.get("risk") or "med"),
            field=raw.get("field"),
            requires_approval=raw.get("requires_approval"),
        )
        before = _lookup_before(canon_snapshot, c.module, c.target, c.field)
        items.append(ChangeItem(
            id=_new_id("ci"),
            layer=c.layer,
            op=c.op,
            module=c.module,
            target=c.target,
            field=c.field,
            before=before,
            after=c.after,
            evidence=c.evidence,
            risk=c.risk,
            requires_approval=bool(c.requires_approval),
            approved=False,
            applied=False,
        ))
        # confidence 写入 to_dict 友好：挂在最后一条的并行 dict 由 to_dict 不含；
        # persist 侧从 pack items dict 读取 —— pack_from_claims 后 to_dict 时补 conf
        try:
            items[-1]._confidence = float(getattr(c, "confidence", 1.0) or 1.0)  # type: ignore[attr-defined]
        except Exception:
            pass
        if c.target:
            targets.append(c.target)
    pack = ChangePack(
        id=_new_id("cp"),
        work=work,
        source=source,
        items=items,
        impact=build_impact(targets, chapter_index=chapter_index),
        status="proposed",
    )
    return pack


def pack_from_discussion_text(
    text: str,
    *,
    work: str = "main",
    source: str = "discussion",
    canon_snapshot: Mapping[str, Any] | None = None,
    chapter_index: Mapping[str, list[int]] | None = None,
    claims: Iterable[CanonClaim | Mapping[str, Any]] | None = None,
) -> ChangePack:
    """讨论/大纲文本 → ChangePack。

    优先使用注入的 claims；否则解析确定性标记。无主张时返回空 items 包（仍不写库）。
    """
    use = list(claims) if claims is not None else parse_marker_claims(text)
    return pack_from_claims(
        use,
        work=work,
        source=source,
        canon_snapshot=canon_snapshot,
        chapter_index=chapter_index,
    )


def build_post_finalize_report(
    *,
    seq: int,
    prose: str,
    work: str = "main",
    claims: Iterable[CanonClaim | Mapping[str, Any]] | None = None,
    canon_snapshot: Mapping[str, Any] | None = None,
    chapter_index: Mapping[str, list[int]] | None = None,
) -> dict[str, Any]:
    """正文确认后的模块报告：分 L2 客观 vs L1 待批；**不自动 apply L1**。"""
    text = prose or ""
    use = list(claims) if claims is not None else parse_marker_claims(text)
    # 若正文无标记，仍给空结构报告（契约完整）
    pack = pack_from_claims(
        use,
        work=work,
        source="body_confirmed",
        canon_snapshot=canon_snapshot,
        chapter_index=chapter_index,
    )
    l2_objective = [i.to_dict() for i in pack.items if not i.requires_approval]
    l1_requires = [i.to_dict() for i in pack.items if i.requires_approval]
    modules_l2 = sorted({i["module"] for i in l2_objective})
    modules_l1 = sorted({i["module"] for i in l1_requires})
    return {
        "seq": seq,
        "work": work,
        "source": "body_confirmed",
        "prose_chars": len(re.sub(r"\s+", "", text)),
        "change_pack": pack.to_dict(),
        "sections": {
            "l2_objective": {
                "label": "客观账本（知识/可见事件类，可自动或一键 objective apply）",
                "modules": modules_l2,
                "items": l2_objective,
                "auto_applied": False,  # 报告本身不写库
            },
            "l1_requires_approval": {
                "label": "设定正典（Codex/规则/关系基石，须人批后 apply）",
                "modules": modules_l1,
                "items": l1_requires,
                "auto_applied": False,
            },
        },
        "impact": pack.impact,
        "silent_l1_write": False,
    }


class InMemoryCanonStore:
    """测试与无 Surreal 路径的可观测账本。"""

    def __init__(self) -> None:
        self.characters: dict[str, dict[str, Any]] = {}
        self.world_rules: dict[str, Any] = {}
        self.intent: dict[str, Any] = {}
        self.knowledge: list[dict[str, Any]] = []
        self.facts: dict[str, Any] = {}
        self.applied_log: list[dict[str, Any]] = []

    def snapshot(self) -> dict[str, Any]:
        return {
            "characters": deepcopy(self.characters),
            "world_rules": deepcopy(self.world_rules),
            "intent": deepcopy(self.intent),
            "knowledge": list(self.knowledge),
            "facts": deepcopy(self.facts),
        }

    def read_character_field(self, target: str, field: str) -> Any:
        bare = target.split(":")[-1]
        ent = self.characters.get(target) or self.characters.get(bare) or {}
        return ent.get(field)

    def apply_item(self, item: ChangeItem) -> dict[str, Any]:
        bare = item.target.split(":")[-1]
        key = item.target if item.target in self.characters else bare
        if item.module == "character":
            ent = self.characters.setdefault(key, {"name": bare})
            if item.field:
                ent[item.field] = item.after
            elif isinstance(item.after, dict):
                ent.update(item.after)
            else:
                ent["note"] = item.after
        elif item.module == "world_rule":
            self.world_rules[key] = item.after
        elif item.module == "intent":
            if item.field:
                self.intent[item.field] = item.after
            elif isinstance(item.after, dict):
                self.intent.update(item.after)
        elif item.module == "knowledge":
            self.knowledge.append({
                "knower": item.target,
                "proposition": item.field,
                "via": item.after,
            })
        elif item.module == "fact":
            self.facts[key] = item.after
        else:
            # 通用桶
            bucket = getattr(self, item.module, None)
            if isinstance(bucket, dict):
                bucket[key] = item.after
        rec = {"item_id": item.id, "module": item.module, "target": item.target, "field": item.field}
        self.applied_log.append(rec)
        return rec


# 正典级模块：即使客户端把 layer 标成 L2 也必须人批（防 layer 侧信道静默写）
def _dispatch_apply(store: Any, item: ChangeItem) -> dict[str, Any]:
    """InMemory 用 apply_item；SurrealStore 用 canon_apply_store。"""
    if isinstance(store, InMemoryCanonStore) or (
        hasattr(store, "apply_item") and not hasattr(store, "add_entity")
    ):
        if hasattr(store, "apply_item"):
            return store.apply_item(item)
    try:
        from scribe3.canon_apply_store import apply_item_to_store
        rec = apply_item_to_store(store, item)
        if rec.get("status") == "error":
            return {"item_id": item.id, **rec}
        rec.setdefault("item_id", item.id)
        return rec
    except Exception as e:
        if hasattr(store, "apply_item"):
            return store.apply_item(item)
        return {"item_id": item.id, "status": "error", "error": str(e)[:200]}


def apply_change_pack(
    pack: ChangePack | Mapping[str, Any],
    *,
    approved_item_ids: Iterable[str] | None = None,
    apply_objective_l2: bool = True,
    store: Any = None,
) -> dict[str, Any]:
    """执行变更包。

    安全策略（防静默写正典）:
    - **仅信任** ``approved_item_ids`` 服务端入参；**忽略** pack 内客户端
      ``item.approved`` / 伪造的 ``requires_approval=False`` / 伪造 ``layer=L2``。
    - 正典模块（character/world_rule/intent/…）或 L0/L1：**必须** id ∈ approved_item_ids。
    - 仅 ``knowledge`` 等客观 L2 可按 ``apply_objective_l2`` 无 L1 式批准落账。
    - store 可为 InMemoryCanonStore 或 SurrealStore。
    """
    p = pack if isinstance(pack, ChangePack) else ChangePack.from_dict(pack)
    approved_set = {str(x) for x in (approved_item_ids or [])}
    store = store if store is not None else InMemoryCanonStore()
    applied: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    # GAP-13：canon 链进入统一审批观察面
    try:
        from scribe3.approval_audit import record_approval_event
        record_approval_event(
            chain="canon",
            action="apply_change_pack",
            work=str(getattr(p, "work", None) or (pack.get("work") if isinstance(pack, dict) else "") or "main"),
            tool_or_pack=str(getattr(p, "id", None) or (pack.get("id") if isinstance(pack, dict) else "") or "change_pack"),
            status="started",
            detail={"approved_ids": list(approved_set)[:20]},
        )
    except Exception:
        pass

    for item in p.items:
        layer = (item.layer or "L1").upper()
        module = (item.module or "").strip().lower()
        item.layer = layer
        item.module = module
        must_approve = item_requires_human_approval(layer, module)
        # 正典模块若被标成 L2，纠回 L1 语义（审计清晰）
        if must_approve and layer == "L2" and module in _CANON_MODULES_REQUIRE_APPROVAL:
            item.layer = "L1"
            layer = "L1"
        item.requires_approval = must_approve
        client_self_approved = bool(item.approved)
        item.approved = False  # 不信任客户端

        if item.applied:
            skipped.append({"id": item.id, "reason": "already_applied"})
            continue

        if must_approve:
            if item.id not in approved_set:
                rejected.append({
                    "id": item.id,
                    "layer": item.layer,
                    "module": item.module,
                    "target": item.target,
                    "reason": "l1_requires_approval_not_granted",
                    "client_self_approved_ignored": client_self_approved,
                    "layer_spoof_blocked": True,
                })
                continue
            rec = _dispatch_apply(store, item)
            if rec.get("status") == "error":
                rejected.append({
                    "id": item.id, "layer": item.layer, "module": item.module,
                    "target": item.target, "reason": "apply_error",
                    "error": rec.get("error"),
                })
                continue
            item.applied = True
            item.approved = True
            applied.append(rec)
            continue

        # 客观 L2（如 knowledge）
        if not apply_objective_l2:
            skipped.append({"id": item.id, "reason": "objective_l2_disabled"})
            continue
        rec = _dispatch_apply(store, item)
        if rec.get("status") == "error":
            rejected.append({
                "id": item.id, "module": item.module, "reason": "apply_error",
                "error": rec.get("error"),
            })
            continue
        item.applied = True
        applied.append(rec)

    if applied and not rejected:
        p.status = "applied"
    elif applied and rejected:
        # DED-04：半包回滚已 apply，避免设定库花脸
        undone = []
        for rec in reversed(list(applied)):
            try:
                if _undo_applied(store, rec):
                    undone.append(rec)
            except Exception:
                pass
        if undone:
            applied = [a for a in applied if a not in undone]
            p.status = "rolled_back" if not applied else "partially_approved"
        else:
            p.status = "partially_approved"
    elif rejected and not applied:
        p.status = "proposed"
    result = {
        "pack_id": p.id,
        "status": p.status,
        "applied": applied,
        "rejected": rejected,
        "skipped": skipped,
        "store_snapshot": store.snapshot() if hasattr(store, "snapshot") else {},
        "pack": p.to_dict(),
        "silent_l1_blocked": any(
            r.get("reason") == "l1_requires_approval_not_granted" for r in rejected
        ),
    }
    try:
        from scribe3.approval_audit import record_approval_event
        record_approval_event(
            chain="canon",
            action="apply_change_pack",
            work=str(getattr(p, "work", None) or "main"),
            tool_or_pack=str(p.id or "change_pack"),
            status=str(p.status or ""),
            detail={
                "applied_n": len(applied),
                "rejected_n": len(rejected),
                "skipped_n": len(skipped),
            },
        )
    except Exception:
        pass
    return result


def _undo_applied(store: Any, rec: dict[str, Any]) -> bool:
    if not isinstance(rec, dict):
        return False
    module = str(rec.get("module") or "")
    op = str(rec.get("op") or "")
    if module == "character" and rec.get("oid") and hasattr(store, "delete_record"):
        return bool(store.delete_record(rec["oid"], cleanup_refs=True))
    if module == "faction" and rec.get("name") and hasattr(store, "delete_faction"):
        store.delete_faction(rec["name"])
        return True
    if module == "item" and rec.get("name") and hasattr(store, "delete_item"):
        store.delete_item(rec["name"])
        return True
    if module == "term" and rec.get("name") and hasattr(store, "delete_term"):
        store.delete_term(rec["name"])
        return True
    if module == "world_rule" and rec.get("name") and hasattr(store, "delete_world_rule"):
        store.delete_world_rule(rec["name"])
        return True
    return False


def mark_items_approved(pack: ChangePack, item_ids: Iterable[str]) -> ChangePack:
    ids = set(item_ids)
    for item in pack.items:
        if item.id in ids:
            item.approved = True
    return pack


__all__ = [
    "CanonClaim",
    "ChangeItem",
    "ChangePack",
    "InMemoryCanonStore",
    "parse_marker_claims",
    "pack_from_claims",
    "pack_from_discussion_text",
    "build_post_finalize_report",
    "build_impact",
    "apply_change_pack",
    "mark_items_approved",
    "item_requires_human_approval",
]
