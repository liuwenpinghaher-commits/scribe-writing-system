"""章 meta JSON 合同列编解码（零 store / 零 Surreal 依赖）。"""
from __future__ import annotations

import json

CHAPTER_JSON_META_KEYS = frozenset({
    "pressure_drive", "beats_meta", "narrative_drive", "narrative_contract", "stage_state",
})

CHAPTER_META_ALLOWED = frozenset({
    "synopsis", "volume", "label", "title", "beats",
    "scene_truth", "involved_characters", "deductions",
    "purpose_text", "deltas",
    *CHAPTER_JSON_META_KEYS,
})


def coerce_chapter_json_dict(val) -> dict:
    """JSON 合同列：None/坏串 → {}；str → json.loads；dict 原样。"""
    if val is None or val == "":
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


def dump_chapter_json_meta(val):
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False)
