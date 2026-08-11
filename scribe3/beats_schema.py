"""节拍结构校验（O15 · 纯函数 · MCP/REST 共用）。"""
from __future__ import annotations

from typing import Any

ALLOWED_BEAT_TYPES = frozenset({
    "dialogue", "action", "interior", "worldbuild", "exposition",
    "dialogue_heavy", "action_heavy", "",
})
GCD_KEYS = frozenset({
    "goal", "conflict", "disaster", "turn", "reaction", "dilemma",
    "decision", "cost", "hook", "text", "done", "beat_type", "id", "uid",
})


def validate_beats_payload(raw: Any) -> tuple[bool, str, list | None]:
    """返回 (ok, reason, normalized_list_or_None)。

    接受 list 或 {"beats": list}；空列表不通过。
    """
    if raw is None:
        return False, "beats_missing", None
    data = raw
    if isinstance(raw, dict):
        if "beats" not in raw:
            return False, "beats_key_missing", None
        data = raw.get("beats")
    if not isinstance(data, list):
        return False, "beats_not_list", None
    if not data:
        return False, "beats_empty", None
    out: list = []
    for i, item in enumerate(data):
        if isinstance(item, str):
            if not item.strip():
                return False, f"beat_{i}_empty_text", None
            if len(item) > 2000:
                return False, f"beat_{i}_text_too_long", None
            out.append({"text": item})
            continue
        if not isinstance(item, dict):
            return False, f"beat_{i}_type", None
        extra = set(item.keys()) - GCD_KEYS
        if extra:
            return False, f"beat_{i}_unknown_keys", None
        text = str(item.get("text") or "")
        if len(text) > 2000:
            return False, f"beat_{i}_text_too_long", None
        bt = item.get("beat_type")
        if bt is not None and str(bt) not in ALLOWED_BEAT_TYPES:
            return False, f"beat_{i}_bad_beat_type", None
        row = {k: item[k] for k in item if k in GCD_KEYS}
        out.append(row)
    return True, "", out
