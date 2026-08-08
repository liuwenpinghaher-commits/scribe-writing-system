"""D7：usage_digest 纯逻辑。"""
from __future__ import annotations

from scribe3.memory_gain import build_usage_digest_from_manifest, comparison_protocol


def test_usage_digest_summary():
    m = {
        "envelope_hash": "abc",
        "blocks": [
            {
                "name": "global",
                "token_estimate": 100,
                "source_ids": ["intent:main", "intent:author_constraints"],
                "masked_source_ids": [],
            },
            {
                "name": "canonical",
                "token_estimate": 200,
                "source_ids": ["must_link:header", "fact:x"],
                "masked_source_ids": ["fact:secret"],
            },
        ],
        "omitted": [{"source_id": "e1", "reason": "token_budget"}],
    }
    d = build_usage_digest_from_manifest(m)
    assert d["total_sources"] == 4
    assert "记忆" in d["summary"] or "来源" in d["summary"]
    assert d["omitted_count"] == 1
    assert any("铁律" in x or "意图" in x for x in d["lines"] + [
        y for b in d["by_block"] for y in (b.get("source_labels") or [])
    ])


def test_comparison_protocol_has_pass_rule():
    p = comparison_protocol()
    assert p["pass_rule"]
    assert len(p["scores"]) >= 3


def test_empty_manifest():
    d = build_usage_digest_from_manifest({})
    assert d["total_sources"] == 0
