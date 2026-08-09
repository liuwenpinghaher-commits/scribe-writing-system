"""Canonical severity and issue-type constants (KD-13)."""
from __future__ import annotations

# Align with FINDING_SEVERITIES + product info
CANONICAL_SEVERITIES = ("S1", "S2", "S3", "S4", "info")

# Types that may enter loop blocking when severity is S1
S1_BLOCKING_TYPES = frozenset({
    "discipline",
    "degeneration",
    "pressure",
    "llm_review",
    "leak",
})

# QC keys that map to issue ledger kinds (expandable beyond five-count UI)
QC_ISSUE_LABELS: dict[str, str] = {
    "repetition": "复读(章内)",
    "cross_repetition": "跨章复读",
    "duplicate_lines": "整句重复",
    "structural": "排比句式",
    "emotion_telling": "情感直说",
    "purple": "辞藻升华",
    "ai_tics": "AI 腔",
    "oversaturation": "过饱和",
    "god_view": "全知/解释口吻",
    "degeneration": "模型退化指纹",
    "filler": "水字数",
    "rule_of_three": "三连套路",
}

# QC keys that are list-of-hits (skip dict-or-None rhythm/adverb)
QC_LIST_KEYS = frozenset(QC_ISSUE_LABELS.keys())

LEGACY_ERROR_KINDS = frozenset({"duplicate_lines", "cross_repetition", "degeneration"})
