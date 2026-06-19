"""C2-5 混合检索 自检:RRF 融合纯函数 + 关键词/图路(用真实段落,向量路给桩)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.retrieval import reciprocal_rank_fusion, keyword_search, hybrid_search  # noqa: E402


def test_rrf():
    # A 在两路都靠前 → 应排第一;C 只在一路
    fused = reciprocal_rank_fusion([["A", "B", "C"], ["A", "C", "D"]])
    ids = [x[0] for x in fused]
    assert ids[0] == "A", ids
    assert set(ids) == {"A", "B", "C", "D"}
    assert reciprocal_rank_fusion([]) == []


def test_keyword_and_hybrid():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    d.upsert_character(w, "沈砚")
    c1 = d.save_chapter(w, 1, "一")
    d.save_segments(w, c1, "沈砚在地下室握紧匕首。\n外面下着雨。", created_by="ai")
    d.add_relation(w, "沈砚", "裴姞", "敌对", valid_from=1)
    d.add_timeline_event(w, 1, "沈砚与裴姞地下室对峙", 1)

    kw = keyword_search(d, w, "地下室 匕首")
    assert any("匕首" in txt for _, txt in kw), kw

    res = hybrid_search(d, w, "沈砚 地下室对峙", k=3, vec_hits=None, upto_seq=1)
    assert res["segments"], res
    assert any("敌对" in g for g in res["graph"]) or any("对峙" in g for g in res["graph"]), res["graph"]
    print("  ✓ test_rrf / test_keyword_and_hybrid")


if __name__ == "__main__":
    test_rrf()
    test_keyword_and_hybrid()
    print("\n通过。")
