"""Assemble generator/judge context from a live store. Soft-fail on missing pieces."""
from __future__ import annotations

import logging
import re
from typing import Any

from scribe3.recall_service import budget_for as _budget_for

_log = logging.getLogger("scribe3.playbook.context")

_LIVE_PAD = "此句只为把设定写够，说明处境、代价和不能拆穿的事。"
_OLD_PAD = "这不是口号，是巷里炉灰和铜腥贴在骨头上的实感。"
GENERIC_SYNOPSIS_MIN = 16

_VOLUME_INTRO_BUDGET = _budget_for("volume_intro", 400)
_CODEX_BUDGET = _budget_for("playbook_codex", 800)
_LEDGER_BUDGET = _budget_for("ledger", 900)
_LEDGER_MAX_ROWS = 8
_LEDGER_DONE_KEEP = 2
_LEDGER_LATER_KEEP = 6
_LEDGER_KNOWN_SKIP = frozenset({
    "unassigned_or_empty",
    "single_chapter",
    "no_synopses",
    "flag_off",
})
_STATUS_ZH = {"tonight": "今晚", "done": "已办", "later": "还没办"}


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


def _craft_skill_triggers(focalizer: str, secrets: list[str] | None) -> list[str]:
    """DED-19：关键场面强制带上技法，不靠模型自己想起。"""
    skills: list[str] = []
    if str(focalizer or "").strip():
        skills.append("限知视角")
    if secrets:
        if "限知视角" not in skills:
            skills.append("限知视角")
        skills.append("知情差")
    return skills


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
    rec = fn("chapter_state", int(seq) - 1) if callable(fn) else None
    if isinstance(rec, dict):
        return rec
    lister = getattr(store, "list_versions", None)
    if callable(lister):
        try:
            rows = lister("chapter_state", int(seq) - 1) or []
        except Exception:
            rows = []
        for rec in reversed(list(rows)):
            if not isinstance(rec, dict):
                continue
            if rec.get("degraded") or rec.get("status") in ("needs_human", "frozen"):
                return rec
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


def prev_stay(store: Any, seq: int) -> str | None:
    """上场责任卡没翻的处境。旧卡没 stay 不拦。"""
    if int(seq) <= 1:
        return None
    fn = getattr(store, "get_frozen", None)
    if not callable(fn):
        return None
    duty = fn("duty_card", int(seq) - 1)
    if not isinstance(duty, dict):
        return None
    stay = str(duty.get("stay") or "").strip()
    return stay or None


def prev_heat(store: Any, seq: int) -> str | None:
    """上场热闹像翻了的那一层。旧卡没 heat 不拦。"""
    if int(seq) <= 1:
        return None
    fn = getattr(store, "get_frozen", None)
    if not callable(fn):
        return None
    duty = fn("duty_card", int(seq) - 1)
    if not isinstance(duty, dict):
        return None
    heat = str(duty.get("heat") or "").strip()
    return heat or None


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
        "day": fields.get("day") or "还在过的日子",
        "said": fields.get("said") or "嘴上要的",
        "needed": fields.get("needed") or "真正缺的",
        "mask": fields.get("mask") or "先给的反面",
        "crack": fields.get("crack") or "破功的那一下",
        "real": fields.get("real") or "破完才落的真意",
        "eye": fields.get("eye") or fields.get("focalizer") or "沈烛若",
        "dist": fields.get("dist") or "near",
        "cut": fields.get("cut") or "空盏磕在井沿上",
        "one_line": fields.get("one_line") or "他把空盏摘下来",
        "keep": fields.get("keep") or "灯油不是自家攒的，空盏才露出来",
        "heat": fields.get("heat") or "井台上有人认了这盏油",
        "stay": fields.get("stay") or "灯还是空的，日子没翻",
        "owed": fields.get("owed") or "",
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


def _lite_rows(world: Any) -> tuple[list[dict[str, Any]], bool]:
    """返回 (rows, threw)。threw=True 才进 _guide_fail。"""
    fn = getattr(world, "chapters_lite", None)
    if not callable(fn):
        return [], False
    try:
        rows = fn() or []
    except Exception as exc:
        _log.warning("chapters_lite failed: %s", exc)
        return [], True
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, dict):
            out.append(r)
    return out, False


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


def _same_volume_id(a: str, b: str) -> bool:
    x = str(a or "").strip()
    y = str(b or "").strip()
    if not x or not y:
        return False
    return x == y or x.endswith(":" + y) or y.endswith(":" + x)


def _row_has_prose(row: dict[str, Any]) -> bool:
    if not isinstance(row, dict) or "has_prose" not in row:
        return False
    return row.get("has_prose") is True


def _ledger_eligible(rows: list[dict[str, Any]], seq: int) -> bool:
    cur = _row_for_seq(rows, seq)
    vol = str(cur.get("volume") or "").strip()
    if not vol:
        return False
    peers = [r for r in rows if _same_volume_id(str(r.get("volume") or ""), vol)]
    if len(peers) < 2:
        return False
    n_syn = 0
    for r in peers:
        syn = str(r.get("synopsis") or "")
        n = int(r.get("seq") or 0)
        if syn and not synopsis_is_generic(rows, n, syn):
            n_syn += 1
    return n_syn >= 2


def assemble_volume_ledger(
    world: Any,
    frozen: Any,
    seq: int,
    rows: list[dict[str, Any]],
) -> tuple[str, str]:
    """本卷台账近窗。返回 (人话文本, skip 原因)。不把卷纲折成钩子。"""
    try:
        from scribe3.feature_flags import flag_truthy
        if not flag_truthy("SCRIBE3_VOLUME_LEDGER"):
            return "", "flag_off"
    except Exception:
        pass
    cur = _row_for_seq(rows, seq)
    vol = str(cur.get("volume") or "").strip()
    if not vol:
        return "", "unassigned_or_empty"
    peers = [r for r in rows if _same_volume_id(str(r.get("volume") or ""), vol)]
    peers.sort(key=lambda r: int(r.get("seq") or 0))
    if len(peers) < 2:
        return "", "single_chapter"
    want = int(seq)
    items: list[dict[str, Any]] = []
    for r in peers:
        try:
            n = int(r.get("seq") or 0)
        except (TypeError, ValueError):
            continue
        if n <= 0:
            continue
        if n == want:
            status = "tonight"
        elif _row_has_prose(r):
            status = "done"
        else:
            status = "later"
        raw_syn = str(r.get("synopsis") or "")
        items.append({
            "seq": n,
            "title": str(r.get("title") or "").strip(),
            "raw_syn": raw_syn,
            "synopsis": strip_seed_pad(raw_syn).replace("\n", " ").strip(),
            "status": status,
        })
    fn = getattr(frozen, "get_frozen", None)
    if callable(fn):
        for it in items:
            if it["status"] != "later":
                continue
            if abs(int(it["seq"]) - want) > 2:
                continue
            try:
                rec = fn("duty_card", int(it["seq"]))
            except Exception:
                rec = None
            if isinstance(rec, dict) and (
                str(rec.get("must_happen") or "").strip() or str(rec.get("bill") or "").strip()
            ):
                it["status"] = "done"
    n_syn = 0
    for it in items:
        if it["synopsis"] and not synopsis_is_generic(rows, it["seq"], it["raw_syn"]):
            n_syn += 1
    if n_syn < 2:
        return "", "no_synopses"
    tonight = [it for it in items if it["status"] == "tonight"]
    done = sorted((it for it in items if it["status"] == "done"), key=lambda x: x["seq"])[-_LEDGER_DONE_KEEP:]
    later = sorted((it for it in items if it["status"] == "later"), key=lambda x: x["seq"])[:_LEDGER_LATER_KEEP]
    keep = {it["seq"] for it in tonight + done + later}
    window = [it for it in items if it["seq"] in keep][:_LEDGER_MAX_ROWS]
    lines: list[str] = []
    for it in window:
        zh = _STATUS_ZH.get(it["status"], "还没办")
        title = it["title"] or f"第{it['seq']}章"
        syn = it["synopsis"]
        if syn:
            lines.append(f"第{it['seq']}章《{title}》〔{zh}〕：{syn}")
        else:
            lines.append(f"第{it['seq']}章《{title}》〔{zh}〕")
    text = "\n".join(lines)
    if len(text) > _LEDGER_BUDGET:
        text = text[:_LEDGER_BUDGET]
    return text, ""


def playbook_volume_ledger(
    world: Any, frozen: Any, seq: int, rows: list[dict[str, Any]],
) -> str:
    text, _reason = assemble_volume_ledger(world, frozen, seq, rows)
    return text


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
    lookback = 3
    try:
        from scribe3.feature_flags import get_flag
        lookback = min(max(1, int(get_flag("SCRIBE3_DUTY_SUMMARY_LOOKBACK") or 3)), 10)
    except Exception:
        lookback = 3
    lines: list[str] = []
    for i in range(int(seq) - 1, int(seq) - 1 - lookback, -1):
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


def _rule_lines(world: Any, needles: list[str], *, pad: bool) -> list[str]:
    rules: list[Any] = []
    rfn = getattr(world, "list_world_rules", None)
    if callable(rfn):
        try:
            rules = list(rfn() or [])
        except Exception:
            rules = []

    def _hit(blob: str) -> bool:
        return any(n in blob for n in needles)

    rule_hits = [
        r for r in rules
        if isinstance(r, dict) and _hit(f"{r.get('name') or ''}|{r.get('cost') or ''}")
    ]
    if not rule_hits:
        pool = [r for r in rules if isinstance(r, dict)]
        rule_hits = (sorted(pool, key=lambda r: str(r.get("name") or "")) if pad else pool)[:3]
    else:
        rule_hits = rule_hits[:3]
    lines: list[str] = []
    for r in rule_hits:
        name = strip_seed_pad(str(r.get("name") or ""))
        cost = strip_seed_pad(str(r.get("cost") or ""))
        if name:
            lines.append(f"{name}（代价：{cost}）" if cost else name)
    return lines


def _legacy_codex_recall(world: Any, seq: int, needles: list[str], public: list[Any]) -> str:
    """紧急回退依赖。删码待旗退役。"""
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
    parts: list[str] = ["这些已经为真，不许另造。"]
    for f in matched:
        eid = str(_fact_get(f, "entity_id") or "").replace("role:", "")
        attr = strip_seed_pad(str(_fact_get(f, "attribute") or ""))
        val = strip_seed_pad(str(_fact_get(f, "value") or ""))
        if attr or val:
            parts.append(f"{eid} / {attr}：{val}")
    parts.extend(_rule_lines(world, needles, pad=True))
    text = "\n".join(parts)
    if text == "这些已经为真，不许另造。":
        return ""
    return text[:_CODEX_BUDGET]


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
    from scribe3.feature_flags import flag_truthy
    legacy_text = _legacy_codex_recall(world, seq, needles, public)
    if not flag_truthy("SCRIBE3_RECALL_PLAYBOOK"):
        text = legacy_text  # 紧急回退口，关旗才走
    else:
        text = ""
        try:
            from scribe3.recall_service import pack_text, recall
            pack = recall(
                world,
                chapter=int(seq),
                focalizer=focalizer,
                query=" ".join(needles),
                budget_tag="playbook_codex",
            )
            parts: list[str] = []
            body = pack_text(pack)
            if body:
                parts.append(body)
            elif public:
                try:
                    from scribe3.pipeline_trace_hooks import note_guide_missing
                    note_guide_missing(
                        "codex_recall_empty",
                        source="playbook",
                        budget_tag="playbook_codex",
                    )
                except Exception:
                    pass
            rules = _rule_lines(world, needles, pad=False)
            if rules:
                if not parts:
                    parts.append("这些已经为真，不许另造。")
                parts.extend(rules)
            text = "\n".join(parts)[:_CODEX_BUDGET]
        except Exception as exc:
            _log.info("codex_recall hub skip: %s", type(exc).__name__)
            try:
                from scribe3.pipeline_trace_hooks import note_guide_missing
                note_guide_missing("codex_recall_overlay_skip")
            except Exception:
                pass
            text = legacy_text  # 降级安全网，非旧路
    try:
        if flag_truthy("SCRIBE3_RECALL_SHADOW"):
            from scribe3.recall_service import shadow_diff
            shadow_diff(
                world, seq, focalizer, legacy_text,
                query=" ".join(needles), path="playbook",
            )
    except Exception:
        pass
    return text


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


GUIDE_SLOT_KEYS = (
    "volume_outline",
    "volume_ledger",
    "north_star",
    "chapter_duty",
    "recent_duty_summary",
    "recent_scene_summary",
    "codex_recall",
    "characters_epistemic_history",
    "prev_prose_tail",
)


def _revision_letter_digest(world: Any, seq: int) -> str:
    for name in ("get_revision_letter", "latest_revision_letter", "get_letter"):
        fn = getattr(world, name, None)
        if callable(fn):
            try:
                row = fn(seq) if fn.__code__.co_argcount >= 2 else fn()
            except TypeError:
                try:
                    row = fn()
                except Exception:
                    row = None
            except Exception:
                row = None
            if isinstance(row, dict):
                return str(row.get("digest") or row.get("text") or row.get("body") or "")[:800]
            if row:
                return str(row)[:800]
    try:
        from scribe3.experience.letter import build_revision_letter
        from scribe3.experience.state import get_letter_overlay
        work = str(getattr(world, "db_name", None) or "main")
        letter = build_revision_letter(
            world, work=work, status_overlay=get_letter_overlay(work),
        )
        items = letter.get("items") if isinstance(letter, dict) else None
        if not items:
            return ""
        open_qs = []
        for it in items:
            if not isinstance(it, dict):
                continue
            if it.get("status") and it.get("status") != "open":
                continue
            q = str(it.get("question") or it.get("kind") or "").strip()
            if q:
                open_qs.append(q)
        return "；".join(open_qs)[:800]
    except Exception:
        return ""


def _scene_grid_digest(world: Any, seq: int) -> str:
    fn = getattr(world, "get_scene_grid", None)
    if callable(fn):
        try:
            row = fn(seq)
            if isinstance(row, dict):
                return _format_scene_grid(row, seq)
            if row:
                return str(row)[:800]
        except Exception:
            pass
    try:
        from scribe3.experience.state import get_scene_grid
        work = str(getattr(world, "db_name", None) or "main")
        grid = get_scene_grid(work, int(seq)) or {}
        return _format_scene_grid(grid, seq)
    except Exception:
        return ""


def _format_scene_grid(grid: dict, seq: int) -> str:
    from scribe3.experience.scene_grid import diagnose_scene_grid, normalize_scene_grid
    g = normalize_scene_grid(grid)
    issues = diagnose_scene_grid(g, seq=seq) or []
    filled = [f"{k}:{g.get(k)}" for k in ("goal", "conflict", "disaster", "reaction", "dilemma", "decision") if g.get(k)]
    msgs = [str(i.get("message") or i.get("code") or "") for i in issues if isinstance(i, dict)]
    parts = []
    if filled:
        parts.append("；".join(filled))
    if msgs:
        parts.append("断链：" + "；".join(m for m in msgs if m))
    return " ".join(parts)[:800]


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
    rows, lite_threw = _lite_rows(world)
    guide_fail: list[str] = []
    if lite_threw:
        guide_fail.append("chapters_lite")
    row = _row_for_seq(rows, seq)
    foc = str(focalizer or "").strip() or str(row.get("focalizer") or "").strip()
    cards = cast_cards(world)
    prev_state = prev_chapter_state(frozen, seq)
    def _slot(name: str, fn):
        try:
            return fn()
        except Exception as exc:
            from scribe3.soft_fail import soft_fail
            soft_fail(f"build_ctx.{name}", exc, logger=_log)
            guide_fail.append(name)
            try:
                from scribe3.pipeline_trace_hooks import note_guide_missing
                note_guide_missing(name)
            except Exception:
                pass
            return ""

    from scribe3.context_snapshot import snapshot_get_or_set
    cache_key = f"{id(world)}:{getattr(world, 'db_name', '')}:{seq}:{foc}"

    def _cached_slot(name, fn):
        return snapshot_get_or_set(f"{cache_key}:{name}", lambda: _slot(name, fn))

    volume_outline = _cached_slot("volume_outline", lambda: playbook_volume_outline(world, seq, rows))
    north_star = _cached_slot("north_star", lambda: playbook_north_star(world))
    chapter_duty = _cached_slot("chapter_duty", lambda: playbook_chapter_duty(seq, rows))
    recent_duty = _cached_slot("recent_duty_summary", lambda: playbook_recent_duty_summary(frozen, seq))
    recent_scene = _cached_slot("recent_scene_summary", lambda: playbook_recent_scene_summary(frozen, seq))
    codex = _cached_slot("codex_recall", lambda: playbook_codex_recall(world, seq, foc, rows=rows))
    epistemic = _slot(
        "characters_epistemic_history",
        lambda: playbook_epistemic_history(frozen, seq),
    )
    prose_tail = _slot("prev_prose_tail", lambda: playbook_prev_prose_tail(world, seq))
    volume_ledger = ""
    ledger_skip = ""
    try:
        volume_ledger, ledger_skip = assemble_volume_ledger(world, frozen, seq, rows)
    except Exception as exc:
        from scribe3.soft_fail import soft_fail
        soft_fail("build_ctx.volume_ledger", exc, logger=_log)
        guide_fail.append("volume_ledger")
        volume_ledger = ""
        ledger_skip = "threw"
    else:
        if (
            not volume_ledger
            and ledger_skip not in _LEDGER_KNOWN_SKIP
            and _ledger_eligible(rows, seq)
        ):
            guide_fail.append("volume_ledger")
            _log.warning("volume_ledger empty despite eligible seq=%s skip=%s", seq, ledger_skip)
        elif ledger_skip:
            _log.info("volume_ledger skip seq=%s reason=%s", seq, ledger_skip)
    ctx: dict[str, Any] = {
        "seq": int(seq),
        "focalizer": foc,
        "available_cast": available_cast(world),
        "cast_cards": cards,
        "available_lines": available_lines(world),
        "prev_hook_quote": prev_hook_quote(frozen, seq),
        "prev_stay": prev_stay(frozen, seq),
        "prev_heat": prev_heat(frozen, seq),
        "secret_list": secret_list(world),
        "prev_state": prev_state,
        "imagery": book_imagery(world),
        "gender_roster": gender_roster(prev_state, cards),
        "volume_outline": volume_outline,
        "volume_ledger": volume_ledger,
        "north_star": north_star,
        "chapter_duty": chapter_duty,
        "recent_duty_summary": recent_duty,
        "recent_scene_summary": recent_scene,
        "codex_recall": codex,
        "characters_epistemic_history": epistemic,
        "prev_prose_tail": prose_tail,
        "revision_letter_digest": _cached_slot(
            "revision_letter_digest",
            lambda: _revision_letter_digest(world, seq),
        ),
        "scene_grid": _cached_slot(
            "scene_grid",
            lambda: _scene_grid_digest(world, seq),
        ),
        "craft_skills": _craft_skill_triggers(foc, secret_list(world)),
        "_guide_fail": list(guide_fail),
        "_volume_ledger_skip": ledger_skip,
    }
    if extra:
        ctx.update(extra)
    if ctx.get("_guide_fail"):
        ctx["safety_note"] = "⚠️ 部分设定数据加载失败，请勿编造未提供的角色/事件信息。"
    _log.info(
        "build_ctx seq=%s lens volume=%s ledger=%s north=%s chapter_duty=%s recent_duty=%s recent_scene=%s codex=%s epistemic=%s prose_tail=%s fail=%s",
        seq,
        len(volume_outline or ""),
        len(volume_ledger or ""),
        len(north_star or ""),
        len(chapter_duty or ""),
        len(recent_duty or ""),
        len(recent_scene or ""),
        len(codex or ""),
        len(epistemic or ""),
        len(prose_tail or ""),
        ctx.get("_guide_fail") or [],
    )
    return ctx
