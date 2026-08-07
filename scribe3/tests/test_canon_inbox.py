"""收件箱：噪声判定、详情标题、API 形状。"""
from __future__ import annotations

from scribe3.canon_inbox import (
    annotate_flags,
    facets,
    filter_items,
    human_title,
    is_noise_heuristic,
)


def test_noise_heuristic_faction_fragments():
    assert is_noise_heuristic({
        "module": "faction", "target": "是会", "extractor": "heuristic", "confidence": 0.4,
    })
    assert is_noise_heuristic({
        "module": "faction", "target": "原本是替高门", "extractor": "hybrid", "confidence": 0.5,
    })
    assert not is_noise_heuristic({
        "module": "faction", "target": "高门代还", "extractor": "marker", "confidence": 1.0,
    })
    assert not is_noise_heuristic({
        "module": "character", "target": "role:沈拾灯", "field": "fear",
        "extractor": "marker", "confidence": 1.0,
    })


def test_human_title_and_filter_priority():
    t = human_title({
        "module": "character", "op": "patch", "target": "role:沈拾灯", "field": "fear",
    })
    assert "角色" in t and "恐惧" in t
    items = [
        {"id": "1", "module": "faction", "target": "是会", "extractor": "heuristic",
         "confidence": 0.4, "op": "add", "source": "prose_finalize"},
        {"id": "2", "module": "character", "target": "role:阿绣", "field": "fear",
         "extractor": "marker", "confidence": 1.0, "op": "patch", "source": "prose_finalize",
         "after": "恨"},
    ]
    fac = facets(items)
    assert fac["noise_count"] >= 1
    sug = filter_items(items, priority="suggested", noise="exclude")
    assert any(i["id"] == "2" for i in sug)
    only_n = filter_items(items, noise="only")
    assert all(annotate_flags(i).get("is_noise") for i in only_n)


def test_batch_decide_empty_ids():
    from scribe3.api.routers import canon_loop as cl
    class _St:
        def list_canon_candidates(self, **kw):
            return []
        def get_canon_candidate(self, uid):
            return None
    # monkeypatch store
    old = cl._store
    cl._store = lambda w: _St()
    try:
        out = cl.batch_decide(cl.BatchDecideReq(work="t", ids=[], decision="reject"))
        assert out.get("processed") == 0
    finally:
        cl._store = old
