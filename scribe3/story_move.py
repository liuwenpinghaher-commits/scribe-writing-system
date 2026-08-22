"""故事招式库：检索 / 公式族 / 组装段。种子卡无 I/O 外读 JSON。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SEEDS = Path(__file__).resolve().parent / "story_moves" / "seeds.json"

_ROLE_CANON = {
    "假": "假", "反": "假", "反面": "假", "期望": "假", "热闹": "假", "胜利": "假",
    "破": "破", "转": "破", "破功": "破", "打碎": "破", "间隙": "破", "露怯": "破",
    "真": "真", "落": "真", "本意": "真", "真相": "真", "孤独": "真", "失败": "真",
}

OH_STORY_SOURCE_STEMS = frozenset({
    "anti-ai-writing", "artifact-protocols", "banned-words", "character-basics",
    "character-design-methods", "character-relations", "commercial-core-methods",
    "cross-book-recall", "dialogue-mastery", "emotional-arc-design", "emotional-methods",
    "female-audience-writing", "format-and-structure", "genre-catalog",
    "genre-core-mechanics", "genre-readers", "genre-writing-formulas", "hooks-chapter",
    "hooks-paragraph", "hooks-suspense", "opening-design", "outline-conflict",
    "outline-methods", "outline-rhythm", "outline-structure-theory", "plot-core-methods",
    "plot-emotion-system", "plot-frameworks", "plot-special-topics", "quality-checklist",
    "reversal-toolkit", "state-tracking", "style-combat-face", "style-craft",
    "style-genre-modules", "workflow-daily", "workflow-revision", "writing-craft",
})


def move_library_enabled() -> bool:
    try:
        from scribe3.feature_flags import flag_truthy, get_flag
        return flag_truthy("SCRIBE3_MOVE_LIBRARY")
    except Exception:
        import os
        return (get_flag("SCRIBE3_MOVE_LIBRARY") or "0").strip().lower() in (
            "1", "true", "yes", "on",
        )


def _norm(s: str) -> str:
    return "".join((s or "").split()).lower()


def _norm_arrow(s: str) -> str:
    t = (s or "").replace("->", "→").replace("－", "→").replace("-", "→")
    return "".join(t.split())


def _role_seq(formula: dict | None) -> tuple[str, ...]:
    return tuple(
        _ROLE_CANON.get(b.get("role") or "", b.get("role") or "")
        for b in ((formula or {}).get("beats") or [])
        if isinstance(b, dict)
    )


def same_formula_family(a: dict | None, b: dict | None) -> bool:
    a, b = a or {}, b or {}
    fa, fb = a.get("formula_family") or "", b.get("formula_family") or ""
    if fa and fa == fb:
        return True
    aa = _norm_arrow((a.get("formula") or {}).get("arrow") if isinstance(a.get("formula"), dict) else a.get("arrow") or "")
    ba = _norm_arrow((b.get("formula") or {}).get("arrow") if isinstance(b.get("formula"), dict) else b.get("arrow") or "")
    if aa == "假→破→真" and ba == "假→破→真":
        return True
    sa = _role_seq(a.get("formula") if isinstance(a.get("formula"), dict) else a)
    sb = _role_seq(b.get("formula") if isinstance(b.get("formula"), dict) else b)
    return bool(sa) and sa == sb


def load_seed_cards() -> list[dict[str, Any]]:
    data = json.loads(_SEEDS.read_text(encoding="utf-8"))
    cards = list(data.get("cards") or [])
    return [c for c in cards if isinstance(c, dict)]


def approved_cards(extra: list[dict] | None = None) -> list[dict[str, Any]]:
    cards = load_seed_cards()
    if extra:
        cards = cards + [c for c in extra if isinstance(c, dict)]
    return [c for c in cards if (c.get("status") or "approved") == "approved"]


def _alias_list(card: dict) -> list[str]:
    out = [card.get("name") or "", card.get("slug") or ""]
    out.extend(card.get("aliases") or [])
    return [x for x in out if str(x).strip()]


def retrieve_story_move(
    query: str,
    *,
    move_id: str | None = None,
    formula: dict | None = None,
    cards: list[dict] | None = None,
) -> list[dict[str, Any]]:
    """按本意/俗名取 1 张已批卡。羁绊撕裂不得落到三角。"""
    approved = list(cards) if cards is not None else approved_cards()
    approved = [c for c in approved if (c.get("status") or "approved") == "approved"]
    if move_id:
        hit = [c for c in approved if c.get("slug") == move_id]
        return hit[:1]
    q = _norm(query)
    if not q:
        return []
    triangle = next((c for c in approved if c.get("slug") == "triangle_info"), None)
    if formula and triangle and same_formula_family(
        {"formula": formula, "formula_family": (formula or {}).get("formula_family")},
        triangle,
    ):
        return [triangle]
    hits: list[dict] = []
    for c in approved:
        for a in _alias_list(c):
            na = _norm(a)
            if na and (q == na or na in q or q in na):
                hits.append(c)
                break
    uniq: dict[str, dict] = {}
    for c in hits:
        uniq[str(c.get("slug"))] = c
    if len(uniq) == 1:
        return list(uniq.values())
    if len(uniq) > 1:
        others = [c for s, c in uniq.items() if s != "triangle_info"]
        if len(others) == 1:
            return others
        return [list(uniq.values())[0]]
    if triangle:
        return [triangle]
    return approved[:1]


def validate_story_move_plan(plan: dict | None) -> dict[str, Any]:
    p = plan if isinstance(plan, dict) else {}
    errors: list[str] = []
    benyi = str(p.get("benyi") or "").strip()
    if not benyi:
        errors.append("缺本意")
    if len(benyi) > 40:
        errors.append("本意过长")
    slug = str(p.get("move_id") or p.get("slug") or "").strip()
    if not slug:
        errors.append("缺招式")
    beats = p.get("beats")
    if beats is not None and not isinstance(beats, list):
        errors.append("构造拍必须是列表")
    ok = not errors
    return {"ok": ok, "errors": errors}


def plan_from_chapter(chapter: dict | None) -> dict:
    ch = chapter if isinstance(chapter, dict) else {}
    plan = ch.get("story_move_plan")
    if isinstance(plan, dict):
        return plan
    bm = ch.get("beats_meta") if isinstance(ch.get("beats_meta"), dict) else {}
    p2 = bm.get("story_move_plan")
    return p2 if isinstance(p2, dict) else {}


def render_story_move_segment(
    plan: dict | None,
    *,
    enabled: bool | None = None,
    cards: list[dict] | None = None,
    uses: list[dict] | None = None,
) -> dict[str, Any]:
    """仅当旗开且 approved∧validation.ok 才输出 1 卡 + ≤2 uses。"""
    meta = {
        "fed": False,
        "applied": False,
        "enabled": False,
        "chars": 0,
        "slug": "",
    }
    on = move_library_enabled() if enabled is None else bool(enabled)
    meta["enabled"] = on
    meta["plan_missing"] = False
    if not on:
        meta["skip_reason"] = "flag_off"
        return {"text": "", "meta": meta}
    p = plan if isinstance(plan, dict) else {}
    val = p.get("validation") if isinstance(p.get("validation"), dict) else validate_story_move_plan(p)
    if not p.get("approved") or not val.get("ok"):
        meta["fed"] = True
        meta["plan_missing"] = True
        meta["skip_reason"] = "plan_missing"
        return {"text": "", "meta": meta}
    slug = str(p.get("move_id") or p.get("slug") or "").strip()
    picked = retrieve_story_move(p.get("benyi") or "", move_id=slug or None, cards=cards)
    if not picked:
        meta["fed"] = True
        meta["skip_reason"] = "card_not_found"
        return {"text": "", "meta": meta}
    card = picked[0]
    meta["slug"] = str(card.get("slug") or "")
    arrow = ""
    form = card.get("formula") if isinstance(card.get("formula"), dict) else {}
    arrow = str(form.get("arrow") or "")
    benyi = str(p.get("benyi") or "").strip()[:40]
    lines = [
        f"【招式·{card.get('name') or card.get('slug')}】本意：{benyi}。别直线：{card.get('straight_line') or ''}",
        f"公式：{arrow}。{card.get('usage') or ''}",
    ]
    plan_beats = p.get("beats") if isinstance(p.get("beats"), list) else form.get("beats") or []
    for b in plan_beats[:6]:
        if isinstance(b, dict):
            role = b.get("role") or b.get("name") or ""
            hint = b.get("text") or b.get("hint") or ""
            lines.append(f"- {role}：{hint}"[:80])
    good = [u for u in (uses or []) if isinstance(u, dict)][:2]
    for u in good:
        lines.append(f"旧用方法：{u.get('summary') or u.get('mechanism') or ''}"[:80])
    text = "\n".join(lines).strip()
    for stem in OH_STORY_SOURCE_STEMS:
        if stem in text:
            text = text.replace(stem, "（方法）")
    text = ("\n\n" + text + "\n") if text else ""
    meta["fed"] = True
    meta["applied"] = bool(text.strip())
    meta["chars"] = len(text)
    return {"text": text, "meta": meta}


def prepare_write_story_move(
    st: Any,
    *,
    chapter: int | None,
    work: str | None = "main",
    enabled: bool | None = None,
) -> dict[str, Any]:
    ch: dict = {}
    try:
        if st is not None and chapter is not None and hasattr(st, "get_chapter"):
            ch = st.get_chapter(int(chapter)) or {}
    except Exception:
        ch = {}
    plan = plan_from_chapter(ch)
    return render_story_move_segment(plan, enabled=enabled)


def sanitize_uses_for_inject(uses: list[dict] | None) -> list[dict]:
    out = []
    for u in uses or []:
        if not isinstance(u, dict):
            continue
        out.append({"summary": str(u.get("summary") or u.get("mechanism") or "")[:80]})
        if len(out) >= 2:
            break
    return out


def validate_move_card(payload: dict | None) -> dict[str, Any]:
    p = payload if isinstance(payload, dict) else {}
    errors: list[str] = []
    name = str(p.get("name") or "").strip()
    if not (2 <= len(name) <= 16):
        errors.append("name 须 2–16 字")
    ol = str(p.get("one_liner") or "").strip()
    if len(ol) > 40:
        errors.append("one_liner ≤40 字")
    form = p.get("formula") if isinstance(p.get("formula"), dict) else {}
    beats = form.get("beats") if isinstance(form.get("beats"), list) else []
    if len(beats) < 2:
        errors.append("formula.beats 至少 2 拍")
    sl = str(p.get("straight_line") or "").strip()
    if len(sl) < 8:
        errors.append("straight_line 过短")
    return {"ok": not errors, "errors": errors}


def _slug_from_name(name: str) -> str:
    import hashlib
    h = hashlib.sha256((name or "").encode("utf-8")).hexdigest()[:10]
    return "am_" + h


def propose_story_move(payload: dict | None, *, extra_cards: list[dict] | None = None) -> dict[str, Any]:
    """纯函数提案闸：禁建 / 并三角 / 生成 pending 卡身。不写库。"""
    p = dict(payload or {})
    gate = propose_merge_gate(p)
    if not gate.get("ok"):
        return gate
    if gate.get("merged"):
        return gate
    val = validate_move_card(p)
    if not val["ok"]:
        return {"ok": False, "code": "invalid", "errors": val["errors"]}
    slug = str(p.get("slug") or "").strip() or _slug_from_name(str(p.get("name") or ""))
    seeds = {c.get("slug") for c in load_seed_cards()}
    extras = {c.get("slug") for c in (extra_cards or []) if (c.get("status") == "approved")}
    if slug in seeds or slug in extras:
        return {"ok": False, "code": "conflict", "slug": slug}
    card = {
        "slug": slug,
        "name": str(p.get("name") or "").strip(),
        "one_liner": str(p.get("one_liner") or "").strip()[:40],
        "formula_family": str(p.get("formula_family") or "custom"),
        "formula": p.get("formula") if isinstance(p.get("formula"), dict) else {},
        "straight_line": str(p.get("straight_line") or "").strip(),
        "aliases": list(p.get("aliases") or []),
        "usage": str(p.get("usage") or ""),
        "status": "pending",
        "origin": "author",
    }
    return {"ok": True, "merged": False, "slug": slug, "status": "pending", "card": card}


def save_story_move_plan_on_chapter(st: Any, seq: int, plan: dict) -> dict[str, Any]:
    """合并写入 chapter.beats_meta.story_move_plan。"""
    smp = dict(plan or {})
    smp["validation"] = validate_story_move_plan(smp)
    if smp.get("approved") and not smp["validation"].get("ok"):
        smp["approved"] = False
    ch = st.get_chapter(int(seq)) or {}
    if not ch:
        return {"ok": False, "code": "not_found"}
    bm = ch.get("beats_meta") if isinstance(ch.get("beats_meta"), dict) else {}
    bm = dict(bm)
    bm["story_move_plan"] = smp
    if not st.update_chapter_meta(int(seq), {"beats_meta": bm}):
        return {"ok": False, "code": "not_found"}
    return {"ok": True, "plan": smp}


def work_cards(st: Any | None = None) -> list[dict[str, Any]]:
    cards = load_seed_cards()
    if st is not None and hasattr(st, "list_author_story_moves"):
        try:
            cards = cards + list(st.list_author_story_moves() or [])
        except Exception:
            pass
    return cards


def propose_merge_gate(payload: dict | None) -> dict[str, Any]:
    """新卡闸：假破真并三角；限知禁建。"""
    p = payload if isinstance(payload, dict) else {}
    blob = " ".join(
        str(x) for x in (p.get("name"), p.get("one_liner"), " ".join(p.get("aliases") or []))
    )
    if any(k in blob for k in ("限知", "dramatic irony", "观众多知", "观众比角色多知道")):
        return {"ok": False, "code": "belongs_to_skill", "skill": "限知视角"}
    triangle = next((c for c in load_seed_cards() if c.get("slug") == "triangle_info"), {})
    aliases = set(_norm(a) for a in _alias_list(triangle))
    name_n = _norm(str(p.get("name") or ""))
    if name_n in aliases or any(_norm(a) in aliases for a in (p.get("aliases") or [])):
        return {"ok": True, "merged": True, "into": "triangle_info", "reason": "俗名属于三角"}
    if same_formula_family(p, triangle):
        return {
            "ok": True,
            "merged": True,
            "into": "triangle_info",
            "reason": "公式仍是假→破→真，并进三角信息法",
        }
    return {"ok": True, "merged": False}


def banned_lexicon_preview(limit: int = 24) -> dict[str, Any]:
    """设置中心只读：不复制词表进技法 md。"""
    from scribe3.critique._common import _BANNED_LEXICON
    keys = list(_BANNED_LEXICON.keys())[: max(0, int(limit))]
    return {"source": "critique._common._BANNED_LEXICON", "keys": keys, "count": len(_BANNED_LEXICON)}
