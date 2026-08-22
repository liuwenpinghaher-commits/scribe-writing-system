"""Map author/LLM aliases onto Surreal ASSERT enums.

Hermes / 审批卡常写「supporting」「民俗」；库约束是英文闭集。
不映射则 s3_add_* 点批假绿（proposal HTTP 200、op error、L1 空）。
"""
from __future__ import annotations

CHAR_IMPORTANCE_CANON = ("protagonist", "major", "minor", "background")
RULE_CATEGORY_CANON = ("magic", "technology", "social", "physical", "economic", "political")

_IMPORTANCE_ALIAS = {
    "supporting": "major",
    "support": "major",
    "secondary": "major",
    "mentioned": "background",
    "mention": "background",
    "side": "minor",
    "extra": "background",
    "配角": "major",
    "主角": "protagonist",
    "路人": "background",
    "提及": "background",
}

_RULE_CATEGORY_ALIAS = {
    "民俗": "social",
    "禁忌": "social",
    "规矩": "social",
    "习俗": "social",
    "法术": "magic",
    "魔法": "magic",
    "术法": "magic",
    "技术": "technology",
    "科技": "technology",
    "物理": "physical",
    "经济": "economic",
    "政治": "political",
    "社会": "social",
}


def normalize_char_importance(raw: str | None) -> str | None:
    if raw is None:
        return None
    v = str(raw).strip()
    if not v:
        return None
    if v in CHAR_IMPORTANCE_CANON:
        return v
    return _IMPORTANCE_ALIAS.get(v) or _IMPORTANCE_ALIAS.get(v.lower()) or v


def normalize_rule_category(raw: str | None, *, default: str = "social") -> str:
    v = str(raw or "").strip()
    if not v:
        return default
    if v in RULE_CATEGORY_CANON:
        return v
    return _RULE_CATEGORY_ALIAS.get(v) or _RULE_CATEGORY_ALIAS.get(v.lower()) or default
