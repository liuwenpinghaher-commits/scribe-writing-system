"""Single judge entry. T=0. Evidence then yes/no. Majority only on sha-unchanged retry."""
from __future__ import annotations

from typing import Any, Callable

from scribe3.playbook.parse import InfraError, parse_json_with_retry
from scribe3.playbook.prompts import (
    contract_judge,
    deduce_judge,
    draft_judge,
    duty_judge,
    duty_judge_v2,
    final_judge,
    final_judge_v2,
    identity_for,
    play_judge,
    play_judge_v2,
)
from scribe3.playbook.quote import PLAYBOOK_VERSION

RUBRICS = {
    "duty": duty_judge,
    "play": play_judge,
    "contract": contract_judge,
    "deduce": deduce_judge,
    "draft": draft_judge,
    "final": final_judge,
}
RUBRICS_V2 = {
    **RUBRICS,
    "duty": duty_judge_v2,
    "play": play_judge_v2,
    "final": final_judge_v2,
}
VERSIONED_RUBRICS = ("playbook.2", "playbook.3", "playbook.3.1", "playbook.3.2", "playbook.3.2.1", "playbook.3.2.2", "playbook.3.2.3", "playbook.3.2.4")


def _rubrics_for(version: str) -> dict:
    if version == "playbook.2":
        return RUBRICS_V2
    return RUBRICS


def _call(llm_fn: Callable, prompt: str, *, system: str) -> str:
    try:
        return llm_fn(prompt, max_tokens=2048, system=system, temperature=0) or ""
    except TypeError:
        try:
            return llm_fn(prompt, max_tokens=2048) or ""
        except TypeError:
            return llm_fn(prompt) or ""


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    verdict = str(raw.get("verdict") or "").strip().lower()
    answers = list(raw.get("answers") or [])
    if verdict not in ("pass", "fail", "needs_human"):
        nos = [a for a in answers if str((a or {}).get("answer") or "").lower() in ("no", "fail")]
        yes_ev = [
            a for a in answers
            if str((a or {}).get("answer") or "").lower() in ("yes", "pass")
            and str((a or {}).get("evidence") or "").strip()
        ]
        if nos:
            verdict = "fail"
        elif not yes_ev:
            verdict = "needs_human"
        else:
            # 格式坏了不能默认盖章通过
            verdict = "needs_human"
    return {
        "verdict": verdict,
        "answers": answers,
        "opinion": str(raw.get("opinion") or ""),
        "judge_version": PLAYBOOK_VERSION,
    }


def judge(
    artifact_type: str,
    artifact: dict,
    rubric_version: str,
    context: dict,
    *,
    llm_fn: Callable | None = None,
    prior: dict | None = None,
) -> dict[str, Any]:
    del artifact  # judges read via context (assembled to match rubric)
    table = _rubrics_for(rubric_version or PLAYBOOK_VERSION)
    if isinstance(prior, dict) and prior.get("verdict") in ("pass", "fail"):
        return _normalize(prior)
    fn = table.get(artifact_type)
    if fn is None:
        raise ValueError(f"unknown judge type: {artifact_type}")
    if llm_fn is None:
        raise InfraError("judge 缺少 llm_fn")
    prompt = fn(context)
    system = identity_for("judge")

    def _once() -> str:
        text = _call(llm_fn, prompt, system=system)
        if not str(text).strip():
            raise InfraError("法官返回空")
        return text

    return _normalize(parse_json_with_retry(_once))


def majority_if_disagreed(first: dict, second: dict, third: dict | None) -> dict[str, Any]:
    votes = [first.get("verdict"), second.get("verdict")]
    if third:
        votes.append(third.get("verdict"))
    winner = "fail" if votes.count("fail") >= votes.count("pass") else "pass"
    picked = third if third and third.get("verdict") == winner else (
        second if second.get("verdict") == winner else first
    )
    out = dict(picked)
    out["rounds"] = [{"verdict": v} for v in votes]
    return out
