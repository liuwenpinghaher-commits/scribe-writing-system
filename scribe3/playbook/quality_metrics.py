"""Wave C 机器尺子。验收层调用这些函数，禁止另写对照实现。"""
from __future__ import annotations

import re
from typing import Any

from scribe3.anti_meta_narration import scan_anti_meta
from scribe3.playbook.structural import (
    _plain,
    check_chapter_state_struct,
    check_gender_pronoun,
    check_pov_consistency,
    detect_narrative_pov,
    dialogue_ratio,
    draft_play_overlap,
    metaphor_per_800,
    residue_hits,
)

_BOUNDARY = re.compile(r"上一章|这一章|下一章|前一章|前章|本章")


def chapter_boundary_count(text: str) -> int:
    scan = scan_anti_meta(text or "")
    return sum(1 for h in (scan.get("hits") or []) if h.get("id") == "M8")


def _who(x: Any) -> str:
    s = str(x or "").strip()
    return s[5:] if s.startswith("role:") else s


def measure_chapter(store: Any, seq: int) -> dict[str, Any]:
    """对已冻结章量 C-Must。store 须有 get_frozen。"""
    seq = int(seq)
    play = store.get_frozen("chapter_play", seq) or {}
    contract = store.get_frozen("chapter_contract", seq) or {}
    duty = store.get_frozen("duty_card", seq) or {}
    draft = store.get_frozen("chapter_draft", seq) or {}
    play_text = str(play.get("text") or "")
    draft_text = str(draft.get("text") or "")
    fields = contract.get("fields") if isinstance(contract.get("fields"), dict) else {}
    prev_hook = ""
    if seq >= 2:
        prev_c = store.get_frozen("chapter_contract", seq - 1) or {}
        prev_f = prev_c.get("fields") if isinstance(prev_c.get("fields"), dict) else {}
        prev_h = prev_f.get("hook") if isinstance(prev_f.get("hook"), dict) else {}
        prev_hook = str(prev_h.get("quote") or "")
    from scribe3.playbook.pipeline import contract_nail_quotes
    exempt = contract_nail_quotes(contract, prev_hook)
    overlap = draft_play_overlap(draft_text, play_text, exempt_quotes=exempt) if play_text and draft_text else 1.0
    cost = fields.get("cost")
    cost_ok = cost not in (None, "", {})
    beats = contract.get("beats") or []
    staged = [b for b in beats if isinstance(b, dict) and b.get("stages_choice") is True]
    conflict_ok = bool(staged) and all(
        b.get("conflict") not in (None, "", {}) for b in staged
    )
    who = [_who(x) for x in (duty.get("who") or []) if _who(x)]
    ch = {}
    getter = getattr(store, "get_chapter", None)
    if callable(getter):
        ch = getter(seq) or {}
    prose = str(ch.get("prose") or draft_text)
    m8 = chapter_boundary_count(prose) + chapter_boundary_count(draft_text)
    dlg = dialogue_ratio(prose)
    meta = metaphor_per_800(prose)
    draft_n = len(_plain(draft_text))
    prev_state = store.get_frozen("chapter_state", seq - 1) or {} if seq >= 2 else {}
    this_state = store.get_frozen("chapter_state", seq) or {}
    roster = []
    for ch in (prev_state.get("characters") or []) if isinstance(prev_state, dict) else []:
        if isinstance(ch, dict) and ch.get("name") and str(ch.get("gender") or "") in ("男", "女"):
            roster.append({"name": ch["name"], "gender": ch["gender"]})
    gp = check_gender_pronoun(prose, roster)
    gender_ok = bool(gp.get("ok"))
    expected_pov = str((prev_state or {}).get("narrative_pov") or "").strip()
    pov_hit = check_pov_consistency(draft_text or prose, expected_pov if seq > 1 else None)
    pov_ok = bool(pov_hit.get("ok"))
    detected_pov = detect_narrative_pov(draft_text or prose)
    residues = residue_hits(draft_text or prose)
    due_open = []
    this_loops = {
        str(x.get("text") or "")
        for x in (this_state.get("open_loops") or [])
        if isinstance(x, dict)
    }
    for loop in (prev_state.get("open_loops") or []) if isinstance(prev_state, dict) else []:
        if not isinstance(loop, dict):
            continue
        try:
            due = int(loop.get("due_seq") or 0)
        except (TypeError, ValueError):
            due = 0
        text = str(loop.get("text") or "")
        if due and due <= seq and text and text in this_loops:
            due_open.append(loop)
    loops_ok = not due_open
    state_present = bool(this_state) and str(this_state.get("status") or "frozen") != "needs_human"
    state_quote_ok = True
    if this_state:
        src = prose.strip() and prose or draft_text
        sq = check_chapter_state_struct(this_state, src)
        state_quote_ok = bool(sq.get("ok"))
        if not state_quote_ok and prose and draft_text and src != draft_text:
            state_quote_ok = bool(check_chapter_state_struct(this_state, draft_text).get("ok"))
    overdue = []
    for loop in (this_state.get("open_loops") or []) if isinstance(this_state, dict) else []:
        if not isinstance(loop, dict):
            continue
        try:
            due = int(loop.get("due_seq") or 0)
        except (TypeError, ValueError):
            due = 0
        if due and due < seq:
            overdue.append(loop)
    ok = (
        overlap <= 0.15
        and m8 == 0
        and cost_ok
        and conflict_ok
        and len(who) >= 2
        and dlg >= 0.15
        and meta <= 1.0
        and draft_n >= 2000
        and bool(play_text)
        and bool(draft_text)
        and gender_ok
        and pov_ok
        and loops_ok
        and (not this_state or (state_present and state_quote_ok))
    )
    return {
        "seq": seq,
        "overlap": round(overlap, 4),
        "boundary_hits": m8,
        "cost_ok": cost_ok,
        "conflict_ok": conflict_ok,
        "who": who,
        "who_n": len(who),
        "dialogue_ratio": round(dlg, 4),
        "metaphor_per_800": round(meta, 4),
        "draft_chars": draft_n,
        "play_chars": len(_plain(play_text)),
        "prose_chars": len(_plain(prose)),
        "gender_ok": gender_ok,
        "pov_ok": pov_ok,
        "narrative_pov": detected_pov,
        "expected_pov": expected_pov or "",
        "residue_hits": residues[:8],
        "due_loops_open": len(due_open),
        "overdue_loops": len(overdue),
        "state_present": state_present,
        "state_quote_ok": state_quote_ok,
        "ok": ok,
    }
