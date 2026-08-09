"""L1 semantic limited-POV reviewer (Track L). Never put secret values in payload."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable

from scribe3.review.normalize import normalize_issues
from scribe3.review.resonance import l1_marker_resonance

_log = logging.getLogger("scribe3.review.l1")

MAX_SECRETS = 24

L1_SYSTEM = (
    "你是长篇网文限知审计员。只根据「焦点角色已知事实」与「禁止直说的私密标签」"
    "判断正文是否泄露了焦点不该知道的内容。不要复述私密正文 value。"
    "只输出 JSON：{\"findings\":[{\"issue\":\"...\",\"evidence\":\"正文短引\",\"severity\":\"S2\"}]}"
)


def build_l1_payload(
    prose: str,
    *,
    focalizer: str,
    secrets: list[dict],
    known_summaries: list[str] | None = None,
) -> dict[str, Any]:
    """Build LLM payload. secrets items: {id, attribute, entity, has_markers} — NEVER value."""
    safe_secrets = []
    for s in (secrets or [])[:MAX_SECRETS]:
        if isinstance(s, dict) and "value" in s:
            s = {k: v for k, v in s.items() if k != "value"}
        safe_secrets.append({
            "id": s.get("id"),
            "attribute": s.get("attribute"),
            "entity": s.get("entity") or s.get("entity_id"),
            "has_markers": bool(s.get("has_markers") or s.get("leak_markers")),
            "label": s.get("label") or s.get("attribute") or "私密槽",
        })
    return {
        "focalizer": focalizer,
        "prose_excerpt": (prose or "")[:6000],
        "known_facts": (known_summaries or [])[:40],
        "secret_slots": safe_secrets,
        "instruction": "若正文像全知写出了 secret_slots 中的私密，报告 finding；禁止在输出中粘贴私密真值。",
    }


def secrets_from_store(store, chapter: int, focalizer: str) -> tuple[list[dict], list[str], set[str]]:
    """Return (secret_slots, known_summaries, marker_set) without secret values in slots."""
    from scribe3.knowledge import project_frame

    frame = project_frame(store, focalizer, chapter)
    known = []
    markers: set[str] = set()
    slots = []
    try:
        facts = store.facts_at(chapter)
    except Exception:
        facts = []
    for f in facts or []:
        fid = getattr(f, "id", None) or ""
        secret = bool(getattr(f, "secret", False))
        attr = getattr(f, "attribute", "") or ""
        eid = getattr(f, "entity_id", "") or ""
        val = getattr(f, "value", "") or ""
        lm = list(getattr(f, "leak_markers", None) or [])
        if frame.knows(fid):
            known.append(f"{eid.split(':')[-1]}·{attr}={'…' if secret else (val[:40] if val else '')}")
            continue
        if secret:
            slots.append({
                "id": fid,
                "attribute": attr,
                "entity": eid,
                "has_markers": bool(lm),
                "label": f"{eid.split(':')[-1]}·{attr}",
            })
            for m in lm or ([val] if val else []):
                if m:
                    markers.add(str(m))
    return slots, known, markers


def run_l1(
    prose: str,
    *,
    store,
    chapter: int,
    focalizer: str | None,
    complete_fn: Callable[[str, str | None], str] | None = None,
    marker_leaks_present: bool = False,
) -> dict[str, Any]:
    """Returns {issues, degraded, reviewers_run, payload_safe}."""
    llm_env = (os.environ.get("SCRIBE3_REVIEW_LLM") or "0").strip().lower() in (
        "1", "true", "yes", "on",
    )
    # Unit tests pass complete_fn explicitly; production needs env flag unless inject fn.
    if complete_fn is None and not llm_env:
        return {
            "issues": [],
            "degraded": [{"source": "llm_review_l1", "reason": "SCRIBE3_REVIEW_LLM off"}],
            "reviewers_run": [],
            "reviewers_skipped": ["llm_review_l1"],
        }
    if not focalizer or not (prose or "").strip():
        return {
            "issues": [],
            "degraded": [],
            "reviewers_run": [],
            "reviewers_skipped": ["llm_review_l1"],
        }
    slots, known, markers = secrets_from_store(store, chapter, focalizer)
    payload = build_l1_payload(prose, focalizer=focalizer, secrets=slots, known_summaries=known)
    # safety: no values
    blob = json.dumps(payload, ensure_ascii=False)
    if '"value"' in blob:
        return {
            "issues": [],
            "degraded": [{"source": "llm_review_l1", "reason": "payload_contained_value"}],
            "reviewers_run": [],
            "reviewers_skipped": ["llm_review_l1"],
        }

    if complete_fn is None:
        try:
            from scribe3.llm import hermes_complete, default_timeout

            def complete_fn(prompt: str, system: str | None = None) -> str:
                return hermes_complete(
                    prompt, system=system,
                    timeout=min(float(default_timeout()), 180.0),
                    max_tokens=600, retries_override=1,
                    thinking="disabled", temperature=0,
                )
        except Exception as e:
            return {
                "issues": [],
                "degraded": [{"source": "llm_review_l1", "reason": f"no_complete_fn:{e}"}],
                "reviewers_run": [],
                "reviewers_skipped": ["llm_review_l1"],
            }

    prompt = "限知审计任务 JSON 输入：\n" + json.dumps(payload, ensure_ascii=False)
    try:
        raw = complete_fn(prompt, L1_SYSTEM)
    except Exception as e:
        _log.warning("L1 complete failed: %s", e)
        return {
            "issues": [],
            "degraded": [{"source": "llm_review_l1", "reason": str(e)[:200]}],
            "reviewers_run": ["llm_review_l1"],
            "reviewers_skipped": [],
        }

    findings = _parse_findings(raw)
    issues = []
    for idx, f in enumerate(findings):
        evidence = str(f.get("evidence") or "")[:120]
        issue_txt = str(f.get("issue") or "疑似限知越界")
        # marker resonance
        hit_marker = marker_leaks_present or any(m and m in (prose or "") for m in list(markers)[:20])
        res = l1_marker_resonance(f, leak_markers_hit=hit_marker)
        sev = "S1" if res else "S2"
        rng = None
        if evidence:
            i = (prose or "").find(evidence[:20])
            if i >= 0:
                rng = [i, i + len(evidence[:20])]
        issues.append({
            "id": f"issue:llm_review:{chapter}:l1:{idx}",
            "source": "llm_review",
            "type": "llm_review",
            "kind": "l1_epistemic",
            "severity": sev,
            "title": "语义限知风险",
            "reason": issue_txt,
            "message": issue_txt,
            "chapter": chapter,
            "range": rng or [0, 0],
            "text": evidence,
            "meta": {
                "severity": sev,
                "resonance": res,
                "detector": "L1",
                "track": "L",
            },
            "suggested_action": "改写为焦点角色可知范围；删除全知破绽。",
        })
    return {
        "issues": normalize_issues(issues, chapter=chapter),
        "degraded": [],
        "reviewers_run": ["llm_review_l1"],
        "reviewers_skipped": [],
        "payload_safe": True,
    }


def _parse_findings(raw: str) -> list[dict]:
    if not raw:
        return []
    text = raw.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    try:
        data = json.loads(text)
    except Exception:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        fs = data.get("findings") or data.get("issues") or []
        return [x for x in fs if isinstance(x, dict)]
    return []
