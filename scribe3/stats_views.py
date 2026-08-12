"""S-6: 读取聚合视图表（stats_*）。flag 关或视图不存在时回退 ad-hoc count。"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("scribe3.stats_views")


def stats_view_enabled() -> bool:
    try:
        from scribe3.surreal_flags import stats_view_read
        return stats_view_read()
    except Exception:
        return False


def read_chapter_count(store: Any) -> int:
    """章计数：优先 stats_chapter_count 视图。"""
    if stats_view_enabled():
        try:
            rows = store.stats_chapter_count_view() or []
            if rows and isinstance(rows[0], dict) and rows[0].get("n") is not None:
                return int(rows[0]["n"])
        except Exception as e:
            _log.debug("stats_chapter_count fallback: %s", e)
    try:
        rows = store.count_chapters_group() or []
        if rows and isinstance(rows[0], dict):
            return int(rows[0].get("n") or 0)
    except Exception:
        pass
    try:
        return len(store.chapters_lite() or [])
    except Exception:
        return 0


def read_open_promise_count(store: Any) -> int:
    if stats_view_enabled():
        try:
            rows = store.stats_open_promises_view() or []
            if rows and isinstance(rows[0], dict) and rows[0].get("n") is not None:
                return int(rows[0]["n"])
        except Exception as e:
            _log.debug("stats_open_promises fallback: %s", e)
    try:
        rows = store.count_open_promises_group() or []
        if rows and isinstance(rows[0], dict):
            return int(rows[0].get("n") or 0)
    except Exception:
        return 0
    return 0


def read_total_words(store: Any) -> int:
    """GAP-5：全书字数聚合（优先 stats_total_words 视图）。"""
    if stats_view_enabled():
        try:
            rows = store.stats_total_words_view() or []
            if rows and isinstance(rows[0], dict) and rows[0].get("total_words") is not None:
                return int(rows[0]["total_words"] or 0)
        except Exception as e:
            _log.debug("stats_total_words fallback: %s", e)
    total = 0
    try:
        rows = store.sum_chapter_word_counts() or []
        if rows and isinstance(rows[0], dict) and rows[0].get("total_words") is not None:
            return int(rows[0]["total_words"] or 0)
    except Exception:
        pass
    try:
        for ch in store.chapters_lite() or []:
            if not isinstance(ch, dict):
                continue
            for k in ("qc_word_count", "word_count", "words"):
                if ch.get(k) is not None:
                    try:
                        total += int(ch.get(k) or 0)
                        break
                    except Exception:
                        pass
            else:
                prose = str(ch.get("prose") or "")
                if prose:
                    total += len(prose)
    except Exception:
        pass
    return total


def read_phase_distribution(store: Any) -> list[dict[str, Any]]:
    """GAP-5：阶段分布。"""
    if stats_view_enabled():
        try:
            rows = store.stats_phase_distribution_view() or []
            out = []
            for r in rows:
                if isinstance(r, dict):
                    out.append({
                        "stage": r.get("stage") or "unknown",
                        "n": int(r.get("n") or 0),
                    })
            if out:
                return out
        except Exception as e:
            _log.debug("stats_phase_distribution fallback: %s", e)
    counts: dict[str, int] = {}
    try:
        for ch in store.chapters_lite() or []:
            if not isinstance(ch, dict):
                continue
            stg = str(ch.get("stage") or ch.get("phase") or "unknown")
            counts[stg] = counts.get(stg, 0) + 1
    except Exception:
        pass
    return [{"stage": k, "n": v} for k, v in sorted(counts.items())]


def read_stats_bundle(store: Any) -> dict[str, Any]:
    """组合统计（/debug/stats）。"""
    return {
        "chapter_count": read_chapter_count(store),
        "open_promises": read_open_promise_count(store),
        "total_words": read_total_words(store),
        "phase_distribution": read_phase_distribution(store),
        "stats_view_enabled": stats_view_enabled(),
    }
