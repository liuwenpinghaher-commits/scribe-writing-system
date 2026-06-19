"""C6-2 质量度量 自检:回收率(time-aware)、一致性加权、章/全书报告。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.foreshadow import ForeshadowStore  # noqa: E402
from scribe_mcp import metrics  # noqa: E402


def test_payoff_and_consistency():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    fs = ForeshadowStore(d.conn)
    f1 = fs.plant(w, "信物", 1); fs.transition(f1, "triggered"); fs.transition(f1, "paid")
    fs.plant(w, "悬念", 2)             # planted
    f3 = fs.plant(w, "弃坑", 3); fs.transition(f3, "abandoned")
    r = metrics.foreshadow_payoff_rate(w and d and w, None) if False else metrics.foreshadow_payoff_rate(d, w)
    assert r["planted"] == 3 and r["paid"] == 1 and r["abandoned"] == 1
    assert r["payoff_rate"] == round(1 / 2, 3)  # 1 paid / (3-1)
    # time-aware:截至第1章只有 f1
    assert metrics.foreshadow_payoff_rate(d, w, upto_seq=1)["planted"] == 1

    d.raise_consistency_flag(w, "时序矛盾", 5, "critical", "x", {})
    d.raise_consistency_flag(w, "命名不一致", 5, "minor", "y", {})
    cs = metrics.consistency_score(d, w)
    assert cs["open_flags"] == 2 and cs["weighted"] == 3.0 + 1.0
    assert 0 < cs["score"] < 1


def test_reports():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    cid = d.save_chapter(w, 1, "一")
    d.save_snapshot(w, cid, "他嘴角勾起一抹弧度。总而言之这一刻他明白了。" * 3, created_by="ai")
    cq = metrics.chapter_quality(d, w, 1)
    assert cq["words"] > 0 and cq["slop_density"] > 0
    rep = metrics.work_quality_report(d, w)
    assert rep["chapters"] == 1 and rep["words"] > 0
    assert "payoff_rate" in rep["foreshadow"] and "score" in rep["consistency"]
    print("  ✓ test_payoff_and_consistency / test_reports")


if __name__ == "__main__":
    test_payoff_and_consistency()
    test_reports()
    print("\n通过。")
