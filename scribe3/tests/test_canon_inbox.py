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


def test_batch_decide_group_key_reject():
    from scribe3.api.routers import canon_loop as cl
    rejected = []

    class _St:
        def list_canon_candidates(self, **kw):
            return [
                {"id": "a1", "module": "faction", "target": "高门", "extractor": "heuristic", "confidence": 0.5},
                {"id": "a2", "module": "faction", "target": "高门", "extractor": "heuristic", "confidence": 0.5},
                {"id": "b1", "module": "character", "target": "role:沈拾灯", "extractor": "marker"},
            ]
        def get_canon_candidate(self, uid):
            for r in self.list_canon_candidates():
                if r["id"] == uid:
                    return r
            return None
        def set_canon_candidate_status(self, uid, status):
            rejected.append((uid, status))

    old = cl._store
    cl._store = lambda w: _St()
    try:
        out = cl.batch_decide(cl.BatchDecideReq(
            work="t", decision="reject", group_key="faction|高门",
        ))
        assert out["ok_count"] == 2
        assert {x[0] for x in rejected} == {"a1", "a2"}
    finally:
        cl._store = old


def test_generic_faction_noise():
    assert is_noise_heuristic({
        "module": "faction", "target": "高门", "extractor": "heuristic", "confidence": 0.5,
    })


def test_noise_door_and_while_and_fake_names():
    """历史脏数据：推门/一会/叫我来看 — 即使 conf=1 hybrid 也标噪声。"""
    for target in ("推门", "他看了一会", "拾灯以为他不会", "河水漫过鞋帮", "师父从门"):
        assert is_noise_heuristic({
            "module": "faction", "target": target, "extractor": "hybrid",
            "confidence": 1.0, "op": "add",
        }), target
    for target in ("role:我来看这", "role:写上灯芯", "role:叫人替了命"):
        assert is_noise_heuristic({
            "module": "character", "target": target, "extractor": "hybrid",
            "confidence": 1.0, "op": "add",
        }), target
    # marker 真组织仍放行
    assert not is_noise_heuristic({
        "module": "faction", "target": "高门代还", "extractor": "marker", "confidence": 1.0,
    })


def test_dedupe_key_and_codex_has():
    from scribe3.canon_inbox import codex_already_has, dedupe_key

    a = {"module": "character", "target": "role:沈拾灯", "op": "add"}
    b = {"module": "character", "target": "role:沈拾灯", "op": "add", "after": {"name": "沈拾灯"}}
    assert dedupe_key(a) == dedupe_key(b)

    class _St:
        def characters(self):
            class C:
                name = "沈拾灯"
            return [C()]
        def entity(self, oid):
            return object() if oid == "role:沈拾灯" else None
        def list_items(self):
            return [{"name": "火镰"}]

    st = _St()
    assert codex_already_has(st, {"module": "character", "target": "role:沈拾灯", "op": "add"})
    assert codex_already_has(st, {"module": "item", "target": "火镰", "op": "add"})
    assert not codex_already_has(st, {"module": "item", "target": "纸钱", "op": "add"})
    assert not codex_already_has(st, {"module": "character", "target": "role:沈拾灯", "op": "patch", "field": "fear"})


def test_suggested_hides_bare_heuristic():
    items = [
        {"id": "n", "module": "faction", "target": "推门", "extractor": "hybrid",
         "confidence": 1.0, "op": "add", "source": "prose_finalize"},
        {"id": "g", "module": "character", "target": "role:阿绣", "field": "fear",
         "extractor": "marker", "confidence": 1.0, "op": "patch", "source": "prose_finalize"},
    ]
    sug = filter_items(items, priority="suggested", noise="exclude")
    assert [i["id"] for i in sug] == ["g"]
    fac = facets(items)
    assert fac["noise_count"] >= 1
