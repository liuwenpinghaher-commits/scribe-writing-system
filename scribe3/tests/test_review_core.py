"""M0–M3 pure unit tests for review package (no Surreal)."""
from __future__ import annotations

from types import SimpleNamespace

from scribe3.review.blocking import is_blocking_issue
from scribe3.review.fp import assert_parity_with_chapter_analysis, prose_fp
from scribe3.review.l1_epistemic import build_l1_payload, run_l1
from scribe3.review.normalize import map_legacy_severity, normalize_issue, normalize_issues
from scribe3.review.schema import CANONICAL_SEVERITIES


def test_map_legacy_severity():
    assert map_legacy_severity("error") == "S2"
    assert map_legacy_severity("warning") == "S3"
    assert map_legacy_severity("blocking") == "S1"
    assert map_legacy_severity("S1") == "S1"
    assert map_legacy_severity("info") == "info"


def test_normalize_degeneration_to_s1():
    iss = normalize_issue({
        "type": "degeneration",
        "message": "meta",
        "meta": {"severity": "blocking", "kind": "placeholder"},
    }, chapter=3)
    assert iss["severity"] == "S1"
    assert iss["status"] == "open"


def test_is_blocking_issue_whitelist():
    # setting + S1 must NOT block
    assert not is_blocking_issue({
        "type": "setting",
        "meta": {"severity": "S1"},
    })
    # discipline + S1 must block
    assert is_blocking_issue({
        "type": "discipline",
        "meta": {"severity": "S1"},
    })
    # degeneration blocking
    assert is_blocking_issue({
        "type": "degeneration",
        "meta": {"severity": "blocking"},
    })
    # llm_review S1
    assert is_blocking_issue({
        "type": "llm_review",
        "meta": {"severity": "S1"},
    })
    # S2 discipline not blocking via S1 rule
    assert not is_blocking_issue({
        "type": "discipline",
        "meta": {"severity": "S2"},
    })


def test_loop_triage_uses_shared_blocking():
    from scribe3.loop import triage
    post = {
        "leaks": [],
        "issues": [
            {"type": "setting", "message": "x", "meta": {"severity": "S1"}},
            {"type": "discipline", "message": "y", "text": "t",
             "meta": {"severity": "S1"}},
        ],
        "degraded_stages": [],
    }
    t = triage(post)
    assert t["verdict"] == "blocking"
    kinds = [b.get("kind") for b in t["blocking"]]
    assert "discipline" in kinds or "S1" in kinds or any(
        "discipline" in str(b) for b in t["blocking"]
    )
    # setting alone would not block — with discipline present we block
    post2 = {
        "leaks": [],
        "issues": [{"type": "setting", "message": "x", "meta": {"severity": "S1"}}],
        "degraded_stages": [],
    }
    t2 = triage(post2)
    assert t2["verdict"] != "blocking" or not any(
        b.get("kind") == "setting" for b in t2["blocking"]
    )


def test_triage_normalized_degeneration_s1_blocks():
    """After normalize (blocking→S1), degeneration must still block — not false-green."""
    from scribe3.loop import triage
    from scribe3.review.normalize import normalize_issue

    raw = {
        "type": "degeneration",
        "message": "placeholder",
        "text": "TODO",
        "meta": {"severity": "blocking", "kind": "placeholder"},
    }
    # Ship path: ledger/review normalizes then triage consumes
    norm = normalize_issue(raw, chapter=1)
    assert norm["severity"] == "S1"
    assert is_blocking_issue(norm) is True
    post = {
        "leaks": [],
        "issues": [norm],  # severity S1 on issue + meta (normalize puts on both)
        "degraded_stages": [],
    }
    # triage reads meta.severity primarily; ensure meta carries S1
    assert (post["issues"][0].get("meta") or {}).get("severity") == "S1"
    t = triage(post)
    assert t["verdict"] == "blocking", t
    assert len(t["blocking"]) >= 1
    assert any(
        b.get("detector") == "find_degeneration" or b.get("kind") in ("placeholder", "degeneration")
        for b in t["blocking"]
    )


def test_triage_normalized_pressure_s1_blocks():
    from scribe3.loop import triage
    from scribe3.review.normalize import normalize_issue

    raw = {
        "type": "pressure",
        "message": "pressure high",
        "text": "x",
        "meta": {"severity": "blocking", "kind": "progress_zero_advance"},
    }
    norm = normalize_issue(raw, chapter=2)
    assert norm["severity"] == "S1"
    t = triage({"leaks": [], "issues": [norm], "degraded_stages": []})
    assert t["verdict"] == "blocking", t
    assert any(b.get("detector") == "pressure_metrics" for b in t["blocking"])


def test_prose_fp_parity():
    assert_parity_with_chapter_analysis()
    assert len(prose_fp("hello")) == 16


def test_build_l1_payload_forbids_value():
    payload = build_l1_payload(
        "正文里有秘密",
        focalizer="role:甲",
        secrets=[{
            "id": "fact:1",
            "attribute": "身世",
            "entity": "role:乙",
            "value": "真身是妖",  # must be stripped
            "leak_markers": ["妖"],
        }],
        known_summaries=["甲·位置=客栈"],
    )
    import json
    blob = json.dumps(payload, ensure_ascii=False)
    assert '"value"' not in blob
    assert "真身是妖" not in blob
    assert payload["secret_slots"][0]["attribute"] == "身世"


def test_run_l1_with_mock_complete():
    store = SimpleNamespace(
        facts_at=lambda ch: [
            SimpleNamespace(
                id="fact:s1", entity_id="role:乙", attribute="身世",
                value="真身是妖", secret=True, leak_markers=["妖"],
            ),
        ],
    )
    # frame: knows nothing about secret

    class _Frame:
        def knows(self, fid):
            return False

    import scribe3.review.l1_epistemic as l1mod
    orig = l1mod.secrets_from_store

    def fake_secrets(store, chapter, focalizer):
        return (
            [{"id": "fact:s1", "attribute": "身世", "entity": "role:乙", "has_markers": True}],
            [],
            {"妖"},
        )

    l1mod.secrets_from_store = fake_secrets
    try:
        def complete_fn(prompt, system=None):
            return '{"findings":[{"issue":"正文泄露乙身世","evidence":"妖气","severity":"S2"}]}'

        out = run_l1(
            "他知道那是妖气缭绕",
            store=store,
            chapter=1,
            focalizer="role:甲",
            complete_fn=complete_fn,
            marker_leaks_present=True,
        )
        assert out["reviewers_run"] == ["llm_review_l1"]
        assert len(out["issues"]) >= 1
        assert out["issues"][0]["type"] == "llm_review"
        # resonance with markers → S1
        assert out["issues"][0]["severity"] == "S1"
    finally:
        l1mod.secrets_from_store = orig


def test_normalize_issues_sort():
    items = normalize_issues([
        {"type": "a", "severity": "S3", "message": "c"},
        {"type": "b", "severity": "S1", "message": "a", "meta": {"severity": "S1"}},
        {"type": "c", "severity": "S2", "message": "b", "meta": {"severity": "S2"}},
    ], chapter=1)
    assert items[0]["severity"] == "S1"
    assert all(s in CANONICAL_SEVERITIES for s in (i["severity"] for i in items))


def test_collect_qc_includes_god_view_key():
    from scribe3.review.ledger import collect_qc_issues
    q = {
        "god_view": [{"kind": "god_spoiler", "text": "他此刻知道了全村秘密"}],
        "degeneration": [{"kind": "placeholder", "text": "TODO"}],
        "repetition": [],
    }
    issues = collect_qc_issues(q, 5)
    kinds = {i["kind"] for i in issues}
    assert "god_view" in kinds
    assert "degeneration" in kinds
