"""故事线投影：Gantt 条 + 情绪曲线（O30/O31 · 纯函数 · 不宣称文学分）。"""
from __future__ import annotations

import re
from typing import Any


def _phase_of(ch: dict[str, Any]) -> str:
    try:
        from scribe3.chapter_stage import stage_from_chapter_dict
        p = stage_from_chapter_dict(ch)
        if p:
            return p
    except Exception:
        pass
    if (ch.get("prose") or "").strip():
        return "draft"
    # chapters_lite 无 prose：用 beats / scene_truth 推断
    if ch.get("beats") or ch.get("scene_truth"):
        return "beats"
    if (ch.get("synopsis") or ch.get("outline") or "").strip():
        return "outline"
    return "outline"


def _stakes_hint(ch: dict[str, Any]) -> str:
    syn = str(ch.get("synopsis") or ch.get("outline") or "")
    meta = ch.get("meta") if isinstance(ch.get("meta"), dict) else {}
    blob = syn + " " + str(meta.get("stakes") or "")
    if re.search(r"stakes\s*[:：]|赌注|代价|风险", blob, re.I):
        return "present"
    if len(syn.strip()) < 8:
        return "unknown"
    return "missing"


def _tension_score(ch: dict[str, Any]) -> float:
    """0–1 启发式张力（低成本辅字段）。

    D7 / DEFERRED：产品主标尺是 emotion ∈ [-5,+5]（见 emotion_scale）；
    本函数有意保留 0–1 启发式（零 LLM），不升级为 NLP。禁止当文学评分。
    """
    score = 0.2
    plan = ch.get("plan") if isinstance(ch.get("plan"), dict) else {}
    beats = plan.get("beats") or ch.get("beats") or []
    n_conflict = 0
    for b in beats if isinstance(beats, list) else []:
        if isinstance(b, dict):
            if str(b.get("conflict") or b.get("disaster") or "").strip():
                n_conflict += 1
        elif isinstance(b, str) and len(b) > 12:
            n_conflict += 0.5
    score += min(0.4, 0.08 * n_conflict)
    prose = str(ch.get("prose") or "")
    if len(prose) > 500:
        score += 0.15
    if len(prose) > 2000:
        score += 0.1
    sc = ch.get("scorecard") if isinstance(ch.get("scorecard"), dict) else {}
    # 仅作启发式，不输出「文学分」
    for k in ("tension", "conflict", "qc_causal"):
        v = sc.get(k)
        try:
            if v is not None and float(v) > 0:
                score += min(0.15, abs(float(v)) / 20.0)
        except Exception:
            pass
    return round(max(0.0, min(1.0, score)), 3)


def project_gantt_rows(
    chapters: list[dict[str, Any]] | None,
    *,
    open_promises: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """章列表 → Gantt 行。"""
    rows: list[dict[str, Any]] = []
    prom = open_promises or []
    for ch in chapters or []:
        if not isinstance(ch, dict):
            continue
        seq = int(ch.get("seq") or ch.get("chapter") or 0)
        if seq <= 0:
            continue
        open_n = 0
        for p in prom:
            if not isinstance(p, dict):
                continue
            setup = p.get("setup_chapter") or p.get("chapter") or p.get("since")
            try:
                if setup is not None and int(setup) == seq:
                    open_n += 1
            except Exception:
                pass
        rows.append({
            "seq": seq,
            "title": str(ch.get("title") or f"第{seq}章"),
            "phase": _phase_of(ch),
            "volume": ch.get("volume") or ch.get("volume_id"),
            "promises_open": open_n,
            "stakes_hint": _stakes_hint(ch),
            "has_prose": bool((ch.get("prose") or "").strip()),
        })
    rows.sort(key=lambda r: r["seq"])
    return {
        "rows": rows,
        "count": len(rows),
        "surface": "storyline.gantt",
        "advisory": True,
        "not_a_score": "literary_quality",
    }


def project_emotion_curve(chapters: list[dict[str, Any]] | None) -> dict[str, Any]:
    """章列表 → 情绪/张力曲线点。

    GAP-14/18：默认输出 emotion ∈ [-5,5]；保留 tension 0–1 兼容字段。
    """
    points: list[dict[str, Any]] = []
    try:
        from scribe3.emotion_scale import score_prose_emotion, tension_01_to_signed
        use_scale = True
    except Exception:
        use_scale = False
    for ch in chapters or []:
        if not isinstance(ch, dict):
            continue
        seq = int(ch.get("seq") or ch.get("chapter") or 0)
        if seq <= 0:
            continue
        t = _tension_score(ch)
        if use_scale:
            prose = str(ch.get("prose") or ch.get("synopsis") or "")
            sc = score_prose_emotion(prose)
            emo = sc["value"]
            # 若正文空，回落映射张力
            if not prose.strip():
                emo = tension_01_to_signed(t)
            label = "负" if emo < -1.5 else ("正" if emo > 1.5 else "平")
            points.append({
                "seq": seq,
                "tension": t,
                "emotion": emo,
                "label": label,
                "scale": [-5.0, 5.0],
            })
        else:
            label = "低" if t < 0.35 else ("中" if t < 0.65 else "高")
            points.append({
                "seq": seq,
                "tension": t,
                "label": label,
            })
    points.sort(key=lambda p: p["seq"])
    out = {
        "points": points,
        "count": len(points),
        "surface": "storyline.emotion_curve",
        "advisory": True,
        "disclaimer": "情绪标尺 -5…+5（advisory），非文学评分，禁止当作 ≥9.5 证据",
        "not_a_kpi": "tokens_saved",
        "emotion_scale": [-5.0, 5.0],
    }
    # GAP-19：对标报告
    try:
        from scribe3.craft_ruler import craft_ruler_report
        out["craft_align"] = craft_ruler_report(points)
    except Exception:
        pass
    return out
