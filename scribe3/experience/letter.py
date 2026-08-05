"""全书 re-vision 问诊信 · 纯聚合,无总分。"""
from __future__ import annotations

from typing import Any

from scribe3.experience.modes import normalize_revision_mode, revision_mode_priority

LETTER_KINDS = (
    "opening_promise",
    "middle_sag",
    "character_arc",
    "theme_or_intent",
    "unpaid_promise",
    "scene_kinetics",
    "pacing",
    "info_control",
    "latent_seed",
    "external_read",
    "custom",
)
ITEM_STATUSES = ("open", "acknowledged", "waived", "fixed")


def letter_has_total_score(letter: dict) -> bool:
    """宪法:letter 不得含加权总分字段。"""
    if not isinstance(letter, dict):
        return False
    banned = ("total_score", "composite_score", "overall_score", "grade_total")
    if any(k in letter for k in banned):
        return True
    # 也不允许 items 上挂 score 汇总
    if "score_sum" in letter or "scores" in letter and isinstance(letter.get("scores"), (int, float)):
        return True
    return False


def _item(item_id: str, kind: str, question: str, evidence: list[dict],
          *, severity: str = "decision") -> dict[str, Any]:
    if kind not in LETTER_KINDS:
        kind = "custom"
    return {
        "id": item_id,
        "kind": kind,
        "severity": severity,  # decision|nudge|info — 非 blocking 门闩
        "question": question,
        "evidence": evidence or [],
        "status": "open",
        "author_note": "",
        "history": [],
    }


def update_letter_item_status(
    letter: dict,
    item_id: str,
    *,
    status: str,
    author_note: str = "",
) -> dict:
    """更新 item 状态并保留审计(不删项)。返回新 letter 副本。"""
    if status not in ITEM_STATUSES:
        raise ValueError(f"非法 status:{status}")
    out = dict(letter)
    items = [dict(i) for i in (out.get("items") or [])]
    found = False
    for i in items:
        if i.get("id") == item_id:
            found = True
            hist = list(i.get("history") or [])
            hist.append({
                "from": i.get("status"),
                "to": status,
                "note": (author_note or "")[:200],
            })
            i["status"] = status
            i["author_note"] = (author_note or i.get("author_note") or "")[:500]
            i["history"] = hist[-20:]
            break
    if not found:
        raise KeyError(item_id)
    out["items"] = items
    return out


def _apply_overlay(items: list[dict], overlay: dict[str, dict]) -> list[dict]:
    out = []
    for it in items:
        o = dict(it)
        ov = overlay.get(o["id"]) or {}
        if ov.get("status") in ITEM_STATUSES:
            o["status"] = ov["status"]
        if "author_note" in ov:
            o["author_note"] = ov.get("author_note") or ""
        if ov.get("history"):
            o["history"] = list(ov["history"])
        out.append(o)
    return out


def _sort_by_mode(items: list[dict], mode: str) -> list[dict]:
    order = revision_mode_priority(mode)
    rank = {k: i for i, k in enumerate(order)}
    return sorted(items, key=lambda x: (rank.get(x.get("kind"), 99), x.get("id") or ""))


def build_revision_letter(
    st,
    *,
    work: str = "main",
    mode: str | None = None,
    status_overlay: dict[str, dict] | None = None,
    external_feedback: list[dict] | None = None,
    seed_suggestions: list[dict] | None = None,
    scene_diagnostics: list[dict] | None = None,
) -> dict[str, Any]:
    """从 store 只读字段聚合问诊信。

    可构造条件:
    - intent 有 reader_feeling/red_lines → opening_promise / theme_or_intent
    - 压力级单调/多章 → middle_sag / pacing
    - open overdue promises → unpaid_promise
    - 弧光计划过期(若有) → character_arc
    """
    mode = normalize_revision_mode(mode)
    items: list[dict] = []
    evidence_base: list[dict] = []

    # —— 意图 / 开篇承诺 ——
    intent: dict = {}
    try:
        if hasattr(st, "get_intent"):
            intent = st.get_intent() or {}
    except Exception:
        intent = {}
    if intent.get("reader_feeling") or intent.get("red_lines") or intent.get("emotional_arc"):
        items.append(_item(
            "intent-opening",
            "opening_promise",
            "开篇向读者承诺的感受/问题,在最新章是否仍在兑现?"
            f"（意图摘录:读者感受「{(intent.get('reader_feeling') or '—')[:40]}」）",
            [{"type": "intent", "reader_feeling": intent.get("reader_feeling"),
              "red_lines": intent.get("red_lines")}],
        ))
        items.append(_item(
            "intent-theme",
            "theme_or_intent",
            "红线与情感弧是否被最近正文冒犯或稀释?"
            f"（红线:「{(intent.get('red_lines') or '—')[:60]}」）",
            [{"type": "intent", "emotional_arc": intent.get("emotional_arc"),
              "red_lines": intent.get("red_lines")}],
        ))

    # —— 章节压力 / 中段 ——
    chapters: list[dict] = []
    try:
        if hasattr(st, "chapters_lite"):
            chapters = list(st.chapters_lite() or [])
        elif hasattr(st, "list_chapters"):
            chapters = list(st.list_chapters() or [])
    except Exception:
        chapters = []
    n_ch = len(chapters)
    if n_ch >= 3:
        items.append(_item(
            "struct-middle",
            "middle_sag",
            f"全书已有 {n_ch} 章:中段是否只在赶路、缺少不可逆代价?"
            "请标出最空的一章并决定砍/并/加戏。",
            [{"type": "chapters", "count": n_ch,
              "seqs": [c.get("seq") for c in chapters[:40]]}],
        ))
        items.append(_item(
            "struct-pacing",
            "pacing",
            "张弛是否长时间同质?若大纲标了压力级,连续高压/低压是否超过三章?",
            [{"type": "pacing_hint", "chapter_count": n_ch}],
            severity="nudge",
        ))

    # 尝试张弛检测
    try:
        from scribe3.brief import chapter_draft_text, find_tension_monotony, parse_chapter_meta
        metas = []
        for c in chapters:
            m = parse_chapter_meta(chapter_draft_text(c))
            if m and m.get("pressure") is not None:
                metas.append({"seq": c.get("seq"), **m})
        mono = find_tension_monotony(metas) if metas else []
        if mono:
            items.append(_item(
                "struct-tension-flat",
                "middle_sag",
                f"检测到张弛单调 {len(mono)} 处,中段是否塌陷?",
                [{"type": "tension_monotony", "findings": mono[:8]}],
            ))
    except Exception:
        pass

    # —— 未回收伏笔 ——
    overdue: list = []
    open_p: list = []
    try:
        if hasattr(st, "promises_with_lifecycle"):
            rows = list(st.promises_with_lifecycle() or [])
            for p in rows:
                if (p.get("status") or "open") != "open":
                    continue
                open_p.append(p)
                win = p.get("window") or {}
                if win.get("state") == "overdue" or p.get("_overdue"):
                    overdue.append(p)
        elif hasattr(st, "open_promises"):
            open_p = list(st.open_promises() or [])
    except Exception:
        pass
    if overdue or open_p:
        sample = overdue[:5] if overdue else open_p[:5]
        items.append(_item(
            "promise-unpaid",
            "unpaid_promise",
            f"有 {len(overdue) or len(open_p)} 条开着的承诺线"
            f"{'（含超期）' if overdue else ''}:哪些必须在本卷回收?",
            [{"type": "promise", "text": (p.get("text") or "")[:80],
              "setup_chapter": p.get("setup_chapter")} for p in sample],
        ))

    # —— 弧光 ——
    try:
        # 尽力从 store 取角色锚;没有则在有多章时仍给通用弧线问
        has_arc = False
        if hasattr(st, "list_characters"):
            chars = st.list_characters() or []
            has_arc = bool(chars)
        if n_ch >= 2 or has_arc:
            items.append(_item(
                "arc-general",
                "character_arc",
                "主角/焦点者从第1章到最新章,内在缺陷或欲望是否发生不可逆改变?"
                "若无,是刻意停滞还是写丢了?",
                [{"type": "arc", "chapter_count": n_ch}],
            ))
    except Exception:
        if n_ch >= 2:
            items.append(_item(
                "arc-general",
                "character_arc",
                "主角内在弧线是否可见?关键选择是否赚够?",
                [{"type": "arc", "chapter_count": n_ch}],
            ))

    # —— 场景动能诊断(外部传入) ——
    for i, d in enumerate(scene_diagnostics or []):
        items.append(_item(
            f"scene-{d.get('seq', i)}-{d.get('code', i)}",
            "scene_kinetics",
            d.get("message") or "场景动能断链,请补反应/决定或改戏。",
            [{"type": "scene_grid", **{k: d.get(k) for k in ("seq", "code", "detail")}}],
            severity="nudge",
        ))

    # —— 种子 ——
    for s in seed_suggestions or []:
        if s.get("promoted"):
            continue
        items.append(_item(
            f"seed-{s.get('id')}",
            "latent_seed",
            f"疑似未登记种子:「{(s.get('text') or '')[:40]}」——要升格为伏笔台账吗?",
            [{"type": "seed", **s}],
            severity="nudge",
        ))

    # —— 外部读感 ——
    for i, fb in enumerate(external_feedback or []):
        items.append(_item(
            f"ext-{fb.get('id', i)}",
            "external_read",
            fb.get("question") or fb.get("body") or "外部读者意见",
            [{"type": "feedback", **fb}],
            severity="decision",
        ))

    # 去重 id
    seen = set()
    uniq = []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        uniq.append(it)

    uniq = _apply_overlay(uniq, status_overlay or {})
    uniq = _sort_by_mode(uniq, mode)

    letter = {
        "work": work,
        "mode": mode,
        "items": uniq,
        "item_count": len(uniq),
        "open_count": sum(1 for i in uniq if i.get("status") == "open"),
        "note": "责编式问诊:无总分;默认不进入定稿 blocking。文学上限仍由作者完成。",
        # 明确禁止总分
        "total_score": None,  # 占位声明为 null;letter_has_total_score 应忽略 null? 
    }
    # 宪法:不要 total_score 键存在为数字。删掉键更干净
    letter.pop("total_score", None)
    return letter
