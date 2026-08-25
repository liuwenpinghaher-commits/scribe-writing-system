"""Per-layer generate. Each function returns a raw payload (not yet frozen)."""
from __future__ import annotations

from typing import Any, Callable

from scribe3.playbook.parse import parse_json_with_retry
from scribe3.playbook.stages import STAGE_MAX_TOKENS
from scribe3.playbook.structural import detect_narrative_pov, thin_metaphors
from scribe3.llm_temps import (
    TEMP_CREATE,
    TEMP_DESIGN,
    TEMP_DRAFT,
    TEMP_FINAL,
    TEMP_SCRIBE,
    TEMP_STATE,
)
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
        from scribe3.pipeline_trace import current_trace_buffer
        buf = current_trace_buffer()
        if buf is not None:
            buf.last_prompt = str(prompt or "")
    except Exception:
        pass
    try:
        return llm_fn(
            prompt, max_tokens=max_tokens, system=system, temperature=temperature,
        ) or ""
    except TypeError:
        try:
            return llm_fn(prompt, max_tokens=max_tokens) or ""
        except TypeError:
            return llm_fn(prompt) or ""


def generate_json(llm_fn: Callable, prompt: str, *, system: str, max_tokens: int, temperature: float = TEMP_CREATE) -> dict[str, Any]:
    def _once() -> str:
        return _call(llm_fn, prompt, system=system, temperature=temperature, max_tokens=max_tokens)

    return parse_json_with_retry(_once)


def generate_text(
    llm_fn: Callable, prompt: str, *, system: str, max_tokens: int, temperature: float = TEMP_CREATE,
) -> str:
    return _call(llm_fn, prompt, system=system, temperature=temperature, max_tokens=max_tokens).strip()


def _nail_jail_duty(raw: dict[str, Any], ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """坐牢卡漏了救人进绳时补结构。不另造情节，只钉骨头。"""
    rec = raw if isinstance(raw, dict) else {}
    ctx = ctx or {}
    kind = str(rec.get("kind") or "").strip()
    hint = " ".join(
        str(ctx.get(k) or "")
        for k in ("chapter_duty", "synopsis", "volume_outline")
    )
    if kind != "坐牢" and "坐牢" not in hint and "进了绳" not in hint and "救人的人" not in hint:
        return rec
    rec["kind"] = "坐牢"
    day = str(rec.get("day") or "").strip()
    if not any(x in day for x in ("镇上", "进城", "进镇", "城里", "找活", "活路")):
        rec["day"] = ("镇上还在找活路。" + day).strip()
    happen = str(rec.get("must_happen") or "").strip()
    stay = str(rec.get("stay") or "").strip()
    savior = any(x in f"{happen}\n{stay}" for x in ("救人", "替他", "遮掩", "拦下", "护住"))
    self_tied = any(x in happen for x in ("把沈槐", "沈槐捆", "沈槐带进绳", "沈槐没被放走", "沈槐进了绳"))
    if (not savior) or self_tied:
        rec["must_happen"] = "杏花替沈槐遮掩，差收了东西当场改口，救人的杏花被捆走"
        rec["stay"] = "救人的杏花进了绳。灯还欠着，油账还在秤上"
        rec["heat"] = "差改口叫良民，街上像把他放了"
        rec["crack"] = "东西一交，差改口"
        rec["real"] = "救人的人进了绳，藏油绳的人没进"
        rec["bill"] = "救人的杏花进了绳"
        rec["cut"] = "绳子勒上杏花腕子那一下"
        rec["one_line"] = "差收了东西改口，救人的人进绳"
        rec["keep"] = "杏花替他遮掩，差把她捆走，油绳还在沈槐身上"
        rec["said"] = "沈槐说自己是来镇上找活的"
        rec["needed"] = "灯还欠着，他不敢把油绳交出去"
        rec["intruder"] = "差收了东西改口"
    else:
        if "救人" not in stay:
            rec["stay"] = ("救人的人进了绳。" + stay).strip()
        heat = str(rec.get("heat") or "").strip()
        if "改口" not in heat and "良民" not in heat:
            rec["heat"] = ("官差改口叫良民。" + heat).strip()
        crack = str(rec.get("crack") or "").strip()
        if "改口" not in crack:
            rec["crack"] = ("东西一交，官差改口。" + crack).strip()
        bill = str(rec.get("bill") or "").strip()
        if "救人" not in bill:
            rec["bill"] = ("救人的人进了绳。" + bill).strip()
    who = [str(x).strip() for x in (rec.get("who") or []) if str(x).strip()]
    cast = [str(x).strip() for x in (ctx.get("available_cast") or rec.get("available_cast") or [])]
    if "差" in cast and "差" not in who:
        who.append("差")
        rec["who"] = who
    if not str(rec.get("intruder") or "").strip():
        rec["intruder"] = "差收了东西改口"
    return rec


def _nail_skip_year_duty(raw: dict[str, Any], ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """跳年卡写成补日历 / N年后时，钉回街上还在过的一天。不另造情节。"""
    rec = raw if isinstance(raw, dict) else {}
    ctx = ctx or {}
    kind = str(rec.get("kind") or "").strip()
    hint = " ".join(
        str(ctx.get(k) or "")
        for k in ("chapter_duty", "synopsis", "volume_outline")
    )
    blob = " ".join(
        str(rec.get(k) or "")
        for k in ("day", "must_happen", "stay", "one_line", "keep", "heat", "said")
    )
    if kind != "跳年" and "跳年" not in hint and "街上还在过" not in hint and "店还没开张" not in hint:
        return rec
    rec["kind"] = "跳年"
    from scribe3.playbook.structural import _SKIP_CALENDAR, _SKIP_STREET, _SKIP_SONG
    live = f"{rec.get('day') or ''}\n{rec.get('must_happen') or ''}\n{rec.get('said') or ''}\n{rec.get('heat') or ''}"
    if _SKIP_CALENDAR.search(blob) or _SKIP_SONG.search(blob) or not _SKIP_STREET.search(live):
        rec["day"] = "店还没开张的早上，街上还在过这一天"
        rec["must_happen"] = "茶馆还在讲旧年，行人还在走，有人当街要改歌"
        rec["stay"] = "灯还欠着，救人的人还在绳上，街上这一天还没过完"
        rec["heat"] = "茶馆把旧年当茶讲，像年已经翻了"
        rec["said"] = "把歌改成好卖的"
        rec["needed"] = "灯还欠着，救人的人还在绳上"
        rec["intruder"] = "行人要改歌"
        rec["cut"] = "铜子落在茶馆柜上那一声"
        rec["one_line"] = "年跳过去了"
        rec["keep"] = "店还没开张的早上和茶馆还在讲，删了只剩过场"
        rec["bill"] = "年跳了，账还在"
        rec["owed"] = str(ctx.get("prev_stay") or rec.get("owed") or "灯还欠着").strip()
    for key in ("day", "must_happen", "stay", "heat", "said", "needed", "keep", "one_line", "bill"):
        val = str(rec.get(key) or "")
        if "乱世铜炉" in val or "十八摸" in val:
            rec[key] = val.replace("乱世铜炉", "这首歌").replace("十八摸", "旧调")
    if not str(rec.get("intruder") or "").strip():
        rec["intruder"] = "行人要改歌"
    return rec


def gen_duty(ctx: dict, llm_fn: Callable) -> dict[str, Any]:
    raw = generate_json(
        llm_fn, duty_generate(ctx), system=identity_for("duty"),
        max_tokens=STAGE_MAX_TOKENS["duty"], temperature=TEMP_DESIGN,
    )
    raw["seq"] = int(ctx.get("seq") or 0)
    raw["focalizer"] = ctx.get("focalizer") or raw.get("focalizer") or ""
    raw["available_cast"] = list(ctx.get("available_cast") or [])
    raw["available_lines"] = list(ctx.get("available_lines") or [])
    raw["bite_from_prev"] = ctx.get("prev_hook_quote")
    if int(raw["seq"] or 0) == 1:
        raw["bite_from_prev"] = None
    if not str(raw.get("owed") or "").strip():
        stay_prev = str(ctx.get("prev_stay") or "").strip()
        if stay_prev:
            raw["owed"] = stay_prev
    _nail_jail_duty(raw, ctx)
    _nail_skip_year_duty(raw, ctx)
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
        temperature=TEMP_DESIGN,
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
        system=IDENTITY_SCRIBE, max_tokens=4096, temperature=TEMP_SCRIBE,
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
        temperature=TEMP_DRAFT,
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
        temperature=TEMP_FINAL,
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
        system=IDENTITY_SCRIBE, max_tokens=4096, temperature=TEMP_STATE,
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
