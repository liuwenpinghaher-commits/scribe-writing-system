"""母题工艺纯函数:回声结构化 · heat 调度 · 注入文案。

无 store 依赖;pytest 可对 plain dict 直接验收。
真源接线:brief.motif_directives / assemble_chapter_brief,
以及 api._codex_block(for_generation=True) 的写作注入。
"""
from __future__ import annotations

from typing import Any, Iterable

# 轻量生命周期(有序);rest=休眠不催回声
MOTIF_PHASES: tuple[str, ...] = ("seed", "echo", "turn", "payoff", "rest")
MOTIF_TIERS: tuple[str, ...] = ("book", "volume", "arc", "chapter")

# 连续触及 ≥ 此章数 → overheat(avoid_overuse)
DEFAULT_OVERHEAT_STREAK = 3
# 距上次触及 gap ≥ 此 → cold(must_echo);从未触及也 cold
DEFAULT_COLD_GAP = 4
# evidence 最短有效字数(空/过短拒写 junk hit)
MIN_EVIDENCE_LEN = 2


def parse_echo_terms(
    echoes: str | None = None,
    echo_terms: list | None = None,
) -> list[str]:
    """合并结构化 echo_terms 与遗留 slash/顿号字符串,去重保序,≥2 字。"""
    out: list[str] = []
    seen: set[str] = set()

    def _add(raw: str) -> None:
        p = (raw or "").strip()
        if len(p) < 2 or p in seen:
            return
        seen.add(p)
        out.append(p)

    if isinstance(echo_terms, list):
        for t in echo_terms:
            if t is None:
                continue
            _add(str(t))
    text = echoes or ""
    if text:
        for sep in ("、", ",", "，", "|", "；", ";"):
            text = text.replace(sep, "/")
        for part in text.split("/"):
            _add(part)
    return out


def format_echoes(terms: Iterable[str]) -> str:
    """结构化 terms → 遗留 slash 字符串(兼容旧 UI/注入)。"""
    return "/".join(t for t in (str(x).strip() for x in (terms or [])) if len(t) >= 2)


def normalize_phase(phase: str | None) -> str:
    p = (phase or "seed").strip().lower()
    return p if p in MOTIF_PHASES else "seed"


def normalize_tier(tier: str | None) -> str:
    t = (tier or "book").strip().lower()
    return t if t in MOTIF_TIERS else "book"


def motif_heat(
    touch_chapters: list[int] | None,
    next_chapter: int,
    *,
    overheat_streak: int = DEFAULT_OVERHEAT_STREAK,
    cold_gap: int = DEFAULT_COLD_GAP,
) -> dict[str, Any]:
    """据触及章号历史判定 heat(相对即将写的 next_chapter)。

    - hot: 在 next_chapter 之前,末尾连续触及 streak ≥ overheat_streak
      (且最后触及章紧邻 next-1 或形成连续块)
    - cold: 从未触及,或 gap = next_chapter - last_touch ≥ cold_gap
    - neutral: 其余

    返回 {heat, last_touch, streak, gap, hit_count}。
    """
    next_ch = int(next_chapter)
    chs = sorted({int(c) for c in (touch_chapters or []) if c is not None and int(c) < next_ch})
    hit_count = len(chs)
    if not chs:
        return {
            "heat": "cold",
            "last_touch": None,
            "streak": 0,
            "gap": None,
            "hit_count": 0,
        }
    last = chs[-1]
    gap = next_ch - last
    # 从 last 往前数连续 streak
    streak = 1
    expect = last - 1
    for c in reversed(chs[:-1]):
        if c == expect:
            streak += 1
            expect -= 1
        elif c < expect:
            break
    # 过热:连续 streak 够长,且最近一次在近窗内(gap 小,仍「刚刷过」)
    if streak >= overheat_streak and gap <= overheat_streak:
        heat = "hot"
    elif gap >= cold_gap:
        heat = "cold"
    else:
        heat = "neutral"
    return {
        "heat": heat,
        "last_touch": last,
        "streak": streak,
        "gap": gap,
        "hit_count": hit_count,
    }


def schedule_motifs(
    motifs: list[dict],
    touch_map: dict[str, list[int]],
    next_chapter: int,
    *,
    overheat_streak: int = DEFAULT_OVERHEAT_STREAK,
    cold_gap: int = DEFAULT_COLD_GAP,
    store: Any = None,
) -> dict[str, Any]:
    """对全书母题做调度。

    touch_map: motif_id -> [chapter, ...]
    返回 {
      must_echo: [row...],      # cold 且 phase 非 rest
      avoid_overuse: [row...],  # hot
      neutral: [row...],
      rows: [全部 enrich 后],
    }
    每 row = motif 字段 + heat 字段 + id 归一。
    """
    must_echo: list[dict] = []
    avoid_overuse: list[dict] = []
    neutral: list[dict] = []
    rows: list[dict] = []
    for m in motifs or []:
        mid = str(m.get("id") or "").strip()
        if mid.startswith("motif:"):
            mid = mid.split(":", 1)[1]
        phase = normalize_phase(m.get("phase"))
        touches = touch_map.get(mid) or touch_map.get(str(m.get("id") or "")) or []
        tier = normalize_tier(m.get("tier"))
        gap = int(cold_gap)
        if tier == "book":
            gap = max(gap, gap * 2)
        elif tier == "chapter":
            gap = max(1, gap // 2)
        heat_info = motif_heat(
            touches, next_chapter,
            overheat_streak=overheat_streak, cold_gap=gap)
        row = {**m, "id": mid or m.get("id"), **heat_info, "phase": phase,
               "tier": tier,
               "echo_terms": parse_echo_terms(m.get("echoes"), m.get("echo_terms"))}
        n_touch = len(touches)
        new_phase = phase
        if phase == "seed" and n_touch >= 2:
            new_phase = "echo"
        elif phase == "echo" and n_touch >= 5:
            new_phase = "turn"
        elif phase == "turn" and n_touch >= 8:
            new_phase = "payoff"
        row["phase"] = new_phase
        row["original_phase"] = phase
        if new_phase != phase and store is not None and mid:
            updater = getattr(store, "update_motif", None)
            if callable(updater):
                try:
                    updater(mid, {"phase": new_phase})
                    import logging
                    logging.getLogger("scribe3.motif_craft").info(
                        "motif %s phase advanced: %s → %s", mid, phase, new_phase)
                except Exception:
                    pass
        rows.append(row)
        if phase == "rest":
            neutral.append(row)
            continue
        h = heat_info["heat"]
        if h == "hot":
            avoid_overuse.append(row)
        elif h == "cold":
            must_echo.append(row)
        else:
            neutral.append(row)
    return {
        "must_echo": must_echo,
        "avoid_overuse": avoid_overuse,
        "neutral": neutral,
        "rows": rows,
        "next_chapter": int(next_chapter),
    }


def _entry_line(m: dict) -> str:
    name = (m.get("name") or "").replace("\n", " ").strip()
    if not name:
        return ""
    theme = (m.get("theme") or "").replace("\n", " ").strip()
    terms = parse_echo_terms(m.get("echoes"), m.get("echo_terms"))
    echoes = "/".join(terms) if terms else (m.get("echoes") or "").replace("\n", " ").strip()
    entry = name
    if theme:
        entry += f"：{theme}"
    if echoes:
        entry += f"（回声:{echoes}）"
    heat = m.get("heat")
    if heat:
        entry += f"[{heat}]"
    return entry


def motif_schedule_directives(
    motifs: list[dict],
    touch_map: dict[str, list[int]],
    next_chapter: int,
    touched: list[dict] | None = None,
    *,
    overheat_streak: int = DEFAULT_OVERHEAT_STREAK,
    cold_gap: int = DEFAULT_COLD_GAP,
) -> dict[str, Any]:
    """章前/注入共用:must_echo + avoid_overuse + 可编织清单 + 上章触及。

    不再 sole 依赖固定 top-5 全表 dump。
    """
    sched = schedule_motifs(
        motifs, touch_map, next_chapter,
        overheat_streak=overheat_streak, cold_gap=cold_gap)
    must_lines = [x for x in (_entry_line(m) for m in sched["must_echo"]) if x]
    avoid_lines = [x for x in (_entry_line(m) for m in sched["avoid_overuse"]) if x]
    # 编织清单:优先 must_echo,再 neutral 补到 5,避开 overuse
    weave: list[str] = []
    for m in sched["must_echo"] + sched["neutral"]:
        line = _entry_line(m)
        if line and line not in weave:
            weave.append(line)
        if len(weave) >= 5:
            break
    # 若全书只有 hot,仍给 1–2 条以免空(标 avoid)
    if not weave:
        for m in sched["avoid_overuse"][:2]:
            line = _entry_line(m)
            if line:
                weave.append(line)

    touched_lines: list[str] = []
    for it in touched or []:
        n = (it.get("name") or it.get("motif_id") or "").replace("\n", " ").strip()
        if not n:
            continue
        e = (it.get("evidence") or "").replace("\n", " ").strip()
        touched_lines.append(f"{n}" + (f"「{e}」" if e else ""))

    return {
        "lines": weave,
        "must_echo": must_lines,
        "avoid_overuse": avoid_lines,
        "touched": touched_lines,
        "count": len(weave),
        "schedule": sched,
    }


def generation_motif_block(directives: dict) -> str:
    """写作路径注入块文案(可拼进 _codex_block)。空则 ""。"""
    parts: list[str] = []
    if directives.get("must_echo"):
        parts.append(
            "【母题·该回声 must_echo】\n"
            + "\n".join(f"- {x}" for x in directives["must_echo"]))
    if directives.get("avoid_overuse"):
        parts.append(
            "【母题·过热避免连刷 avoid_overuse】\n"
            + "\n".join(f"- {x}" for x in directives["avoid_overuse"]))
    if directives.get("lines"):
        parts.append(
            "【贯穿母题·可主动编织】\n"
            + "\n".join(f"- {x}" for x in directives["lines"]))
    return "\n".join(parts)


def evidence_acceptable(evidence: str | None) -> bool:
    return len((evidence or "").strip()) >= MIN_EVIDENCE_LEN
