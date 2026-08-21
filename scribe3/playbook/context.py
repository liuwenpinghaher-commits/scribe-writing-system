"""Assemble generator/judge context from a live store. Soft-fail on missing pieces."""
from __future__ import annotations

import logging
import re
from typing import Any

_log = logging.getLogger("scribe3.playbook.context")

_LIVE_PAD = "此句只为把设定写够，说明处境、代价和不能拆穿的事。"
_OLD_PAD = "这不是口号，是巷里炉灰和铜腥贴在骨头上的实感。"
GENERIC_SYNOPSIS_MIN = 16
_VOLUME_INTRO_BUDGET = 400
_CODEX_BUDGET = 800


def _clean_name(n: str) -> str:
    s = str(n or "").strip()
    if s.startswith("role:"):
        s = s[5:]
    return s.strip()


def _names(rows: list[Any]) -> list[str]:
    out: list[str] = []
    for r in rows or []:
        n = ""
        if isinstance(r, dict):
            n = r.get("name") or r.get("id") or r.get("label") or ""
        else:
            n = getattr(r, "name", None) or getattr(r, "id", None) or ""
            if not n:
                n = str(r or "")
        n = _clean_name(n)
        if n:
            out.append(n)
    return out


def secret_list(st: Any) -> list[str]:
    """本章还不能拆穿的事：红线 + 标了私密的命题。"""
    out: list[str] = []
    getter = getattr(st, "get_intent", None)
    if callable(getter):
        try:
            red = (getter() or {}).get("red_lines") or ""
        except Exception:
            red = ""
        for line in str(red).splitlines():
            hit = line.strip()
            if hit:
                out.append(hit)
    secrets_fn = getattr(st, "_secret_proposition_values", None)
    if callable(secrets_fn):
        try:
            for v in secrets_fn() or []:
                s = str(v or "").strip()
                if s:
                    out.append(s)
        except Exception:
            pass
    seen: set[str] = set()
    uniq: list[str] = []
    for item in out:
        if item not in seen:
            seen.add(item)
            uniq.append(item)
    return uniq


def available_cast(st: Any) -> list[str]:
    for name in ("list_characters", "characters", "list_character_names"):
        fn = getattr(st, name, None)
        if callable(fn):
            try:
                return _names(fn() or [])
            except Exception:
                continue
    return []


def _entity_gender(row: Any) -> str:
    traits: dict[str, Any] = {}
    if isinstance(row, dict):
        traits = row.get("traits") if isinstance(row.get("traits"), dict) else row
        g = traits.get("gender") or row.get("gender") or ""
    else:
        traits = getattr(row, "traits", None) or {}
        g = (traits.get("gender") if isinstance(traits, dict) else "") or getattr(row, "gender", "") or ""
    g = str(g or "").strip()
    return g if g in ("男", "女") else ""


def cast_cards(st: Any) -> list[dict[str, str]]:
    """户口卡片：名字 + 已登记性别。读失败则空列表。"""
    rows: list[Any] = []
    for name in ("list_characters", "characters"):
        fn = getattr(st, name, None)
        if callable(fn):
            try:
                rows = fn() or []
                break
            except Exception:
                continue
    out: list[dict[str, str]] = []
    for r in rows:
        names = _names([r])
        if not names:
            continue
        out.append({"name": names[0], "gender": _entity_gender(r)})
    return out


def book_imagery(st: Any) -> str:
    getter = getattr(st, "get_intent", None)
    if not callable(getter):
        return ""
    try:
        intent = getter() or {}
    except Exception:
        return ""
    if not isinstance(intent, dict):
        return ""
    return str(intent.get("imagery") or "").strip()


def prev_chapter_state(store: Any, seq: int) -> dict[str, Any] | None:
    if int(seq) <= 1:
        return None
    fn = getattr(store, "get_frozen", None)
    if not callable(fn):
        return None
    rec = fn("chapter_state", int(seq) - 1)
    return rec if isinstance(rec, dict) else None


def gender_roster(*sources: Any) -> list[dict[str, str]]:
    """合并上章末态人物 + 户口卡片。后写覆盖先写（户口覆盖末态）。"""
    out: dict[str, str] = {}
    for src in sources:
        if not src:
            continue
        rows = src
        if isinstance(src, dict):
            rows = src.get("characters") or src.get("cast_cards") or []
        for ch in rows or []:
            if not isinstance(ch, dict):
                continue
            n = str(ch.get("name") or "").strip()
            g = str(ch.get("gender") or "").strip()
            if n and g in ("男", "女"):
                out[n] = g
    return [{"name": n, "gender": g} for n, g in out.items()]


def available_lines(st: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for name in ("list_promises", "promises"):
        fn = getattr(st, name, None)
        if not callable(fn):
            continue
        try:
            rows = fn() or []
        except Exception:
            rows = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            pid = str(r.get("id") or r.get("promise_id") or "")
            text = str(r.get("text") or r.get("body") or r.get("title") or "")
            if pid:
                out.append({"kind": "promise", "id": pid, "text": text})
    return out


def prev_hook_quote(store: Any, seq: int) -> str | None:
    if int(seq) <= 1:
        return None
    fn = getattr(store, "get_frozen", None)
    if not callable(fn):
        return None
    contract = fn("chapter_contract", int(seq) - 1)
    if not isinstance(contract, dict):
        return None
    fields = contract.get("fields") if isinstance(contract.get("fields"), dict) else {}
    hook = fields.get("hook") if isinstance(fields.get("hook"), dict) else {}
    q = hook.get("quote")
    return str(q) if q else None


def prev_play_with_hook(quote: str) -> dict[str, Any]:
    """Contract-shaped stub whose hook.quote is the bite source."""
    q = str(quote or "")
    return {"fields": {"hook": {"text": q, "quote": q}}}


def make_duty(prev: dict[str, Any] | None = None, *, seq: int = 2, **fields: Any) -> dict[str, Any]:
    """Mechanical bite: copy previous hook.quote. LLM never invents this field."""
    hook = None
    if int(seq) > 1 and isinstance(prev, dict):
        if "fields" in prev:
            hook = ((prev.get("fields") or {}).get("hook") or {}).get("quote")
        elif "text" in prev:
            # allow passing a play; bite still comes from a contract hook if present
            hook = (prev.get("hook") or {}).get("quote") if isinstance(prev.get("hook"), dict) else None
    return {
        "seq": int(seq),
        "who": list(fields.get("who") or ["沈烛若"]),
        "must_happen": fields.get("must_happen") or "办事",
        "bill": fields.get("bill") or "付账",
        "forbidden_reveal": list(fields.get("forbidden_reveal") or ["秘密"]),
        "bite_from_prev": None if int(seq) == 1 else hook,
        "focalizer": fields.get("focalizer") or "沈烛若",
        "available_cast": list(fields.get("available_cast") or ["沈烛若"]),
        "available_lines": list(fields.get("available_lines") or []),
        "line_to_touch": fields.get("line_to_touch"),
    }


def _collapse_ws(s: str) -> str:
    return "".join(str(s or "").split())


def strip_seed_pad(text: str) -> str:
    s = str(text or "")
    for pad in (_LIVE_PAD, _OLD_PAD):
        s = s.replace(pad, "")
    s = re.sub(r"([^。；\n]{8,40})(?:[；;]\s*\1){2,}", r"\1", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def synopsis_is_generic(rows: list[Any] | None, seq: int, syn: str) -> bool:
    peeled = _collapse_ws(strip_seed_pad(syn))
    if len(peeled) < GENERIC_SYNOPSIS_MIN:
        return True
    n_same = 0
    for row in rows or []:
        other = _collapse_ws(strip_seed_pad(str((row or {}).get("synopsis") or "")))
        if other and other == peeled:
            n_same += 1
    return n_same >= 3


def _fact_get(f: Any, key: str, default: Any = None) -> Any:
    if isinstance(f, dict):
        return f.get(key, default)
    return getattr(f, key, default)


def _lite_rows(world: Any) -> list[dict[str, Any]]:
    fn = getattr(world, "chapters_lite", None)
    if not callable(fn):
        return []
    try:
        rows = fn() or []
    except Exception as exc:
        _log.warning("chapters_lite failed: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, dict):
            out.append(r)
    return out


def _row_for_seq(rows: list[dict[str, Any]], seq: int) -> dict[str, Any]:
    want = int(seq)
    for r in rows:
        try:
            if int(r.get("seq") or 0) == want:
                return r
        except (TypeError, ValueError):
            continue
    return {}


def playbook_volume_outline(world: Any, seq: int, rows: list[dict[str, Any]]) -> str:
    row = _row_for_seq(rows, seq)
    vol_id = str(row.get("volume") or "").strip()
    intro = ""
    title = ""
    fn = getattr(world, "list_volumes", None)
    if callable(fn):
        try:
            vols = fn() or []
        except Exception:
            vols = []
        for v in vols:
            if not isinstance(v, dict):
                continue
            vid = str(v.get("id") or "").strip()
            if vol_id and (vid == vol_id or vid.endswith(":" + vol_id) or vol_id.endswith(vid)):
                title = str(v.get("title") or "").strip()
                intro = strip_seed_pad(str(v.get("intro") or ""))[:_VOLUME_INTRO_BUDGET]
                break
    if not intro and not title:
        return ""
    if title and intro:
        return f"本卷《{title}》在办的事：{intro}"
    if intro:
        return f"本卷在办的事：{intro}"
    return f"本卷《{title}》"


def playbook_chapter_duty(seq: int, rows: list[dict[str, Any]]) -> str:
    row = _row_for_seq(rows, seq)
    title = str(row.get("title") or "").strip()
    syn = str(row.get("synopsis") or "").strip()
    generic = synopsis_is_generic(rows, seq, syn)
    peeled = strip_seed_pad(syn)
    if title and peeled and not generic:
        return f"这一章《{title}》要办的：{peeled}"
    if title:
        return f"这一章《{title}》"
    if peeled and not generic:
        return peeled
    return ""


def playbook_north_star(world: Any) -> str:
    getter = getattr(world, "get_intent", None)
    if not callable(getter):
        return ""
    try:
        intent = getter() or {}
    except Exception:
        intent = {}
    if not isinstance(intent, dict):
        intent = {}
    ns = strip_seed_pad(str(intent.get("north_star") or ""))
    if ns:
        return ns[:240]
    feeling = str(intent.get("reader_feeling") or "").strip()
    arc = str(intent.get("emotional_arc") or "").strip()
    parts: list[str] = []
    if feeling:
        parts.append(f"读完要留下：{feeling}")
    if arc:
        parts.append(f"弧：{arc}")
    return " ".join(parts)[:240]


def playbook_recent_duty_summary(frozen: Any, seq: int) -> str:
    fn = getattr(frozen, "get_frozen", None)
    if not callable(fn):
        return ""
    lines: list[str] = []
    for i in (int(seq) - 1, int(seq) - 2, int(seq) - 3):
        if i < 1:
            continue
        try:
            rec = fn("duty_card", i)
        except Exception:
            rec = None
        if not isinstance(rec, dict):
            continue
        happen = str(rec.get("must_happen") or "").strip()
        bill = str(rec.get("bill") or "").strip()
        if happen or bill:
            lines.append(f"第{i}章：办「{happen}」。账：「{bill}」。")
    return "\n".join(lines)


def playbook_recent_scene_summary(frozen: Any, seq: int) -> str:
    fn = getattr(frozen, "get_frozen", None)
    if not callable(fn):
        return ""
    lines: list[str] = []
    for i in (int(seq) - 1, int(seq) - 2, int(seq) - 3):
        if i < 1:
            continue
        try:
            rec = fn("chapter_play", i)
        except Exception:
            rec = None
        if not isinstance(rec, dict):
            continue
        text = str(rec.get("text") or "").strip().replace("\n", " ")
        if text:
            lines.append(f"第{i}章：{text[:80]}")
    return "\n".join(lines)


def _needles(focalizer: str, title: str, syn: str) -> list[str]:
    raw = " ".join([
        str(focalizer or "").replace("role:", "").strip(),
        str(title or "").strip(),
        strip_seed_pad(syn),
    ])
    out: list[str] = []
    seen: set[str] = set()
    for part in raw.split():
        p = part.strip()
        if len(p) >= 2 and p not in seen:
            seen.add(p)
            out.append(p)
    collapsed = _collapse_ws(raw)
    if len(collapsed) >= 2 and collapsed not in seen:
        out.append(collapsed)
    return out


def playbook_codex_recall(
    world: Any, seq: int, focalizer: str, *, rows: list[dict[str, Any]] | None = None,
) -> str:
    row = _row_for_seq(rows or [], seq)
    title = str(row.get("title") or "")
    syn = str(row.get("synopsis") or "")
    generic = synopsis_is_generic(rows, seq, syn)
    needles = _needles(focalizer, title, "" if generic else syn)
    facts: list[Any] = []
    fn = getattr(world, "facts_at", None)
    if callable(fn):
        try:
            facts = list(fn(int(seq)) or [])
        except Exception as exc:
            _log.warning("facts_at failed: %s", exc)
            facts = []
    public: list[Any] = [f for f in facts if _fact_get(f, "secret") is not True]

    def _hit(blob: str) -> bool:
        return any(n in blob for n in needles)

    matched = [
        f for f in public
        if _hit(f"{_fact_get(f, 'entity_id')}|{_fact_get(f, 'attribute')}|{_fact_get(f, 'value')}")
    ]
    if len(matched) < 2:
        matched = sorted(
            public,
            key=lambda f: (str(_fact_get(f, "entity_id") or ""), str(_fact_get(f, "attribute") or "")),
        )[:4]
    rules: list[Any] = []
    rfn = getattr(world, "list_world_rules", None)
    if callable(rfn):
        try:
            rules = list(rfn() or [])
        except Exception:
            rules = []
    rule_hits = [
        r for r in rules
        if isinstance(r, dict) and _hit(f"{r.get('name') or ''}|{r.get('cost') or ''}")
    ]
    if not rule_hits:
        rule_hits = sorted(
            [r for r in rules if isinstance(r, dict)],
            key=lambda r: str(r.get("name") or ""),
        )[:3]
    else:
        rule_hits = rule_hits[:3]
    parts: list[str] = ["这些已经为真，不许另造。"]
    for f in matched:
        eid = str(_fact_get(f, "entity_id") or "").replace("role:", "")
        attr = strip_seed_pad(str(_fact_get(f, "attribute") or ""))
        val = strip_seed_pad(str(_fact_get(f, "value") or ""))
        if attr or val:
            parts.append(f"{eid} / {attr}：{val}")
    for r in rule_hits:
        name = strip_seed_pad(str(r.get("name") or ""))
        cost = strip_seed_pad(str(r.get("cost") or ""))
        if name:
            parts.append(f"{name}（代价：{cost}）" if cost else name)
    text = "\n".join(parts)
    if text == "这些已经为真，不许另造。":
        return ""
    return text[:_CODEX_BUDGET]


def playbook_epistemic_history(frozen: Any, seq: int) -> str:
    if int(seq) <= 1:
        return ""
    fn = getattr(frozen, "get_frozen", None)
    if not callable(fn):
        return ""
    try:
        rec = fn("chapter_deduce", int(seq) - 1)
    except Exception:
        rec = None
    if not isinstance(rec, dict):
        return ""
    lines: list[str] = []
    for c in rec.get("characters") or []:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        known = str(c.get("known") or "").strip()[:80]
        believed = str(c.get("believed") or "").strip()[:80]
        if cid:
            lines.append(f"{cid} 知道：{known} 以为：{believed}")
    return "\n".join(lines)[:600]


def playbook_prev_prose_tail(world: Any, seq: int) -> str:
    if int(seq) <= 1:
        return ""
    fn = getattr(world, "recent_proses", None)
    if not callable(fn):
        return ""
    try:
        rows = fn(before_seq=int(seq), k=1) or []
    except TypeError:
        try:
            rows = fn(int(seq), 1) or []
        except Exception:
            return ""
    except Exception:
        return ""
    if not rows:
        return ""
    prose = str((rows[-1] or {}).get("prose") or "")
    return prose[-400:] if prose else ""


def build_ctx(
    store: Any,
    seq: int,
    *,
    focalizer: str = "",
    extra: dict[str, Any] | None = None,
    playbook: Any | None = None,
) -> dict[str, Any]:
    world = store
    frozen = playbook if playbook is not None else store
    rows = _lite_rows(world)
    row = _row_for_seq(rows, seq)
    foc = str(focalizer or "").strip() or str(row.get("focalizer") or "").strip()
    cards = cast_cards(world)
    prev_state = prev_chapter_state(frozen, seq)
    volume_outline = ""
    north_star = ""
    chapter_duty = ""
    recent_duty = ""
    recent_scene = ""
    codex = ""
    epistemic = ""
    prose_tail = ""
    try:
        volume_outline = playbook_volume_outline(world, seq, rows)
    except Exception as exc:
        _log.warning("volume_outline failed: %s", exc)
    try:
        north_star = playbook_north_star(world)
    except Exception as exc:
        _log.warning("north_star failed: %s", exc)
    try:
        chapter_duty = playbook_chapter_duty(seq, rows)
    except Exception as exc:
        _log.warning("chapter_duty failed: %s", exc)
    try:
        recent_duty = playbook_recent_duty_summary(frozen, seq)
    except Exception as exc:
        _log.warning("recent_duty_summary failed: %s", exc)
    try:
        recent_scene = playbook_recent_scene_summary(frozen, seq)
    except Exception as exc:
        _log.warning("recent_scene_summary failed: %s", exc)
    try:
        codex = playbook_codex_recall(world, seq, foc, rows=rows)
    except Exception as exc:
        _log.warning("codex_recall failed: %s", exc)
    try:
        epistemic = playbook_epistemic_history(frozen, seq)
    except Exception as exc:
        _log.warning("epistemic_history failed: %s", exc)
    try:
        prose_tail = playbook_prev_prose_tail(world, seq)
    except Exception as exc:
        _log.warning("prev_prose_tail failed: %s", exc)
    ctx: dict[str, Any] = {
        "seq": int(seq),
        "focalizer": foc,
        "available_cast": available_cast(world),
        "cast_cards": cards,
        "available_lines": available_lines(world),
        "prev_hook_quote": prev_hook_quote(frozen, seq),
        "secret_list": secret_list(world),
        "prev_state": prev_state,
        "imagery": book_imagery(world),
        "gender_roster": gender_roster(prev_state, cards),
        "volume_outline": volume_outline,
        "north_star": north_star,
        "chapter_duty": chapter_duty,
        "recent_duty_summary": recent_duty,
        "recent_scene_summary": recent_scene,
        "codex_recall": codex,
        "characters_epistemic_history": epistemic,
        "prev_prose_tail": prose_tail,
    }
    if extra:
        ctx.update(extra)
    _log.info(
        "build_ctx seq=%s lens volume=%s north=%s chapter_duty=%s recent_duty=%s recent_scene=%s codex=%s",
        seq,
        len(volume_outline or ""),
        len(north_star or ""),
        len(chapter_duty or ""),
        len(recent_duty or ""),
        len(recent_scene or ""),
        len(codex or ""),
    )
    return ctx
