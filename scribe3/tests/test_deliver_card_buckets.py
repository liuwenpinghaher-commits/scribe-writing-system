"""PR-6c · deliver pilot_card.buckets 三项计数（无 Surreal / 无 LLM）。"""
from __future__ import annotations

from scribe3.loop import (
    bucket_counts_from_triage,
    normalize_bucket_counts,
    triage,
)


def test_normalize_bucket_counts_from_lists():
    got = normalize_bucket_counts({
        "redline": [{"kind": "leak"}],
        "story": [{"kind": "park_stroll"}, {"kind": "spatial_inventory"}],
        "style": [],
    })
    assert got == {"redline": 1, "story": 2, "style": 0}


def test_normalize_bucket_counts_from_ints_and_missing():
    assert normalize_bucket_counts({"redline": 3, "story": 0}) == {
        "redline": 3, "story": 0, "style": 0,
    }
    assert normalize_bucket_counts(None) == {"redline": 0, "story": 0, "style": 0}
    assert normalize_bucket_counts({}) == {"redline": 0, "story": 0, "style": 0}
    assert normalize_bucket_counts({"redline": True, "story": -1})["redline"] == 0
    assert normalize_bucket_counts({"story": {"count": 4}})["story"] == 4


def test_bucket_counts_from_triage_none_without_buckets_key():
    assert bucket_counts_from_triage(None) is None
    assert bucket_counts_from_triage({"verdict": "pass"}) is None
    assert bucket_counts_from_triage({"buckets": {"story": [1]}}) == {
        "redline": 0, "story": 1, "style": 0,
    }


def test_triage_pass_always_yields_zero_counts():
    t = triage({"leaks": [], "issues": [], "ai_grade": {}, "degraded_stages": []})
    counts = bucket_counts_from_triage(t)
    assert counts == {"redline": 0, "story": 0, "style": 0}


def test_triage_leak_and_park_stroll_split_counts():
    post = {
        "leaks": [{"marker": "私密破绽", "fact_id": "f1"}],
        "issues": [{
            "type": "pressure",
            "message": "公园散步",
            "text": "",
            "meta": {"kind": "park_stroll", "severity": "blocking"},
        }, {
            "type": "punct",
            "message": "标点建议",
            "text": "，，",
            "meta": {},
        }],
        "ai_grade": {},
        "degraded_stages": [],
        "punct_suggestions": [{"message": "多逗号", "text": "，，"}],
    }
    t = triage(post)
    assert "buckets" in t
    counts = bucket_counts_from_triage(t)
    assert counts is not None
    assert counts["redline"] >= 1
    assert counts["story"] >= 1
    # style: advisory punct (+ maybe punct_suggestions)
    assert counts["style"] >= 1
    assert counts["redline"] + counts["story"] + counts["style"] >= 3


def test_deliver_card_shape_contract():
    """artifact.card.buckets 契约：三键 int，可直接进 pilot_card JSON。"""
    t = triage({
        "leaks": [{"marker": "x", "fact_id": "f"}],
        "issues": [],
        "ai_grade": {"grade": "heavy", "gates_hit": ["A"], "indicators": {}},
        "degraded_stages": [],
        "visible_chars": 2000,
    })
    card = {
        "seq": 1,
        "words": 100,
        "qc": 0,
        "promises": [],
        "low_confidence": "无",
        "buckets": bucket_counts_from_triage(t),
    }
    assert set(card["buckets"].keys()) == {"redline", "story", "style"}
    assert all(isinstance(card["buckets"][k], int) for k in card["buckets"])
    assert card["buckets"]["redline"] >= 1  # leak
    assert card["buckets"]["style"] >= 1    # ai_grade heavy → style
