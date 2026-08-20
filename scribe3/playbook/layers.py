"""Per-layer generate. Each function returns a raw payload (not yet frozen)."""
from __future__ import annotations

from typing import Any, Callable

from scribe3.playbook.parse import parse_json_with_retry
from scribe3.playbook.structural import detect_narrative_pov, thin_metaphors
from scribe3.playbook.prompts import (
    IDENTITY_NOVELIST,
    IDENTITY_PLAY,
    IDENTITY_SCRIBE,
    contract_extract,
    deduce_generate,
    draft_generate,
    duty_generate,
    final_generate,
    identity_for,
    play_generate,
    state_extract,
)


def _call(llm_fn: Callable, prompt: str, *, system: str, temperature: float, max_tokens: int) -> str:
    try:
        return llm_fn(
            prompt, max_tokens=max_tokens, system=system, temperature=temperature,
        ) or ""
    except TypeError:
        try:
            return llm_fn(prompt, max_tokens=max_tokens) or ""
        except TypeError:
            return llm_fn(prompt) or ""


def generate_json(llm_fn: Callable, prompt: str, *, system: str, max_tokens: int, temperature: float = 0.8) -> dict[str, Any]:
    def _once() -> str:
        return _call(llm_fn, prompt, system=system, temperature=temperature, max_tokens=max_tokens)

    return parse_json_with_retry(_once)


def generate_text(
    llm_fn: Callable, prompt: str, *, system: str, max_tokens: int, temperature: float = 0.8,
) -> str:
    return _call(llm_fn, prompt, system=system, temperature=temperature, max_tokens=max_tokens).strip()


def gen_duty(ctx: dict, llm_fn: Callable) -> dict[str, Any]:
    raw = generate_json(
        llm_fn, duty_generate(ctx), system=identity_for("duty"), max_tokens=2048,
    )
    raw["seq"] = int(ctx.get("seq") or 0)
    raw["focalizer"] = ctx.get("focalizer") or raw.get("focalizer") or ""
    raw["available_cast"] = list(ctx.get("available_cast") or [])
    raw["available_lines"] = list(ctx.get("available_lines") or [])
    raw["bite_from_prev"] = ctx.get("prev_hook_quote")
    if int(raw["seq"] or 0) == 1:
        raw["bite_from_prev"] = None
    fr = raw.get("forbidden_reveal")
    if not (isinstance(fr, list) and any(str(x).strip() for x in fr)):
        secrets = [str(x).strip() for x in (ctx.get("secret_list") or []) if str(x).strip()]
        if secrets:
            raw["forbidden_reveal"] = secrets[:3]
    ids = []
    for item in ctx.get("available_lines") or []:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
        elif item:
            ids.append(str(item))
    line = raw.get("line_to_touch")
    if line not in (None, "", "null") and ids and str(line) not in ids:
        raw["line_to_touch"] = None
    return raw


def gen_play(ctx: dict, llm_fn: Callable) -> dict[str, Any]:
    text = generate_text(
        llm_fn, play_generate(ctx), system=IDENTITY_PLAY, max_tokens=4096,
    )
    duty = ctx.get("duty") or {}
    return {
        "seq": int(ctx.get("seq") or 0),
        "text": text,
        "duty_sha": duty.get("sha") or "",
    }


def gen_contract(ctx: dict, llm_fn: Callable) -> dict[str, Any]:
    raw = generate_json(
        llm_fn, contract_extract(ctx),
        system=IDENTITY_SCRIBE, max_tokens=4096, temperature=0,
    )
    play = ctx.get("play") or {}
    raw["play_sha"] = play.get("sha") or ctx.get("play_sha") or ""
    raw["seq"] = int(ctx.get("seq") or 0)
    return raw


def gen_deduce(ctx: dict, llm_fn: Callable) -> dict[str, Any]:
    raw = generate_json(
        llm_fn, deduce_generate(ctx), system=IDENTITY_NOVELIST, max_tokens=8192,
    )
    raw["play_sha"] = (ctx.get("play") or {}).get("sha") or ""
    raw["contract_sha"] = (ctx.get("contract") or {}).get("sha") or ""
    raw["seq"] = int(ctx.get("seq") or 0)
    return raw


def gen_draft(ctx: dict, llm_fn: Callable) -> dict[str, Any]:
    text = generate_text(
        llm_fn, draft_generate(ctx), system=IDENTITY_NOVELIST, max_tokens=16384,
        temperature=0.4,
    )
    bite = ctx.get("bite_quote") or ctx.get("prev_hook_quote") or ""
    text = thin_metaphors(text, exempt_quotes=tuple(q for q in (bite,) if q))
    return {
        "seq": int(ctx.get("seq") or 0),
        "text": text,
        "play_sha": (ctx.get("play") or {}).get("sha") or "",
        "contract_sha": (ctx.get("contract") or {}).get("sha") or "",
    }


def gen_final(ctx: dict, llm_fn: Callable) -> dict[str, Any]:
    text = generate_text(
        llm_fn, final_generate(ctx), system=IDENTITY_NOVELIST, max_tokens=16384,
    )
    text = thin_metaphors(text)
    return {
        "seq": int(ctx.get("seq") or 0),
        "text": text,
        "play_sha": (ctx.get("play") or {}).get("sha") or "",
        "contract_sha": (ctx.get("contract") or {}).get("sha") or "",
    }


def _gender_map(ctx: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    prev = ctx.get("prev_state") or {}
    for ch in (prev.get("characters") or []) if isinstance(prev, dict) else []:
        if isinstance(ch, dict) and ch.get("name") and str(ch.get("gender") or "").strip() in ("男", "女"):
            out[str(ch["name"]).strip()] = str(ch["gender"]).strip()
    for ch in ctx.get("cast_cards") or []:
        if isinstance(ch, dict) and ch.get("name") and str(ch.get("gender") or "").strip() in ("男", "女"):
            out[str(ch["name"]).strip()] = str(ch["gender"]).strip()
    return out


def gen_state(ctx: dict, llm_fn: Callable) -> dict[str, Any]:
    raw = generate_json(
        llm_fn, state_extract(ctx),
        system=IDENTITY_SCRIBE, max_tokens=4096, temperature=0.2,
    )
    seq = int(ctx.get("seq") or raw.get("seq") or 0)
    raw["seq"] = seq
    genders = _gender_map(ctx)
    chars = raw.get("characters") if isinstance(raw.get("characters"), list) else []
    for ch in chars:
        if not isinstance(ch, dict):
            continue
        n = str(ch.get("name") or "").strip()
        if n in genders:
            ch["gender"] = genders[n]
    raw["characters"] = chars
    loops = raw.get("open_loops") if isinstance(raw.get("open_loops"), list) else []
    for loop in loops:
        if not isinstance(loop, dict):
            continue
        try:
            frm = int(loop.get("from_seq") or seq)
        except (TypeError, ValueError):
            frm = seq
        if frm < 1:
            frm = seq
        loop["from_seq"] = frm
        try:
            due = int(loop.get("due_seq") or 0)
        except (TypeError, ValueError):
            due = 0
        if due < frm:
            due = frm + 3
        loop["due_seq"] = due
    raw["open_loops"] = loops
    if not isinstance(raw.get("objects"), list):
        raw["objects"] = []
    if not isinstance(raw.get("timeline"), dict):
        raw["timeline"] = {"at": "", "elapsed_from_prev": ""}
    if not isinstance(raw.get("imagery"), list):
        raw["imagery"] = []
    detected = detect_narrative_pov(str(ctx.get("source_text") or ""))
    inherited = str((ctx.get("prev_state") or {}).get("narrative_pov") or "").strip()
    if int(seq) <= 1 or inherited not in ("first", "third"):
        raw["narrative_pov"] = detected
    else:
        raw["narrative_pov"] = inherited
    return raw
