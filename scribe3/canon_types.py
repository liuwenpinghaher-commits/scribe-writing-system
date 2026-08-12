"""Canon types & approval gate — shared by canon_loop / canon_apply_store (EH-04).

Breaks top-level cycle: canon_apply_store must not import canon_loop.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class ChangeItem:
    id: str
    layer: str
    op: str
    module: str
    target: str
    after: Any
    evidence: str
    risk: str
    requires_approval: bool
    field: str | None = None
    before: Any = None
    approved: bool = False
    applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        conf = getattr(self, "_confidence", None)
        if conf is not None:
            d["confidence"] = conf
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ChangeItem":
        return cls(
            id=str(d.get("id") or _new_id("ci")),
            layer=str(d.get("layer") or "L1"),
            op=str(d.get("op") or "patch"),
            module=str(d.get("module") or "character"),
            target=str(d.get("target") or ""),
            after=d.get("after"),
            evidence=str(d.get("evidence") or ""),
            risk=str(d.get("risk") or "med"),
            requires_approval=bool(d.get("requires_approval", True)),
            field=d.get("field"),
            before=d.get("before"),
            approved=bool(d.get("approved", False)),
            applied=bool(d.get("applied", False)),
        )


_CANON_MODULES_REQUIRE_APPROVAL = frozenset({
    "character", "world_rule", "intent", "relation", "faction", "item", "term",
    "promise", "char_state", "fact", "motif",
})
_OBJECTIVE_L2_MODULES = frozenset({"knowledge"})


def item_requires_human_approval(layer: str, module: str) -> bool:
    """硬门：layer∈{L0,L1} 或 module 属正典类 → 必须人批。"""
    mod = (module or "").strip().lower()
    lay = (layer or "L1").upper()
    if lay in ("L0", "L1"):
        return True
    if mod in _CANON_MODULES_REQUIRE_APPROVAL:
        return True
    if mod in _OBJECTIVE_L2_MODULES:
        return False
    return True


__all__ = [
    "ChangeItem",
    "item_requires_human_approval",
    "_new_id",
    "_CANON_MODULES_REQUIRE_APPROVAL",
    "_OBJECTIVE_L2_MODULES",
]
