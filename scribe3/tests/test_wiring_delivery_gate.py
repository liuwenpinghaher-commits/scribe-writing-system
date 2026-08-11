"""交付门 A1/A2/A5：驱动 shipped 入口，无重实现。"""
from __future__ import annotations

from types import SimpleNamespace


def test_a1_product_qc_keys_shared():
    from scribe3.qc_product_keys import (
        PRODUCT_QC_LIST_KEYS,
        product_qc_breakdown_from_flags,
        product_qc_total,
        project_product_qc_breakdown,
    )
    from scribe3.store.core_preamble import QUALITY_CACHE_REVISION

    assert QUALITY_CACHE_REVISION >= 2
    for k in ("god_view", "degeneration", "filler", "rule_of_three"):
        assert k in PRODUCT_QC_LIST_KEYS
    qf = {k: [{"h": 1}] if k in ("god_view", "repetition") else [] for k in PRODUCT_QC_LIST_KEYS}
    bd = product_qc_breakdown_from_flags(qf)
    assert product_qc_total(bd) == 2
    assert project_product_qc_breakdown({"repetition": 1})["god_view"] == 0


def test_a2_enrich_leak_payload_knowers():
    from scribe3.verify import Leak, enrich_leak_payload, proposition_local_id

    assert proposition_local_id("fact:治眼") == "治眼"
    assert proposition_local_id("proposition:x") == "x"

    class Store:
        def list_knowers_for_proposition(self, prop_local, chapter):
            assert prop_local == "治眼"
            assert chapter == 3
            return [
                {"id": "role:甲", "name": "甲", "since_chapter": 1, "value": "SECRET_SHOULD_NOT_PASS"},
            ]

    lk = Leak(fact_id="fact:治眼", marker="治眼术", subject="role:乙", range=(0, 3))
    row = enrich_leak_payload(lk, Store(), 3)
    assert row["knowers_status"] == "ok"
    assert row["knowers_count"] == 1
    assert row["knowers"][0]["id"] == "role:甲"
    assert "value" not in row["knowers"][0]
    assert row["proposition_local"] == "治眼"

    # unavailable store
    row2 = enrich_leak_payload(lk, object(), 1)
    assert row2["knowers_status"] == "unavailable"
    assert row2["knowers"] == []


def test_a2_collect_leak_issues_includes_knowers_meta():
    from scribe3.review.ledger import collect_leak_issues
    from scribe3.verify import Leak

    class Store:
        def list_knowers_for_proposition(self, prop_local, chapter):
            return [{"id": "role:甲", "name": "甲"}]

    def fake_find(prose, store, focalizer, chapter):
        return [Leak("fact:秘", "秘钥", "role:乙", range=(1, 2))]

    import scribe3.review.ledger as led
    orig = led.find_leaks_for_chapter if hasattr(led, "find_leaks_for_chapter") else None
    # patch via verify import path used inside collect_leak_issues
    import scribe3.verify as v
    old = v.find_leaks_for_chapter
    v.find_leaks_for_chapter = fake_find
    try:
        issues, deg = collect_leak_issues("正文含秘钥", Store(), 2, "role:甲")
        assert not deg
        assert issues
        assert issues[0]["meta"]["knowers_count"] == 1
        assert issues[0]["meta"]["knowers"][0]["name"] == "甲"
    finally:
        v.find_leaks_for_chapter = old


def test_a5_faction_work_scope_never_chapter_zero():
    from scribe3.review.ledger import collect_faction_issues, build_work_scope_faction_ledger

    class Store:
        pass

    import scribe3.codex_validate as cv
    old = cv.validate_faction_consistency
    cv.validate_faction_consistency = lambda store: [
        {"kind": "mutual_enemy_missing", "severity": "high", "faction": "faction:甲", "detail": "甲敌乙但乙不敌甲"},
    ]
    try:
        items = collect_faction_issues(Store())
        assert items
        assert items[0]["chapter"] is None
        assert items[0]["meta"]["scope"] == "work"
        assert items[0]["type"] == "faction_consistency"
        pack = build_work_scope_faction_ledger(Store())
        assert all(i.get("chapter") != 0 for i in pack["issues"])
    finally:
        cv.validate_faction_consistency = old


def test_a1_structure_outline_projects_extended_keys():
    """project_product_qc_breakdown used by outline — no five-key clip."""
    from scribe3.qc_product_keys import project_product_qc_breakdown, PRODUCT_QC_LIST_KEYS
    raw = {"repetition": 2, "god_view": 1, "extra_noise": 9}
    out = project_product_qc_breakdown(raw)
    assert set(out) == set(PRODUCT_QC_LIST_KEYS)
    assert out["god_view"] == 1
    assert "extra_noise" not in out


def test_a1_check_prose_source_uses_product_breakdown():
    """Fail if /check still hand-builds five-key qc without SSOT."""
    import inspect
    from scribe3.api.routers import write as write_mod
    src = inspect.getsource(write_mod.check_prose)
    assert "product_qc_breakdown_from_flags" in src
    assert "product_qc_total" in src
    # five-key-only literal construction must not be the response shape
    assert 'qc": {"repetition": len(qf["repetition"])' not in src


def test_a1_check_prose_qc_shape_includes_extended_keys():
    """Simulate check_prose qc assembly with shipped helpers (god_view-only hits)."""
    from scribe3.qc_product_keys import (
        PRODUCT_QC_LIST_KEYS,
        product_qc_breakdown_from_flags,
        product_qc_total,
    )
    qf = {k: [] for k in list(PRODUCT_QC_LIST_KEYS) + ["rhythm", "adverb"]}
    qf["god_view"] = [{"kind": "god_spoiler", "phrase": "其实他知道"}]
    qf["degeneration"] = [{"kind": "loop"}]
    qc = product_qc_breakdown_from_flags(qf)
    qc["total"] = product_qc_total(qc)
    for k in PRODUCT_QC_LIST_KEYS:
        assert k in qc
    assert qc["god_view"] == 1
    assert qc["degeneration"] == 1
    assert qc["total"] == 2
    # five-key-only would report total 0 — this must not happen
    five = sum(qc[k] for k in ("repetition", "structural", "purple", "ai_tics", "oversaturation"))
    assert five == 0
    assert qc["total"] > five


def test_a2_check_and_post_check_leak_issue_meta_knowers_in_source():
    """issue.meta must copy knowers from enrich_leak_payload in check + post_check."""
    import inspect
    from scribe3.api.routers import write as write_mod
    check_src = inspect.getsource(write_mod.check_prose)
    post_src = inspect.getsource(write_mod.post_check)
    for src, name in ((check_src, "check_prose"), (post_src, "post_check")):
        assert "knowers" in src and "knowers_status" in src, name
        assert "enrich_leak_payload" in src, name