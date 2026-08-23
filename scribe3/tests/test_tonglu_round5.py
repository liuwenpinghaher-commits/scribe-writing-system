"""第五轮精修：色值、队列上限、慢搜日志、接线。不起 Surreal。"""
from __future__ import annotations

import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_r5_01_promise_bar_uses_warn_token():
    tl = (ROOT / "scribe3/web/src/views/TimelineView.jsx").read_text(encoding="utf-8")
    assert "color:#7c5a10" not in tl
    assert "var(--color-warn)" in tl


def test_r5_02_critical_stall_has_inbox_action():
    jv = (ROOT / "scribe3/web/src/views/JourneyView.jsx").read_text(encoding="utf-8")
    assert "journey-stall-open-inbox" in jv
    assert "查看收件箱" in jv
    assert "s3-right-tab" in jv


def test_r5_03_extract_retry_caps_at_200():
    from scribe3 import extract_retry as er
    er._PENDING.clear()
    try:
        for i in range(250):
            er.queue_extract_retry(f"t{i}")
        assert len(er.pending_extracts()) == 200
        assert er.pending_extracts()[0]["text"] == "t50"
        assert er.pending_extracts()[-1]["text"] == "t249"
    finally:
        er._PENDING.clear()


def test_r5_04_05_stage_zh_and_grid_transition():
    jv = (ROOT / "scribe3/web/src/views/JourneyView.jsx").read_text(encoding="utf-8")
    assert "STAGE_ZH" in jv
    assert "stageInfo.label" in jv
    assert "grid-rows-[1fr]" in jv
    assert "grid-rows-[0fr]" in jv
    assert "duration-200" in jv


def test_r5_06_dismiss_disabled_matches_lock():
    dock = (ROOT / "scribe3/web/src/studioDocks.jsx").read_text(encoding="utf-8")
    assert "disabled={!!dismissBusy}" in dock
    assert "if (!id || dismissBusy) return" in dock


def test_r5_07_search_debounces():
    src = (ROOT / "scribe3/web/src/capabilities/search/SearchDirectory.jsx").read_text(encoding="utf-8")
    assert "setTimeout" in src
    assert "300" in src


def test_r5_08_domain_hint_jsdoc():
    src = (ROOT / "scribe3/web/src/lib/pilotRollback.js").read_text(encoding="utf-8")
    assert "fallback" in src.lower() or "降级" in src
    assert "next_step.domain" in src or "next_step.domain" in src.replace("\\", "")


def test_r5_09_knn_logs_slow():
    from scribe3.store.materials import MaterialsMixin
    src = inspect.getsource(MaterialsMixin._material_knn_scores)
    assert "time.perf_counter" in src
    assert "knn search slow" in src
    assert "0.5" in src


def test_r5_10_causal_svg_aria():
    tl = (ROOT / "scribe3/web/src/views/TimelineView.jsx").read_text(encoding="utf-8")
    assert 'aria-label' in tl and "因果关系连线图" in tl
    assert 'role' in tl and "img" in tl
