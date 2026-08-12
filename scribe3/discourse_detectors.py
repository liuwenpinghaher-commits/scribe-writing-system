"""话语层 P0 纯检测（Week-1 · 无 LLM · 不写 issues[]）。

算法 A info_delta · 算法 C hook_on_page · 呼吸聚合。
"""
from __future__ import annotations

import re
from typing import Any

from scribe3.discourse_craft_ssot import product_label, tip_text

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def cjk_chars(text: str) -> str:
    return "".join(_CJK_RE.findall(str(text or "")))


def cjk_bigrams(text: str) -> set[str]:
    hans = cjk_chars(text)
    if len(hans) < 2:
        return set()
    return {hans[i : i + 2] for i in range(len(hans) - 1)}


def detect_info_delta(
    focus_synopsis: str,
    near_synopses: list[str] | None = None,
    *,
    focus_event_ids: set[str] | None = None,
    near_event_ids: set[str] | None = None,
    threshold: float = 0.08,
    min_focus_chars: int = 40,
) -> dict[str, Any]:
    """算法 A：CJK bigram 增量；有新 event 则不报警。"""
    focus = str(focus_synopsis or "").strip()
    if len(re.sub(r"\s+", "", focus)) < min_focus_chars:
        return {
            "status": "skip",
            "score": None,
            "emit": False,
            "reason": "focus_synopsis_short",
        }
    F = cjk_bigrams(focus)
    N: set[str] = set()
    for s in near_synopses or []:
        N |= cjk_bigrams(s)
    new = F - N
    score = len(new) / max(len(F), 1)
    fe = set(focus_event_ids or ())
    ne = set(near_event_ids or ())
    new_events = fe - ne
    if new_events:
        return {
            "status": "ok",
            "score": round(score, 4),
            "emit": False,
            "reason": "new_events",
            "new_events": list(new_events)[:8],
            "new_tokens_sample": list(new)[:8],
        }
    emit = score < threshold and len(F) > 0
    return {
        "status": "ok",
        "score": round(score, 4),
        "emit": bool(emit),
        "threshold": threshold,
        "new_tokens_sample": list(new)[:8],
        "reason": "low_delta" if emit else "ok",
    }


def detect_hook_on_page(
    prose: str,
    hook_text: str,
    *,
    threshold: float = 0.15,
) -> dict[str, Any]:
    """算法 C：章末 tail 与 hook 的 CJK bigram 重叠。"""
    body = str(prose or "")
    hook = str(hook_text or "").strip()
    if not body.strip() or not hook:
        return {
            "status": "skip",
            "hook_on_page_ok": None,
            "emit": False,
            "reason": "no_prose_or_hook",
        }
    tail_n = min(400, max(1, int(len(body) * 0.15)))
    prose_tail = body[-tail_n:]
    H = cjk_bigrams(hook)
    T = cjk_bigrams(prose_tail)
    if not H:
        return {
            "status": "skip",
            "hook_on_page_ok": None,
            "emit": False,
            "reason": "hook_no_cjk",
            "tail_n": tail_n,
        }
    overlap = len(H & T) / len(H)
    ok = overlap >= threshold
    return {
        "status": "ok",
        "hook_on_page_ok": bool(ok),
        "emit": not ok,
        "overlap": round(overlap, 4),
        "threshold": threshold,
        "tail_n": tail_n,
        "reason": "ok" if ok else "weak_landing",
    }


def detect_hook_plan(chapter: dict | None) -> dict[str, Any]:
    """规划侧：resolve_chapter_hook 为空 → emit。"""
    try:
        from scribe3.chapter_hooks import resolve_chapter_hook
        hook = resolve_chapter_hook(chapter if isinstance(chapter, dict) else None)
    except Exception as e:
        return {
            "status": "degraded",
            "hook_text": "",
            "emit": False,
            "error": str(e)[:120],
        }
    hook = str(hook or "").strip()
    return {
        "status": "ok",
        "hook_text": hook,
        "emit": not bool(hook),
        "reason": "missing_plan" if not hook else "ok",
    }


def aggregate_breath(
    prose: str,
    *,
    emotion_hits: list[dict] | None = None,
    rhythm: dict | None = None,
    god_view_count: int = 0,
) -> dict[str, Any]:
    """微观呼吸仪表（soft 主面）：复用既有 find_* 结果形状，不造 issues。"""
    body = str(prose or "")
    telling = list(emotion_hits or [])
    if emotion_hits is None and body.strip():
        try:
            from scribe3.critique import find_emotion_telling
            telling = list(find_emotion_telling(body) or [])
        except Exception:
            telling = []
    # 与 quality_issues 同口径：仅 verdict=="uniform" 才报「节奏过匀」；
    # verdict=="ok" / None 不算 hit（高 CV 变化句长不得假报）。
    rhythm_hit = False
    rhythm_meta: dict[str, Any] = {}
    if rhythm is not None:
        if isinstance(rhythm, dict):
            rhythm_meta = dict(rhythm)
            rhythm_hit = str(rhythm_meta.get("verdict") or "") == "uniform" or bool(
                rhythm_meta.get("hit") is True
            ) or str(rhythm_meta.get("uniform") or "") in ("1", "true", "uniform")
            # 显式 uniform=False / hit=False 不报
            if rhythm_meta.get("hit") is False:
                rhythm_hit = False
            if rhythm_meta.get("verdict") == "ok":
                rhythm_hit = False
        elif rhythm:
            rhythm_hit = True
    elif body.strip():
        try:
            from scribe3.critique import find_rhythm_uniformity
            r = find_rhythm_uniformity(body)
            if isinstance(r, dict):
                rhythm_meta = r
                rhythm_hit = str(r.get("verdict") or "") == "uniform"
            elif r:
                rhythm_hit = True
        except Exception:
            pass
    tips: list[dict[str, Any]] = []
    if telling:
        tips.append({
            "family": "telling",
            "product_label": product_label("telling"),
            "tip": tip_text("telling"),
            "count": len(telling),
        })
    if rhythm_hit:
        tips.append({
            "family": "rhythm",
            "product_label": product_label("rhythm"),
            "tip": tip_text("rhythm"),
        })
    if god_view_count > 0:
        tips.append({
            "family": "god_view",
            "product_label": product_label("god_view"),
            "tip": tip_text("god_view"),
            "count": god_view_count,
        })
    if len(tips) >= 2:
        tips.insert(0, {
            "family": "breath",
            "product_label": product_label("breath"),
            "tip": tip_text("breath"),
        })
    return {
        "telling_count": len(telling),
        "rhythm": rhythm_meta or {"hit": rhythm_hit},
        "god_view_count": int(god_view_count or 0),
        "tips": tips,
        "tight": len(tips) >= 2,
    }


def finding(
    type_key: str,
    message: str,
    *,
    meta: dict | None = None,
    severity: str = "advisory",
) -> dict[str, Any]:
    return {
        "type": type_key if type_key.startswith("discourse.") else f"discourse.{type_key}",
        "severity": severity,
        "message": message,
        "meta": dict(meta or {}),
    }
