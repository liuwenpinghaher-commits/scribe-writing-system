"""章设计工作稿：第一份整章，之后只改没过的那一格。"""
from __future__ import annotations

from typing import Any

# 戏格：按戏切，不是十四张填空。
PLAY_SLOTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("who", "在场和挡", ("who_unmet", "cast_invented")),
    ("event", "本章要、选择、决断", (
        "event_unmet", "spine_choice", "choice_mirror", "second_choice",
        "spine_goal_thin", "spine_padding", "spine_atoms", "spine_density",
        "goal_off_world", "choice_unperformed",
    )),
    ("beat", "没演出的那一场", (
        "beat_count", "beat_choice", "beat_off_spine", "beat_leak",
        "choice_not_staged", "gesture_echo", "beat_echo_prev",
        "beat_decision_homeless",
    )),
    ("bill", "代价", (
        "bill_unmet", "spine_cost_thin", "cost_off_axis", "cost_private_only",
        "cost_same_amplitude", "world_untouched", "world_fact_same",
        "world_fact_missing", "axis_terms_missing", "who_pays_missing",
    )),
    ("bite", "咬上章", ("bite_false_prev", "bite_off_hook")),
    ("place", "时空和地点", (
        "place_name_mismatch", "place_travel_unsaid", "clock_jump_unsaid",
        "place_frozen", "place_required", "clock_required", "clock_frozen",
    )),
    ("line", "动哪条线", (
        "line_delta_empty", "line_off_topic", "line_wrong_bind", "lines_unbound",
    )),
)

# 大纲空槽 → 戏格。先展开再按 PLAY_SLOTS 顺序点下一格。
_SPINE_KEY_TO_SLOT: dict[str, str] = {
    "setting": "place",
    "cast": "who", "obstacle": "who", "conflict": "who",
    "goal": "event", "choice": "event", "decision": "event",
    "inciting": "event", "escalation": "event", "info_gap": "event",
    "hook": "event", "forbid": "event",
    "cost": "bill",
    "bite": "bite",
    "lines": "line",
}

SLOT_ALLOW: dict[str, frozenset[str] | None] = {
    "who": frozenset({"cast", "obstacle", "conflict"}),
    "event": frozenset({
        "goal", "choice", "decision", "inciting", "escalation",
        "info_gap", "hook", "forbid",
    }),
    "bill": frozenset({"cost"}),
    "bite": frozenset({"bite"}),
    "place": frozenset({"setting"}),
    "line": frozenset({"lines"}),
    "beat": None,
}

SLOT_OUT_LINES: dict[str, str] = {
    "who": "在场：\n挡：",
    "event": "本章要：\n选择：\n决断：",
    "bill": "代价：",
    "bite": "咬上章：",
    "place": "时空：\n地点：\n地点增量：",
    "line": "动哪条线：",
    "beat": "## 拍N 和这一场的要/挡/变/付/选",
}


def error_ids(errors) -> list[str]:
    """检查结果里的编号。dict / 字符串都能读。"""
    out: list[str] = []
    for e in errors or []:
        if isinstance(e, dict):
            raw = str(e.get("id") or e.get("detail") or "").strip()
        else:
            raw = str(e or "").strip()
        if raw:
            out.append(raw)
    return out


def first_open_slot(errors: list | None, *, struct_ok: bool) -> str | None:
    """下一格要改哪一戏格。结构都没齐，先当整份开稿。"""
    if not struct_ok:
        return None
    raws = error_ids(errors)
    if not raws:
        return None
    expanded: list[str] = []
    for raw in raws:
        if raw.startswith("spine_slots:"):
            key = raw.split(":", 1)[1]
            mapped = _SPINE_KEY_TO_SLOT.get(key)
            if mapped:
                expanded.append(mapped)
                continue
        expanded.append(raw)
    for sid, _title, codes in PLAY_SLOTS:
        if sid in expanded:
            return sid
        for c in codes:
            if c in expanded or any(m == c or m.startswith(c) for m in expanded):
                return sid
        if sid == "beat" and any(m.startswith("beat_") for m in expanded):
            return sid
    return None


def slot_allow_keys(slot: str | None) -> frozenset[str] | None:
    if not slot:
        return None
    return SLOT_ALLOW.get(slot)


def record_attempt(
    n: int,
    parsed: dict[str, Any] | None,
    dens,
    *,
    raw: str = "",
) -> dict[str, Any]:
    src = parsed if isinstance(parsed, dict) else {}
    errors = list(getattr(dens, "errors", None) or [])
    if not src.get("ok"):
        code = str(src.get("code") or "unparsed")
        if code and code not in errors:
            errors = [code] + errors
    return {
        "n": int(n),
        "struct_ok": bool(src.get("ok")),
        "exam_ok": bool(dens is not None and getattr(dens, "ok", False)),
        "errors": errors,
        "chapter_spine": src.get("chapter_spine") if isinstance(src.get("chapter_spine"), dict) else {},
        "beats": src.get("beats") if isinstance(src.get("beats"), list) else [],
        "clock": src.get("clock") if isinstance(src.get("clock"), dict) else {},
        "place": src.get("place") if isinstance(src.get("place"), dict) else {},
        "designated_beat": src.get("designated_beat"),
        "synopsis": src.get("synopsis") or "",
        "raw_cn": int(src.get("cn") or 0),
        "raw_head": (raw or "")[:240],
    }


def first_passed(attempts: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """历史+本轮多份一块看：哪一整份过了，就用哪一份。不拼格子。"""
    for row in attempts or []:
        if row.get("struct_ok") and row.get("exam_ok"):
            return row
    return None


def slim_attempts(attempts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out = []
    for row in attempts or []:
        out.append({
            "n": row.get("n"),
            "ok": bool(row.get("struct_ok") and row.get("exam_ok")),
            "errors": list(row.get("errors") or []),
            "slot": row.get("slot"),
        })
    return out
