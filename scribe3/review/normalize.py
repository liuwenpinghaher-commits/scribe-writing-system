"""Map legacy severities and normalize issue dicts to canonical schema."""
from __future__ import annotations

from typing import Any

from scribe3.review.schema import CANONICAL_SEVERITIES, LEGACY_ERROR_KINDS


def map_legacy_severity(
    sev: str | None,
    *,
    kind: str | None = None,
    type_: str | None = None,
) -> str:
    """Map error/warning/blocking/advisory → S1–S4|info."""
    s = str(sev or "").strip()
    if not s:
        return "S3"
    su = s.upper()
    if su in CANONICAL_SEVERITIES or su == "INFO":
        return "info" if su == "INFO" else su
    if su == "BLOCKING":
        return "S1"
    if su == "ADVISORY":
        return "S2"
    if su == "ERROR":
        # legacy ledger used error for harsh QC; never auto-S1
        return "S2"
    if su == "WARNING":
        return "S3"
    if su in ("CRITICAL", "HIGH"):
        return "S2"
    if su in ("LOW", "HINT"):
        return "S4"
    return "S3"


def normalize_issue(raw: dict[str, Any], *, chapter: int | None = None) -> dict[str, Any]:
    """Produce one canonical issue dict (status always open per KD-18)."""
    meta = dict(raw.get("meta") or {})
    kind = raw.get("kind") or raw.get("type") or meta.get("kind") or "unknown"
    type_ = raw.get("type") or kind
    sev_raw = meta.get("severity") or raw.get("severity")
    # degeneration with blocking → S1
    if type_ == "degeneration" and str(sev_raw or "").lower() == "blocking":
        sev = "S1"
    elif type_ == "pressure" and str(sev_raw or "").lower() == "blocking":
        sev = "S1"
    else:
        sev = map_legacy_severity(str(sev_raw) if sev_raw is not None else None, kind=str(kind), type_=str(type_))
    meta["severity"] = sev
    if "track" not in meta:
        src = str(raw.get("source") or "")
        meta["track"] = "L" if src in ("llm_review", "discipline") or type_ == "llm_review" else "D"
    ch = chapter if chapter is not None else raw.get("chapter")
    out = {
        "id": raw.get("id") or f"issue:{raw.get('source') or 'x'}:{ch}:{kind}",
        "source": raw.get("source") or "system",
        "type": type_,
        "kind": kind,
        "severity": sev,
        "title": raw.get("title") or raw.get("message") or str(kind),
        "reason": raw.get("reason") or raw.get("message") or "",
        "chapter": ch,
        "range": raw.get("range") if isinstance(raw.get("range"), list) else [0, 0],
        "text": raw.get("text") or "",
        "status": "open",
        "suggested_action": raw.get("suggested_action") or "定位后改写或登记设定。",
        "meta": meta,
        "target_node": raw.get("target_node"),
        "fix_action": raw.get("fix_action") or meta.get("fix_action"),
    }
    if out["target_node"] is None and ch is not None:
        out["target_node"] = {
            "id": f"ch:{ch}",
            "type": "chapter",
            "ref": ch,
            "label": f"第 {ch} 章",
        }
    return out


def normalize_issues(items: list[dict] | None, *, chapter: int | None = None) -> list[dict]:
    out = [normalize_issue(i, chapter=chapter) for i in (items or []) if isinstance(i, dict)]
    order = {s: i for i, s in enumerate(CANONICAL_SEVERITIES)}
    out.sort(key=lambda d: order.get(d.get("severity") or "S4", 99))
    return out
