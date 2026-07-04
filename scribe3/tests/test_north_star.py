"""北极星方案任务3 · 章级 scorecard TDD。

蓝图 §3-③ 前半:聚合现成确定性数据为章 scorecard,三分栏 constraints(硬)/
advisory_scores(软)/fulfillment(正向,本批占位空)——绝不合成总分;
挂 save_chapter 既有章缓存机制存稿即算(独立缓存表 chapter_scorecard,台账 D-008);
检测器挂了 → degraded 如实上报,不假绿;全知章 leaks=None(N/A≠0)。
"""
import pytest

import scribe3.app as A
from scribe3.scenario import luanshi_leak_world

from .test_app import _client


def test_scorecard_computed_on_save_three_panes(store):
    store.save_chapter(1, "他把伞收了,雨还没停。院里一个人也没有。", title="一")
    sc = store.get_chapter_scorecard(1)
    assert sc is not None
    assert set(sc) >= {"seq", "constraints", "advisory_scores", "fulfillment", "degraded"}
    c = sc["constraints"]
    assert set(c) >= {"leaks", "degeneration_blocking", "qc_causal", "promise_overdue"}
    assert sc["advisory_scores"]["ai_grade"]["grade"] in ("light", "medium", "heavy")
    assert sc["fulfillment"]["status"] == "not_available", "任务6 前 fulfillment 只占位"
    assert sc["degraded"] == []


def test_scorecard_leaks_none_for_omniscient_chapter(store):
    """全知章(无 focalizer)泄密不可判 → None(N/A),绝不写 0 假绿。"""
    store.save_chapter(1, "全知视角随便写。", title="一", focalizer=None)
    sc = store.get_chapter_scorecard(1)
    assert sc["constraints"]["leaks"] is None


def test_scorecard_counts_leaks_for_focalized_chapter(store):
    """限知章散文冒出帧外私密破绽词 → leaks 计数≥1(setpoint 违规可见)。"""
    luanshi_leak_world(store)
    store.save_chapter(1, "皂衣道人冷笑:这点钱,够你给老娘治眼么。",
                       title="对峙", focalizer="role:老道")
    sc = store.get_chapter_scorecard(1)
    assert sc["constraints"]["leaks"] >= 1


def test_scorecard_promise_overdue_counted(store):
    store.plant_promise("井里那口钟迟早要响", setup_chapter=1, tier="chapter")
    store.save_chapter(8, "第八章正文,旧伏笔早过了窗口。", title="八")
    sc = store.get_chapter_scorecard(8)
    assert sc["constraints"]["promise_overdue"] >= 1


def test_scorecard_degraded_honest_on_detector_failure(store, monkeypatch):
    """降级路径:ai_grade 检测器挂 → 存稿不受影响,degraded 如实上报,不假绿。"""
    import scribe3.critique as C

    def boom(*a, **kw):
        raise RuntimeError("detector down")

    monkeypatch.setattr(C, "aggregate_ai_grade", boom)
    store.save_chapter(2, "第二章正文。", title="二")
    sc = store.get_chapter_scorecard(2)
    assert "ai_grade" in sc["degraded"]
    assert sc["advisory_scores"]["ai_grade"] is None
    assert (store.get_chapter(2) or {}).get("prose"), "检测器挂绝不能阻断存稿"


def test_north_star_chapter_endpoint(store):
    store.save_chapter(3, "第三章正文。", title="三")
    c = _client(store)
    data = c.get("/north-star/chapter/3").json()
    assert data["seq"] == 3
    assert "constraints" in data and "advisory_scores" in data and "fulfillment" in data
    assert c.get("/north-star/chapter/99").status_code == 404


def test_scorecard_lazy_backfill_when_cache_missing(store):
    """旧库章(有正文无缓存行)→ 端点现算回填,不 404。"""
    store.save_chapter(4, "第四章正文。", title="四")
    store._execute_write("DELETE type::record('chapter_scorecard', 4)", {})
    sc = store.get_chapter_scorecard(4)
    assert sc is not None and sc["constraints"] is not None


def test_scorecard_table_in_live_tables():
    """D-008/蓝图附录 A.2:scorecard 缓存表须入 _LIVE_TABLES 走 /live SSE 推送。"""
    assert "chapter_scorecard" in A._LIVE_TABLES
