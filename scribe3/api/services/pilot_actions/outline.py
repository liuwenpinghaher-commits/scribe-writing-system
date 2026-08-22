"""Pilot action stage module (P1-16 phase split)."""
from __future__ import annotations


def build_actions(work: str) -> dict:
    """Bind pilot_runtime free vars and return this stage's action callables."""
    from scribe3.api.services import pilot_runtime as pr
    g = globals()
    for name in dir(pr):
        if name.startswith("__"):
            continue
        g[name] = getattr(pr, name)
    import json, os, logging  # noqa: F401 — used by stage bodies

    def propose_outline(st, seq):
        from scribe3.stage_generate import (
            STAGE_MAX_TOKENS,
            thicken_stage,
        )
        ch0 = st.get_chapter(seq) or {}
        steer = _pilot_steer(st, seq)
        stage_name = "design"

        def llm_fn(prompt, max_tokens=STAGE_MAX_TOKENS[stage_name if stage_name != "plan" else "outline"]):
            return _pilot_llm_gen(
                st, work, seq, stage_name, prompt, max_tokens=max_tokens,
            )

        result = thicken_stage(
            stage_name,
            ch0,
            llm_fn=llm_fn,
            persist_fn=lambda fields: st.update_chapter_meta(seq, fields),
            seq=seq,
            extra=(f"作者意图(最高优先):{steer}" if steer else ""),
            st=st, work=work, focalizer="",
        )
        if result.get("skipped"):
            return result
        if not result.get("ok"):
            return {
                "pilot_park": result.get("message") or "大纲 LLM 未达覆盖地板",
                **result,
            }
        out = result.get("synopsis") or ""
        # OI-2：仅本步新写出 synopsis 时 ensure 本章（skip 大纲不会走到这里）
        _nd = None
        try:
            from scribe3.novel_quality_flags import narrative_engine_enabled
            if narrative_engine_enabled():
                from scribe3.narrative_drive import ensure_narrative_drive
                _nd = ensure_narrative_drive(st, seq, steer=_pilot_steer(st, seq) or "")
        except Exception as e:
            logging.getLogger("scribe3").warning(
                "propose_outline ensure_narrative_drive fail-soft: %s", e)
        ret = {"synopsis": out}
        if _nd is not None:
            ret["narrative_drive"] = _nd
        return ret


    return {"propose_outline": propose_outline}
