# scribe3/chapter_gcd_rest.py
"""GCD 字段级 REST 收紧（纯函数 · emergency 闸旁路用）。

允许：拍数守恒下的 goal/conflict/disaster/reaction/dilemma/decision/text/done 微调。
禁止：增删拍、改 schema、混写 meta、超长字段。
"""
from __future__ import annotations

from typing import Any

GCD_FIELD_KEYS = frozenset({
    "goal", "conflict", "disaster", "turn", "reaction", "dilemma",
    "decision", "cost", "hook", "text", "done", "beat_type",
})
# 闸外入口只许改 GCD 短字段；text 锁定，避免把场面纸截成口号。
GCD_MUTABLE_KEYS = frozenset(GCD_FIELD_KEYS - {"text"})
GCD_FIELD_MAX = 200


def _as_beat_list(raw: Any) -> list:
    if raw is None:
        return []
    if isinstance(raw, list):
        return list(raw)
    return []


def is_gcd_beats_only_body(fields: dict | None) -> bool:
    """请求体是否仅含 beats（无 title/synopsis/volume 等）。"""
    if not isinstance(fields, dict) or not fields:
        return False
    keys = set(fields.keys())
    return keys == {"beats"} or keys <= {"beats", "source"}


def validate_gcd_beats_patch(
    old_beats: Any,
    new_beats: Any,
) -> tuple[bool, str]:
    """返回 (ok, reason)。ok=False 时 reason 为中文/英文短因。"""
    old_l = _as_beat_list(old_beats)
    new_l = _as_beat_list(new_beats)
    if len(new_l) != len(old_l):
        return False, "beat_count_changed"
    for i, (o, n) in enumerate(zip(old_l, new_l)):
        if not isinstance(n, (dict, str)):
            return False, f"beat_{i}_type"
        if isinstance(n, str):
            return False, f"beat_{i}_text_locked"
        extra = set(n.keys()) - GCD_FIELD_KEYS - {"id", "uid"}
        if extra:
            return False, f"beat_{i}_unknown_keys:{sorted(extra)[:4]}"
        for k in GCD_FIELD_KEYS:
            if k in ("text", "done", "beat_type"):
                continue
            v = n.get(k)
            if v is not None and len(str(v)) > GCD_FIELD_MAX:
                return False, f"beat_{i}_{k}_too_long"
    return True, ""


def normalize_beats_for_store(new_beats: Any) -> list:
    """浅拷贝 list，供 update_chapter_meta。"""
    return _as_beat_list(new_beats)


def merge_gcd_beats_keep_text(old_beats: Any, new_beats: Any) -> list:
    """只合并 GCD 短字段；旧 text 一律保留。"""
    out: list = []
    for o, n in zip(_as_beat_list(old_beats), _as_beat_list(new_beats)):
        base = dict(o) if isinstance(o, dict) else {"text": o}
        if not isinstance(n, dict):
            out.append(base)
            continue
        merged = dict(base)
        for k, v in n.items():
            if k in GCD_MUTABLE_KEYS or k in ("id", "uid"):
                merged[k] = v
        if "text" in base:
            merged["text"] = base.get("text")
        out.append(merged)
    return out


def is_emergency_bypass_chapter_path(path: str) -> bool:
    """是否 emergency 世界写闸旁路的章节子路径（无 FastAPI）。

    闸外白名单：
    - archive|restore|restore-version|gcd-fields|beats-fields（正典运维）
    - stage / stage/advance（阶段机 soft · 非正典世界写）
    - deduce/parallel（并行演绎 plan/execute soft · 不直写 prose）
    """
    if not path.startswith("/chapters/"):
        return False
    rest = path[len("/chapters/"):]
    parts = [p for p in rest.split("/") if p]
    if not parts or not parts[0].isdigit():
        return False
    # /chapters/{seq}/archive|restore|...
    if len(parts) == 2 and parts[1] in (
        "archive", "restore", "restore-version",
        "gcd-fields", "beats-fields",
        "stage",
        "story-move-plan",
    ):
        return True
    # /chapters/{seq}/stage/advance
    if len(parts) == 3 and parts[1] == "stage" and parts[2] == "advance":
        return True
    # /chapters/{seq}/deduce/parallel
    if len(parts) == 3 and parts[1] == "deduce" and parts[2] == "parallel":
        return True
    return False


def apply_gcd_beats_patch(
    old_beats: Any,
    new_beats: Any,
) -> tuple[bool, str, list | None]:
    """shipped 闸外写的核心：校验 + 规范化。返回 (ok, reason, normalized_or_None)。

    不走 beats_schema 的 2000 字 text 帽：本入口不改 text，旧场面纸再厚也放行。
    """
    ok, reason = validate_gcd_beats_patch(old_beats, new_beats)
    if not ok:
        return False, reason, None
    return True, "", merge_gcd_beats_keep_text(old_beats, new_beats)
