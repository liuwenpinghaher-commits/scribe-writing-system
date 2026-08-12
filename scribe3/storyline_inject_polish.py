"""故事线注入 polish（O33 / SL2 · 旗控 · 不挡 redline）。

- promise_mode=omit 为 P0 硬保证（默认不输出「开放伏笔：」正文）
- craft_only=false 的弧 notes 不进 text
- 热路径经 build_storyline_feed_context 窗口切片后与 preview 同源
"""
from __future__ import annotations

import os
from typing import Any


def storyline_inject_enabled() -> bool:
    try:
        from scribe3.feature_flags import flag_truthy
        return flag_truthy("SCRIBE3_STORYLINE_INJECT")
    except Exception:
        raw = (os.environ.get("SCRIBE3_STORYLINE_INJECT") or "1").strip().lower()
        return raw in ("1", "true", "yes", "on")


def promise_hint_enabled() -> bool:
    """SL3：可选一行伏笔计数提示；默认关。"""
    try:
        from scribe3.feature_flags import flag_truthy
        return flag_truthy("SCRIBE3_STORYLINE_PROMISE_HINT")
    except Exception:
        raw = (os.environ.get("SCRIBE3_STORYLINE_PROMISE_HINT") or "0").strip().lower()
        return raw in ("1", "true", "yes", "on")


def _normalize_craft_only(raw: Any, *, default: bool = True) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return default


def window_seqs(focus_seq: int | None, *, window: int = 2) -> list[int]:
    """焦点章 ±window 的 seq 列表（含 focus）。"""
    if focus_seq is None:
        return []
    f = int(focus_seq)
    w = max(0, int(window))
    return list(range(max(1, f - w), f + w + 1))


def filter_chapters_for_window(
    chapters: list[dict[str, Any]] | None,
    focus_seq: int | None,
    *,
    window: int = 2,
) -> list[dict[str, Any]]:
    """先切片再 project：仅 focus 窗口章。"""
    allowed = set(window_seqs(focus_seq, window=window))
    if not allowed:
        return list(chapters or [])
    out: list[dict[str, Any]] = []
    for ch in chapters or []:
        if not isinstance(ch, dict):
            continue
        try:
            seq = int(ch.get("seq") or ch.get("chapter") or 0)
        except Exception:
            continue
        if seq in allowed:
            out.append(ch)
    return out


def arc_summaries_for_inject(
    storylines: list[dict[str, Any]] | None,
    focus_seq: int | None,
    *,
    max_arcs: int = 2,
    note_chars: int = 40,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """返回 (arc_summaries 可注入, craft_only_injected_ids, craft_only_skipped).

    规则：仅 craft_only=true 的 notes 进入 summaries；false 记入 skipped。
    """
    f = int(focus_seq) if focus_seq is not None else None
    injected: list[dict[str, Any]] = []
    injected_ids: list[str] = []
    skipped: list[str] = []
    for sl in storylines or []:
        if not isinstance(sl, dict):
            continue
        sid = str(sl.get("id") or "")
        seqs: list[int] = []
        for x in sl.get("chapter_seqs") or []:
            try:
                seqs.append(int(x))
            except Exception:
                continue
        # 无 focus 时取前 max_arcs；有 focus 时仅覆盖 focus 的弧
        if f is not None and seqs and f not in seqs:
            continue
        co = _normalize_craft_only(sl.get("craft_only"), default=True)
        notes = str(sl.get("notes") or "").strip()
        if not co:
            if notes:
                skipped.append(sid or sl.get("title") or "?")
            continue
        if not notes and not (sl.get("title") or "").strip():
            continue
        summary = {
            "id": sid,
            "title": str(sl.get("title") or "")[:40],
            "arc_kind": str(sl.get("arc_kind") or "main")[:24],
            "notes": notes[:note_chars] if notes else "",
            "craft_only": True,
        }
        injected.append(summary)
        if sid:
            injected_ids.append(sid)
        if len(injected) >= max_arcs:
            break
    return injected, injected_ids, skipped


def build_storyline_inject_segment(
    *,
    focus_seq: int | None = None,
    gantt_rows: list[dict[str, Any]] | None = None,
    open_promise_texts: list[str] | None = None,
    emotion_point: dict[str, Any] | None = None,
    arc_summaries: list[dict[str, Any]] | None = None,
    promise_mode: str = "omit",
    open_promise_count: int | None = None,
    craft_only_injected_ids: list[str] | None = None,
    craft_only_skipped: list[str] | None = None,
) -> dict[str, Any]:
    """短注入段 + raw/audit；默认 omit 开放伏笔正文。"""
    mode = (promise_mode or "omit").strip().lower()
    if mode not in ("omit", "hint_only", "full"):
        mode = "omit"

    lines: list[str] = []
    raw_bits: list[str] = []
    if focus_seq:
        lines.append(f"焦点章：第{int(focus_seq)}章")
        raw_bits.append(f"focus={focus_seq}")

    if gantt_rows:
        nearby = [r for r in gantt_rows if isinstance(r, dict)][:5]
        phases = ", ".join(f"#{r.get('seq')}:{r.get('phase')}" for r in nearby)
        if phases:
            lines.append(f"近程阶段：{phases}")
            raw_bits.append(phases)

    for arc in (arc_summaries or [])[:2]:
        if not isinstance(arc, dict):
            continue
        title = str(arc.get("title") or "").strip()
        kind = str(arc.get("arc_kind") or "").strip()
        notes = str(arc.get("notes") or "").strip()
        # 二次门：即使调用方漏过滤，也不注入 craft_only=false
        if not _normalize_craft_only(arc.get("craft_only"), default=True):
            continue
        bits = []
        if title:
            bits.append(title)
        if kind:
            bits.append(f"({kind})")
        if notes:
            bits.append(f"— {notes[:40]}")
        if bits:
            lines.append("相关弧：" + " ".join(bits))
            raw_bits.append(f"arc={title}")

    # 伏笔：omit = 不输出「开放伏笔：」正文行（P0 硬保证）
    if mode == "full":
        for t in (open_promise_texts or [])[:5]:
            s = str(t).strip()
            if s:
                lines.append(f"开放伏笔：{s[:80]}")
                raw_bits.append(s)
    elif mode == "hint_only":
        n = open_promise_count
        if n is None:
            n = len([t for t in (open_promise_texts or []) if str(t).strip()])
        if n and promise_hint_enabled():
            lines.append(f"未收线伏笔约 {int(n)} 条（详见章前简报，勿当设定点名）")
            raw_bits.append(f"promise_hint={n}")

    if emotion_point and emotion_point.get("label"):
        lines.append(
            f"张力启发：{emotion_point.get('label')}"
            f"（启发式，非文学评分）"
        )

    text = ""
    if lines:
        text = (
            "\n\n【故事线提示｜借鉴勿当设定点名】\n"
            + "\n".join(f"- {x}" for x in lines)
            + "\n"
        )

    notes_in_prompt = any(
        str(a.get("notes") or "").strip()
        for a in (arc_summaries or [])
        if isinstance(a, dict) and _normalize_craft_only(a.get("craft_only"), default=True)
    )

    return {
        "name": "storyline_polish",
        "layer": "supplemental",
        "text": text,
        "raw": "\n".join(raw_bits),
        "enabled": storyline_inject_enabled(),
        "promise_mode": mode,
        "audit": {
            "line_count": len(lines),
            "not_a_kpi": "tokens_saved",
            "redline_safe": True,
            "source": "storyline_inject_polish.v1",
            "promise_mode": mode,
            "notes_in_prompt": notes_in_prompt,
            "craft_only_injected_ids": list(craft_only_injected_ids or []),
            "craft_only_skipped": list(craft_only_skipped or []),
            "has_open_promise_body": "开放伏笔：" in text,
        },
        "control": {"uses_tokens_saved": False},
    }


def prepare_write_storyline_inject(
    st: Any,
    *,
    chapter: int | None,
    work: str | None = "main",
    window: int = 2,
    promise_mode: str = "omit",
) -> dict[str, Any]:
    """写路径热入口：组装 storyline 段 text + budget meta。

    **永不抛出**（fail-soft）：异常时仍返回可写入 budget_report 的 meta。
    调用方负责 join 前 `_push("storyline_polish", …)` 与 `bud_rep["storyline_inject"]=meta`。
    """
    meta: dict[str, Any] = {
        "fed": False,
        "promise_mode": (promise_mode or "omit").strip().lower() or "omit",
        "applied": False,
        "enabled": False,
    }
    try:
        if not storyline_inject_enabled():
            return {"meta": meta, "text": ""}
        chapters: list = []
        lines: list = []
        prom: list = []
        try:
            if st is not None and hasattr(st, "chapters_lite"):
                chapters = list(st.chapters_lite() or [])
            elif st is not None and hasattr(st, "list_chapters"):
                chapters = list(st.list_chapters() or [])
        except Exception:
            chapters = []
        try:
            if st is not None and hasattr(st, "list_storylines"):
                lines = list(st.list_storylines() or [])
        except Exception:
            try:
                from scribe3.storyline_store import list_storylines as mem_list
                lines = list(mem_list(str(work or "main")) or [])
            except Exception:
                lines = []
        try:
            if st is not None and hasattr(st, "open_promises"):
                prom = list(st.open_promises() or [])
            elif st is not None and hasattr(st, "list_promises"):
                prom = list(st.list_promises() or [])
        except Exception:
            prom = []
        feed = build_storyline_feed_context(
            focus_seq=int(chapter) if chapter is not None else None,
            chapters=chapters,
            storylines=lines,
            open_promises=prom,
            window=window,
            promise_mode=promise_mode or "omit",
        )
        seg = feed.get("segment") or {}
        text = str(seg.get("text") or "")
        meta = {
            "fed": bool(feed.get("fed")),
            "promise_mode": str(feed.get("promise_mode") or "omit"),
            "applied": bool(text.strip()),
            "enabled": True,
            "window_seqs": list(feed.get("window_seqs") or []),
            "notes_in_prompt": bool(feed.get("notes_in_prompt")),
            "craft_only_injected_ids": list(feed.get("craft_only_injected_ids") or []),
            "craft_only_skipped": list(feed.get("craft_only_skipped") or []),
            "audit": seg.get("audit"),
        }
        return {"meta": meta, "text": text}
    except Exception as e:
        return {
            "meta": {
                "fed": False,
                "promise_mode": "omit",
                "applied": False,
                "enabled": True,
                "error": str(e)[:160],
            },
            "text": "",
        }


def build_storyline_feed_context(
    *,
    focus_seq: int | None,
    chapters: list[dict[str, Any]] | None = None,
    storylines: list[dict[str, Any]] | None = None,
    open_promises: list[Any] | None = None,
    window: int = 2,
    promise_mode: str = "omit",
    use_store_chapters: bool = True,
) -> dict[str, Any]:
    """窗口切片 + 投影 + 弧 notes 过滤 → segment 参数字典。

    热路径与 inject-preview(use_store=1) 同源。
    """
    from scribe3.storyline_project import project_gantt_rows, project_emotion_curve

    win_ch = filter_chapters_for_window(chapters, focus_seq, window=window)
    gantt = project_gantt_rows(win_ch, open_promises=open_promises if isinstance(open_promises, list) else None)
    emo = project_emotion_curve(win_ch)
    pt = None
    if focus_seq and emo.get("points"):
        pt = next(
            (p for p in emo["points"] if int(p.get("seq") or 0) == int(focus_seq)),
            None,
        )

    arcs, inj_ids, skipped = arc_summaries_for_inject(storylines, focus_seq)

    # omit：不传 open_promise_texts 正文
    mode = (promise_mode or "omit").strip().lower()
    open_texts: list[str] = []
    open_count = 0
    if open_promises:
        for p in open_promises:
            if isinstance(p, str) and p.strip():
                open_count += 1
                if mode == "full":
                    open_texts.append(p.strip())
            elif isinstance(p, dict):
                open_count += 1
                if mode == "full":
                    t = str(p.get("text") or p.get("body") or p.get("title") or "").strip()
                    if t:
                        open_texts.append(t)

    seg = build_storyline_inject_segment(
        focus_seq=focus_seq,
        gantt_rows=gantt.get("rows"),
        open_promise_texts=open_texts if mode == "full" else [],
        emotion_point=pt,
        arc_summaries=arcs,
        promise_mode=mode,
        open_promise_count=open_count,
        craft_only_injected_ids=inj_ids,
        craft_only_skipped=skipped,
    )
    return {
        "segment": seg,
        "window_seqs": window_seqs(focus_seq, window=window),
        "gantt": gantt,
        "emotion": emo,
        "arc_summaries": arcs,
        "promise_mode": mode,
        "fed": True,
        "notes_in_prompt": bool(seg.get("audit", {}).get("notes_in_prompt")),
        "craft_only_injected_ids": inj_ids,
        "craft_only_skipped": skipped,
    }
