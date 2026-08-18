"""Allowlist-only structural gates. Six permitted checks, nothing else."""
from __future__ import annotations

import re
from typing import Any  # store is duck-typed; finalize_gate is optional last mile

from scribe3.playbook.quote import quote_in_play

_LABEL_HEAD = re.compile(
    r"^(时空|在场|本章要|选择|决断|代价)\s*[：:]",
)
CLOCK_SPANS = frozenset({"scene", "day", "days"})
CORE_FIELDS = ("goal", "choice", "decision", "hook")
FIVE_LAYERS = ("perceived", "known", "believed", "acted", "blind")


def _fail(code: str, message: str, field: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "code": code, "message": message}
    if field:
        out["field"] = field
    return out


def _ok() -> dict[str, Any]:
    return {"ok": True}


def _quoted(node: Any) -> tuple[str, str]:
    if not isinstance(node, dict):
        return "", ""
    return str(node.get("text") or "").strip(), str(node.get("quote") or "").strip()


def _line_ids(available_lines: list[Any] | None) -> set[str]:
    out: set[str] = set()
    for item in available_lines or []:
        if isinstance(item, dict):
            i = item.get("id")
            if i:
                out.add(str(i))
        elif item:
            out.add(str(item))
    return out


def check_play_struct(play_text: str) -> dict[str, Any]:
    text = (play_text or "").strip()
    if not text:
        return _fail("play_empty", "戏是空的")
    n = len(re.sub(r"\s+", "", text))
    if n < 200 or n > 4000:
        return _fail("play_len", f"戏字数 {n} 不在 200–4000")
    head = text.splitlines()[:3]
    for line in head:
        if _LABEL_HEAD.match((line or "").strip()):
            return _fail("play_label", "戏开头三行带了旧标签行")
    return _ok()


def check_duty_struct(
    duty: dict[str, Any],
    *,
    available_cast: list[str] | None = None,
    available_lines: list[Any] | None = None,
    prev_hook_quote: str | None = None,
) -> dict[str, Any]:
    def _who(x: str) -> str:
        s = str(x or "").strip()
        return s[5:] if s.startswith("role:") else s

    who = [_who(x) for x in (duty.get("who") or []) if _who(x)]
    if not who:
        return _fail("duty_who_empty", "who 不能空", "who")
    if not str(duty.get("must_happen") or "").strip():
        return _fail("duty_must_empty", "must_happen 不能空", "must_happen")
    if not str(duty.get("bill") or "").strip():
        return _fail("duty_bill_empty", "bill 不能空", "bill")
    fr = duty.get("forbidden_reveal")
    if not isinstance(fr, list) or not [x for x in fr if str(x).strip()]:
        return _fail("duty_forbid_empty", "forbidden_reveal 不能空", "forbidden_reveal")
    cast = {_who(x) for x in (available_cast or []) if _who(x)}
    if cast:
        extra = [n for n in who if n not in cast]
        if extra:
            return _fail("duty_who_cast", f"编了户口外的人: {extra}", "who")
    line = duty.get("line_to_touch")
    if line not in (None, "", "null"):
        ids = _line_ids(available_lines)
        if ids and str(line) not in ids:
            return _fail("duty_line", f"编了不存在的线: {line}", "line_to_touch")
    seq = int(duty.get("seq") or 0)
    bite = duty.get("bite_from_prev")
    if seq == 1:
        if bite not in (None, ""):
            return _fail("duty_bite_ch1", "第1章 bite_from_prev 必须是空", "bite_from_prev")
    else:
        expect = prev_hook_quote
        if expect is not None and bite != expect:
            return _fail("duty_bite", "bite_from_prev 必须等于上章 hook.quote", "bite_from_prev")
    return _ok()


def _need_quote(node: Any, play_text: str, field: str, *, required: bool) -> dict[str, Any] | None:
    if node in (None, "", {}):
        if required:
            return _fail("quote_missing", f"{field} 不能空", field)
        return None
    text, quote = _quoted(node)
    if required and (not text or not quote):
        return _fail("quote_missing", f"{field} 缺 text/quote", field)
    if (text or quote) and not quote:
        return _fail("quote_missing", f"{field} 有 text 无 quote", field)
    if quote and not quote_in_play(quote, play_text):
        return _fail("quote_not_in_play", f"{field} 的 quote 不在戏里", field)
    return None


def check_contract_struct(
    contract: dict[str, Any],
    play_text: str,
    *,
    available_lines: list[Any] | None = None,
) -> dict[str, Any]:
    fields = contract.get("fields") if isinstance(contract.get("fields"), dict) else {}
    choice = fields.get("choice") if isinstance(fields.get("choice"), dict) else {}
    for name in CORE_FIELDS:
        hit = _need_quote(fields.get(name), play_text, name, required=True)
        if hit:
            return hit
    for side in ("side_a", "side_b"):
        hit = _need_quote(choice.get(side), play_text, f"choice.{side}", required=True)
        if hit:
            return hit
    hit = _need_quote(choice, play_text, "choice", required=True)
    if hit:
        return hit
    cost = fields.get("cost")
    if cost not in (None, "", {}):
        hit = _need_quote(cost, play_text, "cost", required=True)
        if hit:
            return hit
    beats = contract.get("beats") or []
    if not isinstance(beats, list) or len(beats) < 3:
        return _fail("beats_count", f"beats 要 ≥3，现有 {len(beats) if isinstance(beats, list) else 0}")
    staged = 0
    for i, beat in enumerate(beats):
        if not isinstance(beat, dict):
            return _fail("beat_shape", f"beat[{i}] 不是对象")
        hit = _need_quote(beat.get("goal"), play_text, f"beats[{i}].goal", required=True)
        if hit:
            return hit
        hit = _need_quote(beat.get("turn"), play_text, f"beats[{i}].turn", required=True)
        if hit:
            return hit
        for opt in ("conflict", "cost"):
            if beat.get(opt) not in (None, "", {}):
                hit = _need_quote(beat.get(opt), play_text, f"beats[{i}].{opt}", required=True)
                if hit:
                    return hit
        if beat.get("stages_choice") is True:
            staged += 1
    if staged != 1:
        return _fail("stages_choice", f"stages_choice=true 必须恰好 1 场，现有 {staged}")
    ids = _line_ids(available_lines)
    for i, line in enumerate(contract.get("lines_touched") or []):
        if not isinstance(line, dict):
            continue
        lid = str(line.get("id") or "")
        if ids and lid and lid not in ids:
            return _fail("line_unknown", f"编了不存在的线: {lid}", f"lines_touched[{i}]")
        q = str(line.get("quote") or "")
        if q and not quote_in_play(q, play_text):
            return _fail("quote_not_in_play", "线的 quote 不在戏里", f"lines_touched[{i}]")
    clock = contract.get("clock")
    if isinstance(clock, dict) and clock:
        span = clock.get("span")
        if span not in CLOCK_SPANS:
            return _fail("clock_span", f"clock.span 只允许 {sorted(CLOCK_SPANS)}", "clock")
        hit = _need_quote(clock, play_text, "clock", required=True)
        if hit:
            return hit
    place = contract.get("place")
    if isinstance(place, dict) and (place.get("name") or place.get("quote") or place.get("text")):
        hit = _need_quote(place, play_text, "place", required=bool(place.get("quote") or place.get("text")))
        if hit:
            return hit
    return _ok()


def check_deduce_struct(deduction: dict[str, Any]) -> dict[str, Any]:
    if not str(deduction.get("scene_truth") or "").strip():
        return _fail("scene_truth_empty", "scene_truth 不能空")
    chars = deduction.get("characters") or []
    if not isinstance(chars, list) or not chars:
        return _fail("chars_empty", "characters 不能空")
    for i, ch in enumerate(chars):
        if not isinstance(ch, dict):
            return _fail("char_shape", f"characters[{i}] 不是对象")
        for layer in FIVE_LAYERS:
            if not str(ch.get(layer) or "").strip():
                return _fail("five_layer", f"{ch.get('id') or i} 缺 {layer}", layer)
    ore = deduction.get("ore") or []
    if not isinstance(ore, list) or not (3 <= len(ore) <= 8):
        return _fail("ore_count", f"矿要 3–8 条，现有 {len(ore) if isinstance(ore, list) else 0}")
    return _ok()


def check_draft_struct(draft_text: str) -> dict[str, Any]:
    text = (draft_text or "").strip()
    if not text:
        return _fail("draft_empty", "排演是空的")
    n = len(re.sub(r"\s+", "", text))
    if n < 500:
        return _fail("draft_len", f"排演字数 {n} 低于 500")
    return _ok()


def check_final_struct(prose_text: str) -> dict[str, Any]:
    text = (prose_text or "").strip()
    if not text:
        return _fail("prose_empty", "正文是空的")
    n = len(re.sub(r"\s+", "", text))
    if n < 1000:
        return _fail("prose_len", f"正文字数 {n} 低于 1000")
    return _ok()


def check_final_last_mile(prose_text: str, *, store: Any = None, seq: int | None = None) -> dict[str, Any]:
    """Length floor + kept finalize_gate (deterministic last mile)."""
    hit = check_final_struct(prose_text)
    if not hit.get("ok"):
        return hit
    if store is None:
        return hit
    try:
        from scribe3.finalize_gate import check_finalize_for_save
        fg = check_finalize_for_save(store, int(seq or 0), prose_text or "")
    except Exception as exc:
        return _fail("finalize_gate_error", str(exc)[:240])
    if not fg.get("allowed"):
        return _fail(
            str(fg.get("code") or "finalize_gate"),
            str(fg.get("detail") or "定稿门没过"),
        )
    return hit
