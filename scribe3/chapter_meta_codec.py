"""章 meta JSON 合同列编解码（零 store / 零 Surreal 依赖）。"""
from __future__ import annotations

import json

CHAPTER_JSON_META_KEYS = frozenset({
    "pressure_drive", "beats_meta", "narrative_drive", "narrative_contract",
    "stage_state", "chapter_spine",
})

# JSON 列表合同列（揭示覆盖等）
CHAPTER_JSON_LIST_META_KEYS = frozenset({
    "reveal_secret_ids",
})

CHAPTER_META_ALLOWED = frozenset({
    "synopsis", "volume", "label", "title", "beats",
    "scene_truth", "involved_characters", "deductions",
    "purpose_text", "deltas", "focalizer", "prose_lock",
    "play_sha", "contract_sha", "playbook_version",
    "outline_status", "outline_rev", "confidence",
    "settled_note",
    *CHAPTER_JSON_META_KEYS,
    *CHAPTER_JSON_LIST_META_KEYS,
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


def coerce_chapter_json_list(val) -> list:
    """JSON 列表列：None/坏串 → []；去空白、保序去重。"""
    if val is None or val == "":
        return []
    if isinstance(val, list):
        raw = val
    elif isinstance(val, tuple):
        raw = list(val)
    elif isinstance(val, str):
        try:
            parsed = json.loads(val)
            raw = parsed if isinstance(parsed, list) else [parsed]
        except (ValueError, TypeError):
            raw = [val]
    else:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        s = str(item or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out
