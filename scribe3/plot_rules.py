"""剧情规则 P1 视角不得独占、P2 手段不得单一。

不设比例闸。问的是有没有那个人、有没有第二类动作。
句子好坏不进这里。
"""
from __future__ import annotations

from collections import Counter

from scribe3.ontology import canon_oid

ACTIONS = ("买", "换", "骗", "抢", "拖", "揭发", "结盟", "背叛")
ACTION_SET = frozenset(ACTIONS)


def normalize_action(raw) -> str | None:
    s = str(raw or "").strip()
    return s if s in ACTION_SET else None


def normalize_focalizer(raw) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    return canon_oid(s) or s


def chapter_focalizer(ch: dict, *, default: str) -> str:
    return normalize_focalizer((ch or {}).get("focalizer")) or default


def chapter_action(ch: dict) -> str | None:
    ch = ch or {}
    return normalize_action(ch.get("action") or ch.get("plot_action"))


def _seq(ch) -> int:
    try:
        return int((ch or {}).get("seq") or 0)
    except (TypeError, ValueError):
        return 0


def _in_range(ch, lo: int, hi: int) -> bool:
    s = _seq(ch)
    return lo <= s <= hi


def acting_alt_focalizers(st, oids: list[str], lo: int, hi: int) -> set[str]:
    """本卷既限知、又在该章给自己立了命题的点名视角。"""
    want = {o for o in oids if o}
    if not want or not hasattr(st, "chapters_lite"):
        return set()
    by_seq: dict[int, set[str]] = {}
    for ch in st.chapters_lite() or []:
        if not _in_range(ch, lo, hi):
            continue
        foc = normalize_focalizer(ch.get("focalizer"))
        if foc in want:
            by_seq.setdefault(_seq(ch), set()).add(foc)
    if not by_seq:
        return set()
    acted: set[str] = set()
    for f in (st.facts_at(hi) or []) if hasattr(st, "facts_at") else []:
        ch = int(getattr(f, "valid_from", 0) or 0)
        eid = str(getattr(f, "entity_id", "") or "")
        if eid in by_seq.get(ch, ()):
            acted.add(eid)
    return acted


def unused_alt_focalizers(st, oids: list[str], lo: int, hi: int) -> list[str]:
    acted = acting_alt_focalizers(st, oids, lo, hi)
    return [o for o in oids if o and o not in acted]


def action_classes_in(st, lo: int, hi: int) -> set[str]:
    out: set[str] = set()
    if not hasattr(st, "chapters_lite"):
        return out
    for ch in st.chapters_lite() or []:
        if not _in_range(ch, lo, hi):
            continue
        a = normalize_action(ch.get("plot_action") or ch.get("action"))
        if a:
            out.add(a)
    return out


def _alt_oids(charter: dict) -> list[str]:
    return [i["oid"] for i in (charter.get("alt_focalizers") or []) if i.get("oid")]


def any_non_hero_acting(st, lo: int, hi: int, hero: str) -> bool:
    hero_n = normalize_focalizer(hero)
    foc_by_seq: dict[int, str] = {}
    if not hasattr(st, "chapters_lite"):
        return False
    for ch in st.chapters_lite() or []:
        if not _in_range(ch, lo, hi):
            continue
        foc = normalize_focalizer(ch.get("focalizer"))
        if foc and foc != hero_n:
            foc_by_seq[_seq(ch)] = foc
    if not foc_by_seq:
        return False
    for f in (st.facts_at(hi) or []) if hasattr(st, "facts_at") else []:
        ch = int(getattr(f, "valid_from", 0) or 0)
        eid = str(getattr(f, "entity_id", "") or "")
        if foc_by_seq.get(ch) == eid:
            return True
    return False


def plot_deficits(st, vol: dict, lo: int, hi: int, *, hero: str) -> list[str]:
    """空列表 = P1/P2 过。调用方只在卷末拿它当硬项。

    没有 `chapters_lite` 的旧夹具测寿命账，不在这里拦。
    """
    if not hasattr(st, "chapters_lite"):
        return []
    from scribe3.charter import normalize_charter

    c = normalize_charter((vol or {}).get("charter"))
    rng = c["chapter_range"] or [lo, hi]
    vol_lo, _vol_hi = int(rng[0]), int(rng[1])
    msgs: list[str] = []
    alts = _alt_oids(c)
    if alts:
        unused = unused_alt_focalizers(st, alts, vol_lo, hi)
        if unused:
            msgs.append("本卷点名的非主角视角还没自己办事：" + "、".join(unused))
    elif not any_non_hero_acting(st, vol_lo, hi, hero):
        msgs.append("本卷没有非主角自己办事的章")
    classes = action_classes_in(st, vol_lo, hi)
    if len(classes) < 2:
        shown = "、".join(sorted(classes)) or "（一章都没标）"
        msgs.append(
            f"本卷动作全是同一类：{shown}。"
            "至少再有一类（买/换/骗/抢/拖/揭发/结盟/背叛）")
    return msgs


def volume_plot_block(st, vol_lo: int, upto: int, *,
                      hero: str, alt_focalizers) -> str:
    """写入章级提示：已有视角/动作台账 + 两条规则。"""
    alts: list[tuple[str, str]] = []
    for item in alt_focalizers or []:
        if isinstance(item, str):
            oid, why = normalize_focalizer(item), ""
        else:
            oid = normalize_focalizer((item or {}).get("oid"))
            why = str((item or {}).get("why") or "")
        if oid:
            alts.append((oid, why))
    acted = acting_alt_focalizers(st, [o for o, _ in alts], vol_lo, upto)
    lines = [
        "**本卷剧情（视角不得独占，手段不得单一）**：",
        f"- 主角默认视角 {hero}。本卷至少一章由下面这个人限知，"
        "且该章核心动作是他自己做的，不是旁观。",
    ]
    if alts:
        for oid, why in alts:
            tag = "已自己办事" if oid in acted else "尚未自己办事"
            lines.append(f"  - {oid}：{why or '（未写他做什么）'}｜{tag}")
    else:
        lines.append("  - （契约还没点名非主角视角，本批必须写出一章别人自己办事）")
    counts: Counter[str] = Counter()
    if upto >= vol_lo and hasattr(st, "chapters_lite"):
        for ch in st.chapters_lite() or []:
            if vol_lo <= _seq(ch) <= upto:
                a = normalize_action(ch.get("plot_action") or ch.get("action"))
                counts[a or "未标"] += 1
    if counts:
        ledger = "、".join(f"{k} {n}章" for k, n in counts.most_common())
        lines.append(f"- 本卷已标动作：{ledger}。本批不得让整卷只剩同一类。")
    else:
        lines.append("- 本卷还没有标过动作。本批开始标，且不得全是同一类。")
    lines.append(
        "- 每章必须写 `focalizer` 和 `action`。"
        "action 只许：买、换、骗、抢、拖、揭发、结盟、背叛。")
    return "\n".join(lines)


def ensure_alt_focalizers(charter: dict, *, hero: str,
                          candidates=()) -> list[dict]:
    """契约已点名则保留；否则先用候选人，再从写厚名单里挑一个非主角人物。"""
    have = [i for i in (charter.get("alt_focalizers") or []) if i.get("oid")]
    if have:
        return have
    hero_n = normalize_focalizer(hero)
    for raw in candidates or ():
        oid = normalize_focalizer(raw)
        if oid.startswith("role:") and oid != hero_n:
            return [{"oid": oid, "why": "这一卷他自己办事，不是旁观主角。"}]
    for item in charter.get("thickens") or []:
        if isinstance(item, str):
            oid, why = item, ""
        else:
            oid = str((item or {}).get("oid") or "")
            why = str((item or {}).get("why") or "")
        oid = normalize_focalizer(oid)
        if oid.startswith("role:") and oid != hero_n:
            return [{"oid": oid,
                     "why": why or "这一卷他自己办事，不是旁观主角。"}]
    return []
