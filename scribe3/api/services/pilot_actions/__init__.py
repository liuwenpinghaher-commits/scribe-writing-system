"""Pilot action stages. Beats/deduce/draft modules retired; they call playbook."""
from __future__ import annotations

from scribe3.api.services.pilot_actions import (
    outline,
    check,
    deliver,
    finalize,
)

_STAGE_MODULES = (outline, check, deliver, finalize)

ACTION_KEYS = (
    "propose_outline",
    "expand_beats",
    "deduce",
    "draft_loop",
    "full_check",
    "deliver",
    "finalize",
)


def _playbook_action(work: str, stage: str):
    def fn(st, seq):
        from scribe3.playbook.context import build_ctx
        from scribe3.playbook.pipeline import run_stage

        def llm_fn(prompt, max_tokens=4096, **_kw):
            from scribe3.api.services.misc_helpers import _pilot_llm_gen
            return _pilot_llm_gen(st, work, seq, stage, prompt, max_tokens=max_tokens)

        return run_stage(
            st, int(seq), stage, llm_fn=llm_fn,
            ctx=build_ctx(st, int(seq), playbook=st), persist=True,
        )
    return fn


def build_pilot_executor_body(work: str) -> dict:
    out: dict = {}
    for mod in _STAGE_MODULES:
        out.update(mod.build_actions(work))
    out["expand_beats"] = _playbook_action(work, "design")
    out["deduce"] = _playbook_action(work, "deduce")
    out["draft_loop"] = _playbook_action(work, "draft")
    missing = [k for k in ACTION_KEYS if k not in out]
    if missing:
        raise RuntimeError(f"pilot stage map missing keys: {missing}")
    return {k: out[k] for k in ACTION_KEYS}
