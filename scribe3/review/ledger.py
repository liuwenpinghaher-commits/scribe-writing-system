"""Track D issue collection for GET /issues Phase A (no LLM)."""
from __future__ import annotations

import logging
from typing import Any, Callable

from scribe3.review.normalize import normalize_issues
from scribe3.review.schema import LEGACY_ERROR_KINDS, QC_ISSUE_LABELS, QC_LIST_KEYS

_log = logging.getLogger("scribe3.review.ledger")


def _hit_text(hit) -> str:
    if isinstance(hit, str):
        return hit
    if isinstance(hit, dict):
        for k in ("phrase", "line", "span", "text", "detail", "reason", "message"):
            if hit.get(k):
                return str(hit[k])
    return str(hit)


def _hit_range(hit) -> list[int]:
    if isinstance(hit, dict):
        span = hit.get("range") or hit.get("loc")
        if isinstance(span, (list, tuple)) and len(span) == 2:
            return [int(span[0] or 0), int(span[1] or 0)]
        if hit.get("start") is not None or hit.get("end") is not None:
            return [int(hit.get("start") or 0), int(hit.get("end") or 0)]
    return [0, 0]


def _iter_list_hits(hits) -> list:
    if hits is None:
        return []
    if isinstance(hits, int):
        return [{} for _ in range(max(0, hits))]
    if isinstance(hits, dict):
        # rhythm/adverb style: single dict hit or None
        return [hits] if hits else []
    if isinstance(hits, list):
        return hits
    return []


def collect_qc_issues(q: dict, seq: int) -> list[dict]:
    issues: list[dict] = []
    for source_key, label in QC_ISSUE_LABELS.items():
        if source_key not in QC_LIST_KEYS and source_key not in q:
            continue
        hits = q.get(source_key)
        # skip non-list rhythm/adverb unless dict present
        if source_key in ("rhythm", "adverb"):
            if not isinstance(hits, dict) or not hits:
                continue
            hits = [hits]
        else:
            hits = _iter_list_hits(hits)
        for idx, hit in enumerate(hits):
            reason = _hit_text(hit)
            raw_sev = "error" if source_key in LEGACY_ERROR_KINDS else "warning"
            typ = "degeneration" if source_key == "degeneration" else source_key
            meta = {"severity": "blocking" if source_key == "degeneration" else raw_sev}
            if isinstance(hit, dict) and hit.get("kind"):
                meta["kind"] = hit.get("kind")
            issues.append({
                "id": f"issue:qc:{seq}:{source_key}:{idx}",
                "source": "qc",
                "type": typ,
                "kind": source_key,
                "severity": raw_sev,
                "title": label,
                "reason": reason,
                "message": reason,
                "chapter": seq,
                "range": _hit_range(hit),
                "text": reason[:80] if reason else "",
                "meta": meta,
                "suggested_action": "定位到正文后改写或删减重复表达。",
            })
    return issues


def collect_causal_issues(causal_result: dict, seq: int) -> list[dict]:
    issues = []
    for idx, v in enumerate(causal_result.get("violations") or []):
        reason = (v.get("reason") if isinstance(v, dict) else str(v)) or str(v)
        issues.append({
            "id": f"issue:causal:{seq}:{idx}",
            "source": "causal",
            "type": "causal",
            "kind": "causal",
            "severity": "warning",
            "title": "因果链缺口",
            "reason": reason,
            "message": reason,
            "chapter": seq,
            "range": [0, 0],
            "text": "",
            "meta": {"severity": "S3", "event": (v or {}).get("event") if isinstance(v, dict) else None},
            "suggested_action": "补上前因、目标或结果承接。",
        })
    return issues


def collect_leak_issues(prose: str, store, seq: int, focalizer: str | None) -> tuple[list[dict], list[dict]]:
    """Returns (issues, degraded_sources). No LLM. Leaks carry knowers enrichment in meta."""
    degraded = []
    issues = []
    if not prose or not focalizer:
        return issues, degraded
    try:
        from scribe3.verify import find_leaks_for_chapter, enrich_leak_payload
        for idx, lk in enumerate(find_leaks_for_chapter(prose, store, focalizer, seq)):
            enr = enrich_leak_payload(lk, store, seq)
            kn_n = int(enr.get("knowers_count") or 0)
            kn_note = f"；知情者 {kn_n} 人" if kn_n else "；知情者未列出/空"
            issues.append({
                "id": f"issue:leaks:{seq}:{idx}",
                "source": "leaks",
                "type": "leak",
                "kind": "leak",
                "severity": "S1",
                "title": "限知泄露",
                "reason": f"破绽词「{lk.marker}」{kn_note}",
                "message": f"限知泄露:「{lk.marker}」{kn_note}",
                "chapter": seq,
                "range": list(lk.range) if lk.range else [0, 0],
                "text": lk.marker,
                "meta": {
                    "severity": "S1",
                    "fact_id": lk.fact_id,
                    "subject": lk.subject,
                    "detector": "find_leaks",
                    "track": "D",
                    "knowers": enr.get("knowers") or [],
                    "knowers_status": enr.get("knowers_status"),
                    "knowers_count": kn_n,
                    "proposition_local": enr.get("proposition_local"),
                },
                "suggested_action": "删破绽词或以误判/物象暗示私密。",
            })
    except Exception as e:
        _log.warning("collect_leak_issues failed seq=%s: %s", seq, e)
        degraded.append({"source": "leaks", "chapter": seq, "reason": str(e)[:200]})
    return issues, degraded


def collect_faction_issues(store) -> list[dict]:
    """全书势力一致性 → advisory issues（meta.scope=work · 禁止 chapter=0）。"""
    issues: list[dict] = []
    try:
        from scribe3.codex_validate import validate_faction_consistency
        findings = validate_faction_consistency(store) or []
    except Exception as e:
        _log.warning("collect_faction_issues: %s", e)
        return issues
    for idx, f in enumerate(findings):
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity") or "low").lower()
        # soft product: map to warning/info
        product_sev = "error" if sev in ("high", "error", "blocking") else "warning"
        fac = f.get("faction") or ""
        detail = f.get("detail") or f.get("kind") or "势力一致性"
        issues.append({
            "id": f"issue:faction:{idx}:{fac or idx}",
            "source": "faction",
            "type": "faction_consistency",
            "kind": str(f.get("kind") or "faction_consistency"),
            "severity": product_sev,
            "title": "势力一致性",
            "reason": str(detail),
            "message": str(detail),
            "chapter": None,  # work-scope · never 0
            "range": [0, 0],
            "text": "",
            "meta": {
                "severity": "advisory",
                "scope": "work",
                "faction": fac,
                "track": "D",
                "raw_severity": sev,
            },
            "suggested_action": "核对势力关系与 power_share，在 Codex 修正后再扫。",
            "target_node": {"type": "work", "label": "全书"},
        })
    return issues


def collect_secret_without_markers(store, seq: int) -> list[dict]:
    """D-debt: secret props open at chapter without leak_markers."""
    issues = []
    try:
        facts = store.facts_at(seq) if hasattr(store, "facts_at") else []
        for idx, f in enumerate(facts or []):
            secret = bool(getattr(f, "secret", False) or (f.get("secret") if isinstance(f, dict) else False))
            if not secret:
                continue
            markers = getattr(f, "leak_markers", None)
            if markers is None and isinstance(f, dict):
                markers = f.get("leak_markers")
            if markers:
                continue
            fid = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else f"fact:{idx}")
            issues.append({
                "id": f"issue:secret_debt:{seq}:{idx}",
                "source": "system",
                "type": "secret_without_markers",
                "kind": "secret_without_markers",
                "severity": "S3",
                "title": "私密命题缺破绽词",
                "reason": f"{fid} 为 secret 但无 leak_markers，限知扫描可能漏检",
                "message": f"{fid} 缺 leak_markers",
                "chapter": seq,
                "range": [0, 0],
                "text": "",
                "meta": {"severity": "S3", "fact_id": fid, "track": "D"},
                "suggested_action": "为私密命题补 leak_markers。",
            })
    except Exception as e:
        _log.warning("collect_secret_without_markers: %s", e)
    return issues


def build_phase_a_ledger(
    *,
    store,
    seq: int,
    qc_fn: Callable,
    causal_fn: Callable,
) -> dict[str, Any]:
    """Phase A: Track D only, never LLM."""
    degraded: list[dict] = []
    raw: list[dict] = []
    sources_run: list[str] = []
    sources_skipped = ["discipline", "llm_review", "quality_dim", "tension_rubric"]

    ch = store.get_chapter(seq) if hasattr(store, "get_chapter") else None
    prose = (ch or {}).get("prose") or ""
    focalizer = (ch or {}).get("focalizer")

    try:
        q = qc_fn(seq) if callable(qc_fn) else {}
        if not isinstance(q, dict):
            q = {}
        raw.extend(collect_qc_issues(q, seq))
        sources_run.append("qc")
        if q.get("detector_errors"):
            for k, msg in (q.get("detector_errors") or {}).items():
                degraded.append({"source": f"qc:{k}", "chapter": seq, "reason": str(msg)[:200]})
    except Exception as e:
        degraded.append({"source": "qc", "chapter": seq, "reason": str(e)[:200]})

    try:
        cr = causal_fn(seq) if callable(causal_fn) else {}
        if not isinstance(cr, dict):
            cr = {}
        raw.extend(collect_causal_issues(cr, seq))
        sources_run.append("causal")
        if cr.get("no_event_data"):
            # not an error; optional info issue
            pass
        if cr.get("error"):
            degraded.append({"source": "causal", "chapter": seq, "reason": str(cr.get("error"))[:200]})
    except Exception as e:
        degraded.append({"source": "causal", "chapter": seq, "reason": str(e)[:200]})

    leak_issues, leak_deg = collect_leak_issues(prose, store, seq, focalizer)
    raw.extend(leak_issues)
    degraded.extend(leak_deg)
    if focalizer and prose:
        sources_run.append("leaks")
    else:
        sources_skipped.append("leaks")

    raw.extend(collect_secret_without_markers(store, seq))
    sources_run.append("secret_without_markers")

    issues = normalize_issues(raw, chapter=seq)
    coverage = {
        "mode": "deterministic_only",
        "tracks": ["D"],
        "sources_run": sources_run,
        "sources_skipped": sources_skipped,
        "snapshot": None,
        "note": "未跑语义深检；点「全量体检」或 POST /review/chapter",
    }
    return {
        "issues": issues,
        "degraded_sources": degraded,
        "coverage": coverage,
    }


def build_work_scope_faction_ledger(store) -> dict[str, Any]:
    """全书势力 advisory 包（供 issue_ledger 全书扫描附加一次）。"""
    raw = collect_faction_issues(store)
    # normalize without forcing chapter=0
    issues = []
    for it in raw:
        row = dict(it)
        if row.get("chapter") == 0:
            row["chapter"] = None
        issues.append(row)
    return {
        "issues": issues,
        "sources_run": ["faction"],
        "coverage_note": "势力一致性为全书 scope（advisory）",
    }
