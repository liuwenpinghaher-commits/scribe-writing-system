"""产品 QC 合计 SSOT（扩维 keys · REVISION 对齐）。"""
from __future__ import annotations


def test_product_keys_include_extended_and_exclude_rhythm():
    from scribe3.qc_product_keys import PRODUCT_QC_LIST_KEYS
    assert "god_view" in PRODUCT_QC_LIST_KEYS
    assert "degeneration" in PRODUCT_QC_LIST_KEYS
    assert "filler" in PRODUCT_QC_LIST_KEYS
    assert "rule_of_three" in PRODUCT_QC_LIST_KEYS
    assert "rhythm" not in PRODUCT_QC_LIST_KEYS
    assert "adverb" not in PRODUCT_QC_LIST_KEYS


def test_breakdown_from_flags_counts_lists():
    from scribe3.qc_product_keys import product_qc_breakdown_from_flags, product_qc_total
    qf = {
        "repetition": [{"x": 1}, {"y": 2}],
        "structural": [],
        "purple": [{"a": 1}],
        "ai_tics": [],
        "oversaturation": [],
        "god_view": [{"g": 1}],
        "degeneration": [],
        "filler": [{"f": 1}],
        "rule_of_three": [],
        "rhythm": {"uniform": True},
        "adverb": None,
    }
    bd = product_qc_breakdown_from_flags(qf)
    assert bd["repetition"] == 2
    assert bd["god_view"] == 1
    assert bd["filler"] == 1
    assert "rhythm" not in bd
    # rep2 + purple1 + god1 + filler1 = 5
    assert product_qc_total(bd) == 5


def test_project_fills_missing_keys():
    from scribe3.qc_product_keys import project_product_qc_breakdown, PRODUCT_QC_LIST_KEYS
    p = project_product_qc_breakdown({"repetition": 3})
    assert set(p.keys()) == set(PRODUCT_QC_LIST_KEYS)
    assert p["repetition"] == 3
    assert p["god_view"] == 0


def test_quality_cache_revision_is_2():
    from scribe3.store.core_preamble import QUALITY_CACHE_REVISION
    assert QUALITY_CACHE_REVISION >= 2


def test_compute_cache_uses_product_keys(monkeypatch):
    """_compute_chapter_caches breakdown 含扩维键（不写库）。"""
    from scribe3.store.chapters import ChaptersMixin
    from scribe3.qc_product_keys import PRODUCT_QC_LIST_KEYS

    class Fake(ChaptersMixin):
        def events_at(self, seq):
            return []

    # quality_flags 返回假数据
    fake_qf = {k: [{"hit": 1}] if k == "god_view" else [] for k in (
        "repetition", "structural", "purple", "ai_tics", "oversaturation",
        "god_view", "degeneration", "filler", "rule_of_three",
    )}
    fake_qf["rhythm"] = None
    fake_qf["adverb"] = None
    monkeypatch.setattr("scribe3.critique.quality_flags", lambda prose: fake_qf)
    st = Fake()
    # need _split_scenes
    monkeypatch.setattr(
        "scribe3.store.chapters._split_scenes",
        lambda prose: [{"title": "s", "chars": 10}],
    )
    cache = st._compute_chapter_caches(1, "正文" * 20)
    import json
    bd = json.loads(cache["qc_breakdown"])
    for k in PRODUCT_QC_LIST_KEYS:
        assert k in bd
    assert bd["god_view"] == 1
    assert cache["qc_issues"] == 1
