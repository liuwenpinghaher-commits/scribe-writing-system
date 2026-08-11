"""A3: quality_dim advisory projection (1–5) + load_chapter_dim_scores + runner wiring."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from scribe3.review.m5_projection import project_quality_dim_advisory
from scribe3.review.blocking import is_blocking_issue


def test_project_quality_dim_empty():
    assert project_quality_dim_advisory(None, chapter=1) == []
    assert project_quality_dim_advisory({}, chapter=1) == []


def test_project_quality_dim_1_5_thresholds():
    scores = {
        "coherence_causality": 1,
        "character_truth": 2,
        "scene_necessity": 3,
        "structure_pacing": 4,
        "suspense_payoff": 5,
    }
    issues = project_quality_dim_advisory(scores, chapter=7)
    kinds = {i["kind"]: i for i in issues}
    assert set(kinds) == {"coherence_causality", "character_truth", "scene_necessity"}
    assert kinds["coherence_causality"]["severity"] == "S3"
    assert kinds["character_truth"]["severity"] == "S3"
    assert kinds["scene_necessity"]["severity"] == "S4"
    for i in issues:
        assert i["source"] == "quality_dim"
        assert i["type"] == "quality_dim"
        assert (i.get("meta") or {}).get("track") == "L"
        assert (i.get("meta") or {}).get("scale") == "1-5"
        assert not is_blocking_issue(i)


def test_project_quality_dim_skips_invalid():
    issues = project_quality_dim_advisory({"a": "x", "b": 2.0}, chapter=1)
    assert len(issues) == 1
    assert issues[0]["kind"] == "b"


def test_quality_dim_never_blocking_even_if_s1_meta_forged():
    # projection never emits S1; forged still not in S1_BLOCKING_TYPES
    assert not is_blocking_issue({
        "type": "quality_dim",
        "meta": {"severity": "S1"},
    })


def test_load_chapter_dim_scores_no_job(monkeypatch):
    from scribe3.quality import dim_scores as ds

    monkeypatch.delenv("SCRIBE3_QUALITY_DIM_ADVISORY", raising=False)
    monkeypatch.setattr(
        "scribe3.quality.api._latest_job_id_for_seq",
        lambda store, seq: None,
    )
    assert ds.load_chapter_dim_scores(object(), "main", 1) is None


def test_load_chapter_dim_scores_flag_off(monkeypatch):
    from scribe3.quality import dim_scores as ds

    monkeypatch.setenv("SCRIBE3_QUALITY_DIM_ADVISORY", "0")
    assert ds.load_chapter_dim_scores(object(), "main", 1) is None
    assert ds.quality_dim_advisory_enabled() is False


def test_load_chapter_dim_scores_system_only(monkeypatch):
    from scribe3.quality import dim_scores as ds
    from scribe3.quality.models import JudgmentState

    monkeypatch.delenv("SCRIBE3_QUALITY_DIM_ADVISORY", raising=False)
    monkeypatch.setattr(
        "scribe3.quality.api._latest_job_id_for_seq",
        lambda store, seq: "job:abc",
    )

    def _j(dim, kind, score, state=JudgmentState.EVALUABLE):
        return SimpleNamespace(
            judgment=SimpleNamespace(
                dimension=dim,
                evaluator_kind=kind,
                state=state,
                score=score,
            ),
        )

    eval_obj = SimpleNamespace(
        system_reference_judgments=(
            _j("coherence_causality", "system", 2),
            _j("coherence_causality", "reference", 1),  # ignored
            _j("character_truth", "system", 5),
            _j("scene_necessity", "system", None, JudgmentState.INSUFFICIENT),
            _j("structure_pacing", "system", 3),
            # multi-unit weaker wins
            _j("coherence_causality", "system", 1),
        ),
    )

    fake_quality = MagicMock()
    fake_quality.get_job_status.return_value = SimpleNamespace(status="completed")
    fake_quality.get_evaluation.return_value = eval_obj

    monkeypatch.setattr(
        "scribe3.quality.store.QualityStore",
        lambda store: fake_quality,
    )
    out = ds.load_chapter_dim_scores(object(), "main", 3)
    assert out is not None
    assert out["coherence_causality"] == 1.0  # min of 2 and 1
    assert out["character_truth"] == 5.0
    assert out["structure_pacing"] == 3.0
    assert "scene_necessity" not in out


def test_load_chapter_dim_scores_not_completed(monkeypatch):
    from scribe3.quality import dim_scores as ds

    monkeypatch.delenv("SCRIBE3_QUALITY_DIM_ADVISORY", raising=False)
    monkeypatch.setattr(
        "scribe3.quality.api._latest_job_id_for_seq",
        lambda store, seq: "job:x",
    )
    fake_quality = MagicMock()
    fake_quality.get_job_status.return_value = SimpleNamespace(status="running")
    monkeypatch.setattr(
        "scribe3.quality.store.QualityStore",
        lambda store: fake_quality,
    )
    assert ds.load_chapter_dim_scores(object(), "main", 1) is None


def test_run_chapter_review_full_includes_quality_dim(monkeypatch):
    from scribe3.review import runner as runner_mod

    monkeypatch.delenv("SCRIBE3_QUALITY_DIM_ADVISORY", raising=False)
    monkeypatch.setenv("SCRIBE3_REVIEW_LLM", "0")

    store = MagicMock()
    store.get_chapter.return_value = {
        "prose": "他推开门。雨很大。" * 20,
        "focalizer": None,
    }

    monkeypatch.setattr(
        runner_mod,
        "_deterministic_post",
        lambda *a, **k: {
            "issues": [],
            "leaks": [],
            "quality": {"total": 0},
            "ai_grade": None,
            "degraded_stages": [],
            "leaks_degraded": False,
        },
    )
    monkeypatch.setattr(
        "scribe3.quality.dim_scores.load_chapter_dim_scores",
        lambda store, work, seq: {
            "coherence_causality": 2,
            "character_truth": 5,
        },
    )
    # Force deterministic path (no real post_check import path)
    import scribe3.api.models as api_models
    monkeypatch.setattr(api_models, "PostCheckReq", None, raising=False)

    out = runner_mod.run_chapter_review(
        store=store, work="main", seq=1, mode="full",
    )
    qd = [i for i in out["issues"] if i.get("source") == "quality_dim"]
    assert len(qd) == 1
    assert qd[0]["kind"] == "coherence_causality"
    assert "quality_dim" in out["coverage"]["reviewers_run"]
    assert "L" in out["coverage"]["tracks"]


def test_run_chapter_review_deterministic_skips_quality_dim(monkeypatch):
    from scribe3.review import runner as runner_mod

    monkeypatch.delenv("SCRIBE3_QUALITY_DIM_ADVISORY", raising=False)
    store = MagicMock()
    store.get_chapter.return_value = {"prose": "正文。", "focalizer": None}
    monkeypatch.setattr(
        runner_mod,
        "_deterministic_post",
        lambda *a, **k: {
            "issues": [],
            "leaks": [],
            "quality": {"total": 0},
            "ai_grade": None,
            "degraded_stages": [],
            "leaks_degraded": False,
        },
    )
    called = {"n": 0}

    def boom(*a, **k):
        called["n"] += 1
        raise AssertionError("should not load dim scores in deterministic mode")

    monkeypatch.setattr("scribe3.quality.dim_scores.load_chapter_dim_scores", boom)
    import scribe3.api.models as api_models
    monkeypatch.setattr(api_models, "PostCheckReq", None, raising=False)

    out = runner_mod.run_chapter_review(
        store=store, work="main", seq=1, mode="deterministic",
    )
    assert called["n"] == 0
    assert not any(i.get("source") == "quality_dim" for i in out["issues"])
    assert "quality_dim" in out["coverage"]["reviewers_skipped"]


def test_run_chapter_review_flag_off_skips(monkeypatch):
    from scribe3.review import runner as runner_mod

    monkeypatch.setenv("SCRIBE3_QUALITY_DIM_ADVISORY", "0")
    monkeypatch.setenv("SCRIBE3_REVIEW_LLM", "0")
    store = MagicMock()
    store.get_chapter.return_value = {"prose": "正文。", "focalizer": None}
    monkeypatch.setattr(
        runner_mod,
        "_deterministic_post",
        lambda *a, **k: {
            "issues": [],
            "leaks": [],
            "quality": {"total": 0},
            "ai_grade": None,
            "degraded_stages": [],
            "leaks_degraded": False,
        },
    )
    import scribe3.api.models as api_models
    monkeypatch.setattr(api_models, "PostCheckReq", None, raising=False)

    out = runner_mod.run_chapter_review(
        store=store, work="main", seq=1, mode="full",
    )
    assert "quality_dim" in out["coverage"]["reviewers_skipped"]
    assert not any(i.get("source") == "quality_dim" for i in out["issues"])
