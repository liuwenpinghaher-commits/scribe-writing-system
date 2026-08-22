"""Read completed ten-dim system scores for soft quality_dim advisory (no LLM).

A3 adapter: reuses ``quality.api._latest_job_id_for_seq`` + QualityStore evaluation.
Never invents scores; fail-soft → None.
"""
from __future__ import annotations

import logging
from typing import Any

from scribe3.feature_flags import get_flag

_log = logging.getLogger("scribe3.quality.dim_scores")


def quality_dim_advisory_enabled() -> bool:
    """Default ON. Set SCRIBE3_QUALITY_DIM_ADVISORY=0/false/off to disable."""
    v = get_flag("SCRIBE3_QUALITY_DIM_ADVISORY").strip().lower()
    return v not in ("0", "false", "no", "off")


def load_chapter_dim_scores(
    store: Any,
    work: str,
    seq: int,
) -> dict[str, float] | None:
    """Return ``{dimension_key: score_1_to_5}`` or None if unavailable.

    - Only ``evaluator_kind=system`` + ``state=evaluable`` + non-null score.
    - Multi-unit: keep the weakest (min) score per dimension.
    - Flag off / no job / not completed / empty → None.
    - Any exception → None (never raises to caller).
    """
    if not quality_dim_advisory_enabled():
        return None
    try:
        from scribe3.quality.api import _latest_job_id_for_seq
        from scribe3.quality.models import JudgmentState
        from scribe3.quality.store import QualityStore
    except Exception as e:
        _log.warning("load_chapter_dim_scores import failed: %s", e)
        return None
    try:
        job_id = _latest_job_id_for_seq(store, int(seq))
        if not job_id:
            return None
        quality = QualityStore(store)
        status = quality.get_job_status(job_id)
        if getattr(status, "status", None) != "completed":
            return None
        evaluation = quality.get_evaluation(job_id)
        scores: dict[str, float] = {}
        for bound in evaluation.system_reference_judgments or ():
            j = getattr(bound, "judgment", bound)
            if getattr(j, "evaluator_kind", None) != "system":
                continue
            state = getattr(j, "state", None)
            state_v = state.value if hasattr(state, "value") else state
            if state is not JudgmentState.EVALUABLE and state_v != "evaluable":
                continue
            score = getattr(j, "score", None)
            if score is None:
                continue
            dim = getattr(j, "dimension", None)
            if not dim:
                continue
            try:
                num = float(score)
            except (TypeError, ValueError):
                continue
            key = str(dim)
            if key not in scores or num < scores[key]:
                scores[key] = num
        return scores or None
    except Exception as e:
        _log.warning(
            "load_chapter_dim_scores work=%s seq=%s: %s",
            work, seq, e,
        )
        return None
