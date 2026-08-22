"""Unified chapter review runner (POST /review/chapter + post-check delegate)."""
from __future__ import annotations

import logging
from typing import Any, Callable

from scribe3.review.fp import prose_fp
from scribe3.review.normalize import normalize_issues
from scribe3.review.snapshot import persist_enabled, save_chapter_review

_log = logging.getLogger("scribe3.review.runner")


def run_chapter_review(
    *,
    store,
    work: str,
    seq: int,
    prose: str | None = None,
    focalizer: str | None = None,
    mode: str = "deterministic",
    complete_fn: Callable | None = None,
    include_discipline: bool = False,
) -> dict[str, Any]:
    """Run Track D always; Track L when mode=full and flags allow.

    M2–M3: does not require side table; save is no-op unless persist flag set.
    """
    ch = store.get_chapter(seq) if hasattr(store, "get_chapter") else None
    prose = prose if prose is not None else ((ch or {}).get("prose") or "")
    focalizer = focalizer if focalizer is not None else (ch or {}).get("focalizer")
    fp = prose_fp(prose)
    degraded: list[dict] = []
    issues: list[dict] = []
    reviewers_run: list[str] = ["deterministic_d"]
    reviewers_skipped: list[str] = []

    # --- Track D via existing post-check internals when possible ---
    post: dict[str, Any] = {}
    try:
        from scribe3.api.routers import write as write_mod
        # Prefer building through PostCheckReq path if available
        from scribe3.api import models as api_models
        PostCheckReq = getattr(api_models, "PostCheckReq", None)
        if PostCheckReq is not None:
            req = PostCheckReq(prose=prose or "", focalizer=focalizer, seq=seq, chapter=seq)
            # Call post_check function directly — may pull LLM discipline if full
            # For deterministic mode, we build a lightweight D path
            if mode == "deterministic" and not include_discipline:
                post = _deterministic_post(store, work, seq, prose, focalizer)
            else:
                post = write_mod.post_check(req, seq=seq, work=work)
        else:
            post = _deterministic_post(store, work, seq, prose, focalizer)
    except Exception as e:
        _log.warning("runner post path: %s", e)
        post = _deterministic_post(store, work, seq, prose, focalizer)
        degraded.append({"source": "post_check", "reason": str(e)[:200]})

    for iss in post.get("issues") or []:
        if isinstance(iss, dict):
            issues.append(iss)
    for lk in post.get("leaks") or []:
        # already in issues usually
        pass
    if post.get("degraded_stages"):
        for s in post["degraded_stages"]:
            degraded.append({"source": s, "chapter": seq, "reason": "degraded"})
    if post.get("leaks_degraded"):
        degraded.append({"source": "leaks", "chapter": seq, "reason": "leaks_degraded"})

    # discipline counts as L0 when present in post
    if any(i.get("type") == "discipline" for i in issues):
        reviewers_run.append("discipline_l0")
    elif mode == "full":
        reviewers_skipped.append("discipline_l0")

    # L1
    from scribe3.feature_flags import flag_truthy
    llm_on = flag_truthy("SCRIBE3_REVIEW_LLM")
    # complete_fn injection always allows L1 (tests); else need env
    if mode == "full" and (llm_on or complete_fn is not None):
        try:
            from scribe3.review.l1_epistemic import run_l1
            marker_leaks = bool(post.get("leaks"))
            l1 = run_l1(
                prose or "",
                store=store,
                chapter=seq,
                focalizer=focalizer,
                complete_fn=complete_fn,
                marker_leaks_present=marker_leaks,
            )
            issues.extend(l1.get("issues") or [])
            degraded.extend(l1.get("degraded") or [])
            reviewers_run.extend(l1.get("reviewers_run") or [])
            for s in l1.get("reviewers_skipped") or []:
                if s not in reviewers_skipped:
                    reviewers_skipped.append(s)
        except Exception as e:
            degraded.append({"source": "llm_review_l1", "reason": str(e)[:200]})
            reviewers_skipped.append("llm_review_l1")
    else:
        if "llm_review_l1" not in reviewers_skipped:
            reviewers_skipped.append("llm_review_l1")
        for name in ("llm_review_l2", "llm_review_l3", "llm_review_l4", "llm_review_l5"):
            if name not in reviewers_skipped:
                reviewers_skipped.append(name)

    # A3: ten-dim quality_dim advisory from completed evaluation (read-only, no LLM)
    dim_note = ""
    if mode in ("full", "semantic"):
        try:
            from scribe3.quality.dim_scores import (
                load_chapter_dim_scores,
                quality_dim_advisory_enabled,
            )
            from scribe3.review.m5_projection import project_quality_dim_advisory

            if not quality_dim_advisory_enabled():
                if "quality_dim" not in reviewers_skipped:
                    reviewers_skipped.append("quality_dim")
            else:
                scores = load_chapter_dim_scores(store, work, seq)
                if scores:
                    issues.extend(project_quality_dim_advisory(scores, chapter=seq))
                    if "quality_dim" not in reviewers_run:
                        reviewers_run.append("quality_dim")
                else:
                    if "quality_dim" not in reviewers_skipped:
                        reviewers_skipped.append("quality_dim")
                    dim_note = "无十维分数"
        except Exception as e:
            degraded.append({"source": "quality_dim", "chapter": seq, "reason": str(e)[:200]})
            if "quality_dim" not in reviewers_skipped:
                reviewers_skipped.append("quality_dim")
    else:
        if "quality_dim" not in reviewers_skipped:
            reviewers_skipped.append("quality_dim")

    norm = normalize_issues(issues, chapter=seq)
    cov_mode = "full" if mode == "full" and "llm_review_l1" in reviewers_run else (
        "semantic" if mode == "full" else "deterministic"
    )
    if mode == "full" and "llm_review_l1" not in reviewers_run:
        cov_mode = "partial"
    has_l = any(
        x.startswith("llm") or x in ("discipline_l0", "quality_dim")
        for x in reviewers_run
    )
    note_parts = []
    if reviewers_skipped and mode == "full":
        note_parts.append("partial")
    if dim_note:
        note_parts.append(dim_note)
    coverage = {
        "mode": cov_mode,
        "tracks": ["D"] + (["L"] if has_l else []),
        "reviewers_run": reviewers_run,
        "reviewers_skipped": reviewers_skipped,
        "prose_fp": fp,
        "note": "；".join(note_parts),
    }
    out = {
        "ok": True,
        "chapter": seq,
        "work": work,
        "mode": mode,
        "prose_fp": fp,
        "issues": norm,  # 人话给前端；消费方应优先读 gate.hits
        "leaks": post.get("leaks") or [],
        "quality": post.get("quality"),
        "ai_grade": post.get("ai_grade"),
        "degraded_sources": degraded,
        "degraded_stages": post.get("degraded_stages") or [],
        "leaks_degraded": post.get("leaks_degraded"),
        "coverage": coverage,
        "post": post,
    }
    # snapshot write only when enabled (M4a); quality_dim has meta.track=L
    if persist_enabled() and mode in ("full", "semantic", "deterministic"):
        save_chapter_review(store, work=work, seq=seq, payload={
            "prose_fp": fp,
            "mode": cov_mode,
            "issues": [i for i in norm if (i.get("meta") or {}).get("track") == "L"
                       or i.get("source") in ("llm_review", "discipline", "quality_dim")],
            "coverage": coverage,
            "degraded": degraded,
        })
    try:
        if flag_truthy("SCRIBE3_QUALITY_GATE_UNIFIED"):
            from scribe3.quality_gate import from_existing
            out["gate"] = from_existing({
                "ok": out.get("ok"),
                "code": "review",
                "message": str(out.get("note") or ""),
                "hits": out.get("issues") or [],
            })
    except Exception:
        pass
    return out


def _deterministic_post(store, work: str, seq: int, prose: str, focalizer: str | None) -> dict:
    """Minimal D-only post-check shape without LLM discipline."""
    from scribe3.critique import quality_flags, quality_issues
    from scribe3.verify import find_leaks_for_chapter

    degraded_stages = []
    try:
        qf = quality_flags(prose or "")
    except Exception:
        qf = {}
        degraded_stages.append("quality_flags")
    from scribe3.qc_product_keys import product_qc_breakdown_from_flags, product_qc_total
    qc_breakdown = product_qc_breakdown_from_flags(qf)
    issues = []
    try:
        issues = quality_issues(prose or "")
    except Exception:
        degraded_stages.append("quality_issues")
    leaks = []
    leaks_degraded = False
    if focalizer and prose:
        try:
            from scribe3.verify import enrich_leak_payload
            leaks = [
                enrich_leak_payload(lk, store, seq)
                for lk in find_leaks_for_chapter(prose, store, focalizer, seq)
            ]
            for lk in leaks:
                issues.append({
                    "type": "leak",
                    "message": f"限知泄露:「{lk['marker']}」",
                    "text": lk["marker"],
                    "range": lk["range"],
                    "meta": {
                        "severity": "S1",
                        "fact_id": lk["fact_id"],
                        "subject": lk["subject"],
                        "knowers": lk.get("knowers") or [],
                        "knowers_status": lk.get("knowers_status"),
                        "knowers_count": lk.get("knowers_count"),
                    },
                })
        except Exception:
            leaks_degraded = True
            degraded_stages.append("find_leaks")
    return {
        "issues": issues,
        "leaks": leaks,
        "leaks_degraded": leaks_degraded,
        "degraded_stages": degraded_stages,
        "quality": {"total": product_qc_total(qc_breakdown), **qc_breakdown},
        "ai_grade": None,
    }
