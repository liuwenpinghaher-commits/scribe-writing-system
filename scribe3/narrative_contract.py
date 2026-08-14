"""叙事合同 SSOT（narrative-mainline · 纯函数为主）。

设计：docs/plans/2026-08-13-narrative-mainline.md R2
场面 briefing / 咬合 / 章差序：docs/plans/2026-08-13-scene-contract-unify.md R6
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA = "narrative_contract.v1"
CONTRACT_MIN_FIELD_CHARS = 8
BEAT_MIN_CHARS = 6
PROP_LIKE_MAX = 6

CONFLICT_LEX: frozenset[str] = frozenset({
    "拦", "讨", "逼", "拒", "抵", "揭", "追", "逃", "威胁", "债", "选",
    "对峙", "交锋", "挡住", "拦住", "不肯", "被迫", "代价", "两难",
    "夺", "抢", "锁", "封", "跪", "咬", "撞", "踢", "挡", "压",
    "要挟", "勒索", "撕", "毁", "破", "杀", "伤", "骗", "瞒",
    "扯", "跟", "缠", "撵", "拦下", "讨债",
})

# 虚词/体标记：仅诊断，不得单独使 shape_ok
ACTION_HINT = ("了", "着", "住", "过", "来", "去", "给", "把", "被", "让")

_PLACEHOLDERS = frozenset({
    "无", "有", "n/a", "暂无", "待补", "TODO", "无代价", "-", "—",
    "待填", "xxx", "tbd",
})

_FIELD_KEYS = ("desire", "obstacle", "turn", "cost")

_SLOGAN_EXACT = frozenset({
    "查明真相", "活下去", "局势", "命运", "局势/对立面", "对立面",
    "对立面/外力", "付出代价", "心情沉重",
})
_DRIVE_TURN_TEMPLATE_RE = re.compile(r"因[「「].{0,40}[」」].*局势被迫转向")


def cn_len(s: str) -> int:
    from scribe3.llm_visible import strip_thinking_markup
    return len(re.sub(r"\s+", "", strip_thinking_markup(s or "").strip()))


def cn_strip(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def beat_text(b: Any) -> str:
    if isinstance(b, str):
        return b.strip()
    if isinstance(b, dict):
        return str(b.get("text") or b.get("beat") or b.get("action") or "").strip()
    return ""


def beat_shape(text: str) -> tuple[bool, list[str]]:
    """R2: shape_ok ⟺ CONFLICT_LEX 命中且 cn_len≥BEAT_MIN；ACTION_HINT 不得单独成立。

    短串分流（设计表 #4–#7 / #10）：
    - 无冲突词 + 短名词标签 → prop_like（湿脚印）
    - 无冲突词 + 虚词动作 → action_hint_only（他走了）
    - 有冲突词但过短 → too_short（对峙）
    """
    t = cn_strip(text)
    if not t:
        return False, ["empty"]
    if t in _PLACEHOLDERS:
        return False, ["placeholder"]
    n = cn_len(t)
    has_lex = any(k in t for k in CONFLICT_LEX)
    has_hint = any(a in t for a in ACTION_HINT)
    if n < BEAT_MIN_CHARS:
        if has_lex:
            return False, ["too_short"]
        if has_hint:
            return False, ["action_hint_only"]
        # 短静物/道具标签（ch4）
        return False, ["prop_like"]
    if has_lex:
        return True, []
    if n <= PROP_LIKE_MAX:
        return False, ["prop_like"]
    if has_hint:
        return False, ["action_hint_only"]
    return False, ["no_conflict_clue"]


def conflict_beats_ok(items: list | None) -> dict[str, Any]:
    texts = [beat_text(b) for b in (items or [])]
    texts = [t for t in texts if t.strip()]
    shaped: list[dict[str, Any]] = []
    prop_like: list[str] = []
    for t in texts:
        ok, rs = beat_shape(t)
        shaped.append({"text": t, "shape_ok": ok, "reasons": rs})
        if "prop_like" in rs or (not ok and "too_short" in rs):
            prop_like.append(t)
    n_ok = sum(1 for x in shaped if x["shape_ok"])
    return {
        "ok": n_ok >= 1,
        "total": len(texts),
        "valid": n_ok,
        "prop_like": prop_like,
        "items": shaped,
    }


def validate_narrative_contract(raw: Any) -> dict[str, Any]:
    """Validate contract dict. Returns normalized contract with validation block."""
    errors: list[str] = []
    warnings: list[str] = []
    if raw is None:
        return {
            "schema": SCHEMA,
            "version": 1,
            "desire": "",
            "obstacle": "",
            "turn": "",
            "cost": "",
            "conflict_beats": None,
            "bindings": {},
            "validation": {"ok": False, "errors": ["missing_contract"], "warnings": []},
            "source": "empty",
            "locked": False,
        }
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return {
                "schema": SCHEMA,
                "version": 1,
                "desire": "",
                "obstacle": "",
                "turn": "",
                "cost": "",
                "conflict_beats": None,
                "bindings": {},
                "validation": {
                    "ok": False,
                    "errors": ["contract_not_json"],
                    "warnings": [],
                },
                "source": "error",
                "locked": False,
            }
    if not isinstance(raw, dict):
        return {
            "schema": SCHEMA,
            "version": 1,
            "desire": "",
            "obstacle": "",
            "turn": "",
            "cost": "",
            "conflict_beats": None,
            "bindings": {},
            "validation": {
                "ok": False,
                "errors": ["contract_not_dict"],
                "warnings": [],
            },
            "source": "error",
            "locked": False,
        }

    out: dict[str, Any] = {
        "schema": str(raw.get("schema") or SCHEMA),
        "version": int(raw.get("version") or 1),
        "desire": str(raw.get("desire") or "").strip(),
        "obstacle": str(raw.get("obstacle") or "").strip(),
        "turn": str(raw.get("turn") or "").strip(),
        "cost": str(raw.get("cost") or "").strip(),
        "conflict_beats": raw.get("conflict_beats"),
        "bindings": raw.get("bindings") if isinstance(raw.get("bindings"), dict) else {},
        "source": str(raw.get("source") or "author"),
        "locked": bool(raw.get("locked")),
    }
    for k in _FIELD_KEYS:
        v = out[k]
        if not v or cn_len(v) < CONTRACT_MIN_FIELD_CHARS:
            errors.append(f"field_short:{k}")
        elif cn_strip(v) in _PLACEHOLDERS:
            errors.append(f"field_placeholder:{k}")

    cb = out.get("conflict_beats")
    if cb is not None and not isinstance(cb, list):
        errors.append("conflict_beats_not_list")
        out["conflict_beats"] = None

    ok = len(errors) == 0
    out["validation"] = {"ok": ok, "errors": errors, "warnings": warnings}
    return out


def migrate_contract_from_drive(drive: Any) -> dict[str, Any]:
    """Best-effort assemble contract from narrative_drive (compat)."""
    d = drive if isinstance(drive, dict) else {}
    desire = str(
        d.get("want") or d.get("goal") or d.get("inciting") or d.get("desire") or ""
    ).strip()
    obstacle = str(
        d.get("opposition") or d.get("obstacle") or d.get("force") or ""
    ).strip()
    turn = str(d.get("turn") or d.get("event") or d.get("deadline") or "").strip()
    cost = str(d.get("cost") or d.get("stake") or d.get("price") or "").strip()
    raw = {
        "schema": SCHEMA,
        "version": 1,
        "desire": desire,
        "obstacle": obstacle,
        "turn": turn,
        "cost": cost,
        "conflict_beats": None,
        "bindings": {"narrative_drive_fp": str(d.get("fp") or "")[:32]},
        "source": "assembled",
        "locked": False,
    }
    c = validate_narrative_contract(raw)
    if not c["validation"]["ok"]:
        c["validation"]["warnings"] = list(c["validation"].get("warnings") or []) + [
            "assembled_from_drive_incomplete"
        ]
    return c


def project_drive_from_contract(contract: Any) -> dict[str, Any]:
    """Author-primary: synthesize a minimal drive inject blob from contract."""
    c = validate_narrative_contract(contract)
    return {
        "schema": "narrative_drive.projected",
        "inciting": c.get("desire") or "",
        "opposition": c.get("obstacle") or "",
        "turn": c.get("turn") or "",
        "cost": c.get("cost") or "",
        "source": "contract",
    }


def format_contract_block(contract: Any, *, max_chars: int = 180) -> str:
    c = validate_narrative_contract(contract)
    if not any(c.get(k) for k in _FIELD_KEYS):
        return ""
    lines = [
        "【叙事合同】",
        f"欲望：{(c.get('desire') or '')[:40]}",
        f"阻力：{(c.get('obstacle') or '')[:40]}",
        f"回合：{(c.get('turn') or '')[:40]}",
        f"代价：{(c.get('cost') or '')[:40]}",
    ]
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[: max_chars - 1] + "…"
    return text


def resolve_beat_items(
    contract: dict | None,
    chapter_beats: list | None,
) -> list:
    """conflict_beats if non-empty list else chapter.beats."""
    c = contract if isinstance(contract, dict) else {}
    cb = c.get("conflict_beats")
    if isinstance(cb, list) and any(beat_text(x) for x in cb):
        return cb
    return list(chapter_beats or [])


def contract_has_scene_fields(contract: Any) -> bool:
    """任一 desire/obstacle/turn/cost 非空（与 format_story_contract_head 同一谓词）。"""
    c = validate_narrative_contract(contract) if contract is not None else validate_narrative_contract(None)
    return any(str(c.get(k) or "").strip() for k in _FIELD_KEYS)


def contract_content_fp(contract: Any) -> str:
    """落库四义 + bindings.evidence_must_show。无 traces 第二参。空四义+空痕迹 → 稳定空指纹。"""
    c = validate_narrative_contract(contract)
    bindings = c.get("bindings") if isinstance(c.get("bindings"), dict) else {}
    raw_tr = bindings.get("evidence_must_show")
    if isinstance(raw_tr, list):
        traces = [str(t).strip() for t in raw_tr if str(t).strip()][:3]
    elif isinstance(raw_tr, str) and raw_tr.strip():
        traces = [raw_tr.strip()]
    else:
        traces = []
    payload = {
        "desire": cn_strip(c.get("desire") or ""),
        "obstacle": cn_strip(c.get("obstacle") or ""),
        "turn": cn_strip(c.get("turn") or ""),
        "cost": cn_strip(c.get("cost") or ""),
        "traces": traces,
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _drive_str(drive: Any, *path: str) -> str:
    """沿嵌套路径取字符串；中段为 dict 则继续；叶子为 dict 则空串（禁 str(dict)）。"""
    cur: Any = drive
    for p in path:
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(p)
    if isinstance(cur, dict) or cur is None:
        return ""
    return str(cur).strip()


def _clip_brief(s: Any, n: int) -> str:
    raw = str(s or "").strip()
    if n and len(raw) > n:
        return raw[: n - 1] + "…"
    return raw


def is_drive_template_turn(text: str) -> bool:
    t = str(text or "").strip()
    return bool(t) and (
        "局势被迫转向" in t or bool(_DRIVE_TURN_TEMPLATE_RE.search(t))
    )


def _is_slogan_or_placeholder(text: str) -> bool:
    t = cn_strip(text)
    if not t:
        return True
    if t in _PLACEHOLDERS or t in _SLOGAN_EXACT:
        return True
    return False


def _share_8(a: str, b: str) -> bool:
    sa, sb = cn_strip(a), cn_strip(b)
    if not sa or not sb:
        return False
    if sa == sb:
        return True
    if len(sa) >= 8 and sa in sb:
        return True
    if len(sb) >= 8 and sb in sa:
        return True
    if len(sa) >= 8 and len(sb) >= 8:
        for i in range(len(sa) - 7):
            if sa[i : i + 8] in sb:
                return True
    return False


def check_scene_lock(
    contract: dict | None,
    *,
    prev_contract: dict | None = None,
) -> dict[str, Any]:
    """只 advisory。不改 validation.ok / 不进 may_claim_story。"""
    warnings: list[dict[str, str]] = []
    c = contract if isinstance(contract, dict) else {}
    desire = str(c.get("desire") or "").strip()
    obstacle = str(c.get("obstacle") or "").strip()
    turn = str(c.get("turn") or "").strip()
    bindings = c.get("bindings") if isinstance(c.get("bindings"), dict) else {}
    raw_tr = bindings.get("evidence_must_show")
    if raw_tr is None:
        raw_tr = c.get("traces")
    traces: list[str] = []
    if isinstance(raw_tr, list):
        traces = [str(t).strip() for t in raw_tr if str(t).strip()]
    elif isinstance(raw_tr, str) and raw_tr.strip():
        traces = [raw_tr.strip()]

    if obstacle and (
        _is_slogan_or_placeholder(obstacle)
        or cn_strip(obstacle) in ("局势", "命运", "局势/对立面", "对立面", "对立面/外力")
    ):
        warnings.append({
            "code": "obstacle_not_on_desire",
            "message": "阻力拦不住这场欲望（口号或空局势）",
        })
    if turn and desire and _share_8(turn, desire):
        warnings.append({
            "code": "turn_repeats_desire",
            "message": "回合与欲望近重复",
        })
    if not traces or all(_is_slogan_or_placeholder(t) for t in traces):
        warnings.append({
            "code": "trace_not_visible",
            "message": "没有看得见的痕迹",
        })
    prev = prev_contract if isinstance(prev_contract, dict) else {}
    prev_turn = str(prev.get("turn") or "").strip()
    if turn and prev_turn and _share_8(turn, prev_turn):
        warnings.append({
            "code": "repeat_prev_turn",
            "message": "本场回合复读上章回合",
        })
    return {"warnings": warnings}


def _neighbor_pair(prev: dict | None, next_chapter: dict | None) -> list[dict]:
    out: list[dict] = []
    if isinstance(prev, dict) and prev:
        out.append(prev)
    if isinstance(next_chapter, dict) and next_chapter:
        out.append(next_chapter)
    return out


def assemble_scene_briefing(
    here: dict | None,
    prev: dict | None = None,
    inventory: dict | None = None,
    neighbor_contracts: list | None = None,
) -> dict[str, Any]:
    """schema=scene_briefing.v1; persist=False. 禁止当合同。"""
    here = here if isinstance(here, dict) else {}
    prev = prev if isinstance(prev, dict) else {}
    inv = inventory if isinstance(inventory, dict) else {}

    beats_raw = here.get("beats") if isinstance(here.get("beats"), list) else []
    beats: list[dict[str, Any]] = []
    for i, b in enumerate(beats_raw[:8]):
        t = beat_text(b)
        ok, _rs = beat_shape(t) if t else (False, ["empty"])
        beats.append({"i": i, "text": t, "shape_ok": bool(ok)})

    drive = here.get("narrative_drive") if isinstance(here.get("narrative_drive"), dict) else {}
    contract = here.get("narrative_contract") if isinstance(here.get("narrative_contract"), dict) else {}
    bindings = contract.get("bindings") if isinstance(contract.get("bindings"), dict) else {}
    ev = bindings.get("evidence_must_show")
    here_traces: list[str] = []
    if isinstance(ev, list):
        here_traces = [str(x).strip() for x in ev if str(x).strip()][:3]

    meta: dict[str, Any] = {}
    try:
        from scribe3.brief import parse_chapter_meta
        parsed = parse_chapter_meta(here.get("synopsis") or here.get("beats") or "")
        if isinstance(parsed, dict):
            meta = {k: parsed[k] for k in ("role", "pressure", "stakes", "hook") if k in parsed}
    except Exception:
        meta = {}

    prev_c = prev.get("narrative_contract") if isinstance(prev.get("narrative_contract"), dict) else {}
    prev_drive = prev.get("narrative_drive") if isinstance(prev.get("narrative_drive"), dict) else {}
    prev_end = _drive_str(prev_drive, "end_hook") or str(inv.get("prev_end_hook") or "")
    prev_b = prev_c.get("bindings") if isinstance(prev_c.get("bindings"), dict) else {}
    prev_tr = prev_b.get("evidence_must_show")
    prev_traces: list[str] = []
    if isinstance(prev_tr, list):
        prev_traces = [str(x).strip() for x in prev_tr if str(x).strip()][:3]

    overdue = [p for p in (inv.get("overdue_promises") or []) if p][:5]
    opens: list[Any] = []
    for p in (inv.get("open_promises") or [])[:8]:
        lab = ""
        if isinstance(p, dict):
            lab = str(p.get("label") or p.get("text") or p.get("summary") or p.get("title") or "")
        else:
            lab = str(p or "")
        if lab and any(x in lab for x in ("债", "禁", "讨", "到期", "期限", "若不", "否则", "威胁")):
            opens.append(p if isinstance(p, dict) else {"label": lab})
        if len(opens) >= 5:
            break

    neighbors: list[dict[str, Any]] = []
    for n in (neighbor_contracts or [])[:2]:
        if not isinstance(n, dict):
            continue
        nc = n.get("narrative_contract") if isinstance(n.get("narrative_contract"), dict) else n
        neighbors.append({
            "seq": n.get("seq"),
            "turn": _clip_brief(nc.get("turn") if isinstance(nc, dict) else "", 80),
            "desire": _clip_brief(nc.get("desire") if isinstance(nc, dict) else "", 80),
        })

    opp_flat = drive.get("opposition")
    opp_wants = _drive_str(drive, "opposition", "wants")
    if not opp_wants and isinstance(opp_flat, str):
        opp_wants = opp_flat.strip()

    return {
        "schema": "scene_briefing.v1",
        "persist": False,
        "here": {
            "seq": here.get("seq"),
            "title": str(here.get("title") or ""),
            "synopsis": _clip_brief(here.get("synopsis") or "", 400),
            "beats": beats,
            "scene_truth": _clip_brief(here.get("scene_truth") or "", 400),
            "contract": {k: str(contract.get(k) or "") for k in _FIELD_KEYS},
            "drive": {
                "inciting": (
                    _drive_str(drive, "inciting_force", "summary")
                    or _drive_str(drive, "inciting")
                    or _drive_str(drive, "want")
                    or _drive_str(drive, "goal")
                ),
                "opposition_who": _drive_str(drive, "opposition", "who_or_what"),
                "opposition_wants": opp_wants,
                "scene_turn": _drive_str(drive, "scene_turn") or _drive_str(drive, "turn"),
                "end_hook": _drive_str(drive, "end_hook"),
                "if_fail": (
                    _drive_str(drive, "deadline_or_cost", "if_fail")
                    or _drive_str(drive, "cost")
                    or _drive_str(drive, "stake")
                ),
            },
            "traces": here_traces,
            "focalizer": str(here.get("focalizer") or ""),
            "meta": meta,
        },
        "prev": {
            "seq": prev.get("seq"),
            "title": str(prev.get("title") or ""),
            "contract": {k: str(prev_c.get(k) or "") for k in _FIELD_KEYS},
            "end_hook": prev_end,
            "traces": prev_traces,
            "unresolved": prev_end or str(prev_c.get("turn") or ""),
        },
        "volume_pos": meta,
        "inventory": {
            "overdue_promises": overdue,
            "open_promises": opens,
        },
        "neighbors": neighbors,
    }


def _cand(text: Any, source: str, **extra: Any) -> dict[str, Any] | None:
    t = str(text or "").strip()
    if not t:
        return None
    row: dict[str, Any] = {"text": t, "source": source}
    row.update(extra)
    return row


def _scene_candidates(briefing: dict | None) -> dict[str, list[dict[str, Any]]]:
    briefing = briefing if isinstance(briefing, dict) else {}
    here = briefing.get("here") if isinstance(briefing.get("here"), dict) else {}
    prev = briefing.get("prev") if isinstance(briefing.get("prev"), dict) else {}
    drive = here.get("drive") if isinstance(here.get("drive"), dict) else {}
    meta = here.get("meta") if isinstance(here.get("meta"), dict) else {}
    inv = briefing.get("inventory") if isinstance(briefing.get("inventory"), dict) else {}

    desire: list[dict[str, Any]] = []
    for t, src in (
        (drive.get("inciting"), "here.drive.inciting"),
        ((here.get("synopsis") or "").splitlines()[0] if here.get("synopsis") else "", "here.synopsis"),
        (prev.get("end_hook"), "prev.end_hook"),
        ((prev.get("contract") or {}).get("turn") if isinstance(prev.get("contract"), dict) else "", "prev.contract.turn"),
    ):
        row = _cand(t, src)
        if row:
            desire.append(row)
    for p in (inv.get("overdue_promises") or [])[:2]:
        lab = ""
        pid = ""
        if isinstance(p, dict):
            lab = str(p.get("label") or p.get("text") or p.get("summary") or "")
            pid = str(p.get("id") or p.get("promise_id") or "")
        if lab:
            desire.append({"text": lab, "source": f"inventory.promise:{pid or 'overdue'}"})

    obstacle: list[dict[str, Any]] = []
    for t, src in (
        (drive.get("opposition_wants"), "here.drive.opposition"),
        (drive.get("opposition_who"), "here.drive.opposition"),
    ):
        row = _cand(t, src)
        if row:
            obstacle.append(row)

    turn: list[dict[str, Any]] = []
    for b in here.get("beats") or []:
        if isinstance(b, dict) and b.get("shape_ok") and b.get("text"):
            turn.append({"text": str(b["text"]), "source": f"here.beat[{b.get('i')}]"})
    st = drive.get("scene_turn") or ""
    if st:
        turn.append({
            "text": str(st),
            "source": "here.drive.scene_turn",
            "template": is_drive_template_turn(str(st)),
        })

    cost: list[dict[str, Any]] = []
    for t, src in (
        (drive.get("if_fail"), "here.drive.if_fail"),
        (meta.get("stakes"), "meta.stakes"),
    ):
        row = _cand(t, src)
        if row:
            cost.append(row)

    return {
        "desire": desire,
        "obstacle": obstacle,
        "turn": turn,
        "cost": cost,
        "traces": [],
    }


def _draft_if_qualified(
    candidates: dict[str, list[dict[str, Any]]] | None,
) -> tuple[dict[str, Any], bool]:
    """过 4.4.1 启发式才填 draft。空材料 / 仅模板句 → needs_author。"""
    candidates = candidates if isinstance(candidates, dict) else {}
    draft: dict[str, Any] = {
        "desire": "", "obstacle": "", "turn": "", "cost": "", "traces": [],
    }

    def pick(items: list | None, *, allow_template: bool = False) -> str:
        for it in items or []:
            if not isinstance(it, dict):
                continue
            t = str(it.get("text") or "").strip()
            if not t:
                continue
            if it.get("template") and not allow_template:
                continue
            if is_drive_template_turn(t):
                continue
            if _is_slogan_or_placeholder(t):
                continue
            if cn_len(t) < 4:
                continue
            return t
        return ""

    draft["desire"] = pick(candidates.get("desire"))
    draft["obstacle"] = pick(candidates.get("obstacle"))
    if cn_strip(draft["obstacle"]) in ("局势", "命运", "局势/对立面", "对立面", "对立面/外力"):
        draft["obstacle"] = ""
    draft["turn"] = pick(candidates.get("turn"))
    draft["cost"] = pick(candidates.get("cost"))
    traces: list[str] = []
    for it in candidates.get("traces") or []:
        if not isinstance(it, dict):
            continue
        t = str(it.get("text") or "").strip()
        if t and not _is_slogan_or_placeholder(t):
            traces.append(t)
        if len(traces) >= 3:
            break
    draft["traces"] = traces

    has_any = any(draft[k] for k in _FIELD_KEYS) or bool(traces)
    cand_any = any(candidates.get(k) for k in ("desire", "obstacle", "turn", "cost", "traces"))
    needs_author = (not has_any) or (not cand_any)
    # 仅有模板回合、其它格也空 → 问作者
    if not draft["turn"] and not draft["desire"] and not draft["obstacle"] and not draft["cost"]:
        needs_author = True
    return draft, needs_author


def _pressure_trace_candidates(chapter: dict | None) -> list[dict[str, Any]]:
    here = chapter if isinstance(chapter, dict) else {}
    contract = here.get("narrative_contract") if isinstance(here.get("narrative_contract"), dict) else {}
    bindings = contract.get("bindings") if isinstance(contract.get("bindings"), dict) else {}
    ev = bindings.get("evidence_must_show")
    if isinstance(ev, list) and any(str(x).strip() for x in ev):
        return []
    out: list[dict[str, Any]] = []
    pd = here.get("pressure_drive") if isinstance(here.get("pressure_drive"), dict) else {}
    irr = pd.get("irreversible") if isinstance(pd.get("irreversible"), dict) else {}
    ev2 = irr.get("evidence_must_show")
    if isinstance(ev2, list):
        for t in ev2:
            if str(t).strip():
                out.append({"text": str(t).strip(), "source": "here.pressure.irreversible"})
    elif isinstance(ev2, str) and ev2.strip():
        out.append({"text": ev2.strip(), "source": "here.pressure.irreversible"})
    stairs = None
    prog = pd.get("progress") if isinstance(pd.get("progress"), dict) else None
    if isinstance(prog, dict):
        stairs = prog.get("stairs")
    if stairs is None:
        stairs = pd.get("stairs")
    if isinstance(stairs, list):
        for s in stairs:
            if isinstance(s, dict):
                t = str(s.get("evidence_must_show") or "").strip()
                if t:
                    out.append({"text": t, "source": "here.pressure.stairs"})
    return out[:3]


def suggest_scene_contract(
    chapter: dict | None,
    *,
    prev: dict | None = None,
    inventory: dict | None = None,
    next_chapter: dict | None = None,
) -> dict[str, Any]:
    """candidates + 可选 draft + lock_warnings + briefing。persist 恒 False。

    禁止 first-hit scrape 填满四格再假装 adopted_would_be.ok。
    """
    here = chapter if isinstance(chapter, dict) else {}
    prev_ch = prev if isinstance(prev, dict) else None
    next_ch = next_chapter if isinstance(next_chapter, dict) else None
    briefing = assemble_scene_briefing(
        here,
        prev=prev_ch,
        inventory=inventory,
        neighbor_contracts=_neighbor_pair(prev_ch, next_ch),
    )
    candidates = _scene_candidates(briefing)
    candidates["traces"] = list(candidates.get("traces") or []) + _pressure_trace_candidates(here)
    draft, needs_author = _draft_if_qualified(candidates)
    prev_contract = None
    if prev_ch:
        prev_contract = prev_ch.get("narrative_contract") if isinstance(prev_ch.get("narrative_contract"), dict) else None
    lock = check_scene_lock(draft, prev_contract=prev_contract)
    if needs_author:
        adopted = adopt_scene_suggest(None)
    else:
        adopted = adopt_scene_suggest(draft)
    return {
        "schema": "scene_suggest.v1",
        "persist": False,
        "briefing": briefing,
        "candidates": candidates,
        "draft": draft,
        "needs_author": needs_author,
        "lock_warnings": lock["warnings"],
        "adopted_would_be": adopted,
    }


def adopt_scene_suggest(suggest: dict | None) -> dict[str, Any]:
    """主编改写后的载荷 → 可落库合同。服务端/MCP 映射器；不是 scrape 原样。"""
    s = suggest if isinstance(suggest, dict) else {}
    traces = s.get("traces") if isinstance(s.get("traces"), list) else []
    traces = [str(t).strip() for t in traces if str(t).strip()][:3]
    raw = {
        "schema": SCHEMA,
        "version": 1,
        "desire": str(s.get("desire") or "").strip(),
        "obstacle": str(s.get("obstacle") or "").strip(),
        "turn": str(s.get("turn") or "").strip(),
        "cost": str(s.get("cost") or "").strip(),
        "conflict_beats": None,
        "bindings": {
            "evidence_must_show": traces,
            "adopted_from": "suggest",
        },
        "source": "orch",
        "locked": False,
    }
    return validate_narrative_contract(raw)


def sanitize_narrative_contract_write(
    raw: Any,
    *,
    source: str,
    prev: dict | None = None,
) -> dict[str, Any]:
    """四义覆盖；bindings merge 保留 scene_voice / narrative_drive_fp。非 dict 抛 ValueError。"""
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("narrative_contract_not_dict")
    prev = prev if isinstance(prev, dict) else {}
    prev_b = prev.get("bindings") if isinstance(prev.get("bindings"), dict) else {}
    incoming = raw if isinstance(raw, dict) else {}

    def clip500(val: Any) -> str:
        return str(val or "").strip()[:500]

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": 1,
        "conflict_beats": None,
        "locked": False,
        "source": str(source or "author"),
    }
    for k in _FIELD_KEYS:
        if k in incoming:
            out[k] = clip500(incoming.get(k))
        else:
            out[k] = clip500(prev.get(k))
    inc_b = incoming.get("bindings") if isinstance(incoming.get("bindings"), dict) else {}
    merged: dict[str, Any] = {}
    if "scene_voice" in inc_b:
        merged["scene_voice"] = inc_b["scene_voice"]
    elif "scene_voice" in prev_b:
        merged["scene_voice"] = prev_b["scene_voice"]
    if "narrative_drive_fp" in inc_b:
        merged["narrative_drive_fp"] = inc_b["narrative_drive_fp"]
    elif "narrative_drive_fp" in prev_b:
        merged["narrative_drive_fp"] = prev_b["narrative_drive_fp"]
    if "evidence_must_show" in inc_b:
        ev = inc_b["evidence_must_show"]
        if isinstance(ev, list):
            merged["evidence_must_show"] = [str(x).strip() for x in ev if str(x).strip()][:3]
        elif isinstance(ev, str) and ev.strip():
            merged["evidence_must_show"] = [ev.strip()]
    elif "evidence_must_show" in prev_b:
        merged["evidence_must_show"] = prev_b["evidence_must_show"]
    if "adopted_from" in inc_b:
        merged["adopted_from"] = inc_b["adopted_from"]
    out["bindings"] = merged
    return validate_narrative_contract(out)


def load_scene_suggest(st: Any, seq: int) -> dict[str, Any]:
    """I/O：装本章/邻章/库存再交 suggest_scene_contract。零写。"""
    try:
        here = (st.get_chapter(int(seq)) or {}) if st is not None else {}
    except Exception:
        here = {}
    prev = None
    nxt = None
    if st is not None and int(seq) > 1:
        try:
            prev = st.get_chapter(int(seq) - 1) or None
        except Exception:
            prev = None
    if st is not None:
        try:
            nxt = st.get_chapter(int(seq) + 1) or None
        except Exception:
            nxt = None
    inv: dict[str, Any] = {}
    try:
        from scribe3.narrative_drive import assemble_narrative_inventory
        if st is not None:
            inv = assemble_narrative_inventory(st, int(seq)) or {}
    except Exception:
        inv = {}
    return suggest_scene_contract(here, prev=prev, inventory=inv, next_chapter=nxt)

