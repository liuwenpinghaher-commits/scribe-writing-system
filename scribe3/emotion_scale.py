"""GAP-14/18：情绪值计算 — 可切换 heuristic | lexicon | llm_sim。

输出标尺约定：**-5.0 … +5.0**（负面…正面）。
旧 0–1 张力请用 :func:`tension_01_to_signed` 映射。
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import os
import re
from typing import Any

# 轻量中文词表（可扩展；非宣称 NLP 行业精度）
_POS = ("喜", "欢", "安心", "希望", "温暖", "释然", "痛快", "爱", "笑", "光明")
_NEG = ("怒", "惧", "悲", "恨", "绝望", "冰冷", "恐惧", "痛", "死", "黑暗", "恨不得")


def emotion_mode() -> str:
    raw = (get_flag("SCRIBE3_EMOTION_MODE") or "lexicon").strip().lower()
    if raw in ("heuristic", "lexicon", "llm_sim", "legacy01"):
        return raw
    return "lexicon"


def tension_01_to_signed(t: float) -> float:
    """0–1 → -5…+5（0.5 映射 0）。"""
    try:
        x = float(t)
    except Exception:
        x = 0.5
    x = max(0.0, min(1.0, x))
    return round((x - 0.5) * 10.0, 3)


def score_prose_emotion(prose: str, *, mode: str | None = None) -> dict[str, Any]:
    """对正文打情绪分。返回 value ∈ [-5,5] + 明细。"""
    m = (mode or emotion_mode()).strip().lower()
    text = prose or ""
    if m == "legacy01":
        # 兼容旧张力：长度启发式 0-1 再映射
        t = min(1.0, len(text) / 3000.0) * 0.5 + 0.25
        return {
            "value": tension_01_to_signed(t),
            "scale": [-5.0, 5.0],
            "mode": m,
            "legacy_01": round(t, 3),
        }
    pos = sum(1 for w in _POS if w in text)
    neg = sum(1 for w in _NEG if w in text)
    # 标点兴奋度
    bang = len(re.findall(r"[！!]{1,3}", text))
    raw = (pos - neg) + 0.15 * bang
    # 归一到约 [-5,5]
    value = max(-5.0, min(5.0, raw * 1.2))
    if m == "llm_sim":
        # 二次平滑：向 0 收缩少许 + 保留极性（可测、无网）
        value = round(value * 0.85, 3)
    else:
        value = round(value, 3)
    return {
        "value": value,
        "scale": [-5.0, 5.0],
        "mode": m,
        "pos_hits": pos,
        "neg_hits": neg,
        "advisory": True,
        "not_a_score": "literary_quality",
    }


def chapter_emotion_points(chapters: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    pts: list[dict[str, Any]] = []
    for ch in chapters or []:
        if not isinstance(ch, dict):
            continue
        seq = int(ch.get("seq") or ch.get("chapter") or 0)
        if seq <= 0:
            continue
        prose = str(ch.get("prose") or ch.get("synopsis") or "")
        sc = score_prose_emotion(prose)
        pts.append({
            "seq": seq,
            "emotion": sc["value"],
            "label": "负" if sc["value"] < -1.5 else ("正" if sc["value"] > 1.5 else "平"),
            "mode": sc["mode"],
        })
    pts.sort(key=lambda p: p["seq"])
    return pts
