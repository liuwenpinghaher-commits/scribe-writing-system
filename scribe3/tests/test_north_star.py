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


# ===== 北极星任务7 · 书级 scorecard 四维 =====

def test_book_scorecard_four_dims_no_total(store):
    """四维面板:张弛/回收率/矛盾密度(仅自比)/达成率;绝不合成总分(宪法)。"""
    import json as _j
    store.save_chapter(1, "第一章正文,字数若干,人事各安。", title="一")
    store.save_chapter(2, "第二章正文,风声渐紧,旧账翻页。", title="二")
    store.plant_promise("要收的", setup_chapter=1, tier="chapter")
    pid = next(p["id"] for p in store.list_promises() if p["text"] == "要收的")
    store.advance_promise(pid, payoff_chapter=2)
    store.plant_promise("还开着的", setup_chapter=2, tier="chapter")
    store.update_chapter_meta(1, {"deltas": [
        {"kind": "fact", "subject": "a", "predicate": "p1", "status": "achieved"},
        {"kind": "fact", "subject": "b", "predicate": "p2", "status": "carried",
         "carried_from": 1}]})
    data = _client(store).get("/north-star/book").json()
    assert set(data) >= {"tension", "promise_recovery", "contradiction_density",
                         "fulfillment"}
    pr = data["promise_recovery"]
    assert pr["payoff"] == 1 and pr["open"] == 1 and abs(pr["rate"] - 0.5) < 1e-6
    cd = data["contradiction_density"]
    assert cd["self_compare_only"] is True, "矛盾密度只可自比趋势(蓝图 v2 口径警示)"
    fu = data["fulfillment"]
    assert fu["achieved"] == 1 and fu["total"] == 2 and fu["carried_backlog"] == 1
    flat = _j.dumps(data, ensure_ascii=False)
    assert "total_score" not in flat and "overall" not in flat, "绝不合成总分(宪法)"


def test_book_fulfillment_dedups_by_chain_tail(store):
    """P1门审查 P1-4:书级达成率按 (kind,predicate) 链尾去重——还清的债不再挂账,
    分母不随滚动膨胀(此前一条最终达成的 delta 被计成 50%)。"""
    store.save_chapter(5, "五。", title="五")
    store.save_chapter(6, "六。", title="六")
    store.update_chapter_meta(5, {"deltas": [
        {"kind": "promise", "subject": "债", "predicate": "同一条债",
         "status": "carried", "carried_from": 5}]})
    store.update_chapter_meta(6, {"deltas": [
        {"kind": "promise", "subject": "债", "predicate": "同一条债",
         "status": "achieved", "carried_from": 5}]})
    fu = _client(store).get("/north-star/book").json()["fulfillment"]
    assert fu["total"] == 1 and fu["achieved"] == 1 and fu["carried_backlog"] == 0
    assert abs(fu["rate"] - 1.0) < 1e-6


def test_book_scorecard_empty_book_no_fake_green(store):
    """空书:各维 no_data 如实标注,不出 0 假绿。"""
    data = _client(store).get("/north-star/book").json()
    assert data["promise_recovery"]["no_data"] is True
    assert data["fulfillment"]["no_data"] is True
    assert data["contradiction_density"]["no_data"] is True


def test_scorecard_table_in_live_tables():
    """D-008/蓝图附录 A.2:scorecard 缓存表须入 _LIVE_TABLES 走 /live SSE 推送。"""
    assert "chapter_scorecard" in A._LIVE_TABLES
