"""从已加载故事输入冻结 ExpectedFacts。有 I/O，禁止再打 facts_at。"""
from __future__ import annotations

from typing import Any

from scribe3.run_card import ExpectedFacts, make_facts


def _truthy_flag(name: str, default: str = "0") -> bool:
    try:
        from scribe3.feature_flags import get_flag
        raw = get_flag(name)
    except Exception:
        import os
        raw = os.environ.get(name, default)
    return str(raw or default).strip().lower() in ("1", "true", "yes", "on")


def collect_expected_facts(
    st: Any,
    *,
    work: str,
    chapter: int,
    phase: str,
    with_tools: bool,
    focalizer: str | None,
    request_text: str = "",
    extra_instructions: str = "",
    inputs: dict | None = None,
    holder: dict | None = None,
    is_revision: bool | None = None,
) -> ExpectedFacts:
    inp = inputs if isinstance(inputs, dict) else {}
    hold = holder if isinstance(holder, dict) else {}
    np = (phase or "").strip().lower()
    contract = inp.get("contract") if isinstance(inp.get("contract"), dict) else {}
    traces = inp.get("evidence_must_show") or []
    if not isinstance(traces, list):
        traces = []
    try:
        from scribe3.narrative_contract import (
            contract_has_scene_fields,
            is_drive_template_turn,
            _is_slogan_or_placeholder,
        )
        has_scene = contract_has_scene_fields(contract)
        slogan_fields: list[str] = []
        for key in ("desire", "obstacle", "turn", "cost"):
            val = str(contract.get(key) or "")
            if val and (_is_slogan_or_placeholder(val) or is_drive_template_turn(val)):
                slogan_fields.append(key)
    except Exception:
        has_scene = bool(contract)
        slogan_fields = []

    present_fields = tuple(
        k for k in ("desire", "obstacle", "turn", "cost")
        if str(contract.get(k) or "").strip()
    )

    has_prev = False
    prev_hook = bool(str(inp.get("prior_consequences") or "").strip())
    if int(chapter or 0) > 1 and st is not None and hasattr(st, "get_chapter"):
        try:
            prev = st.get_chapter(int(chapter) - 1)
            has_prev = bool(prev)
            if isinstance(prev, dict) and not prev_hook:
                pnd = prev.get("narrative_drive") if isinstance(prev.get("narrative_drive"), dict) else {}
                prev_hook = bool(str(pnd.get("end_hook") or "").strip())
        except Exception:
            has_prev = int(chapter) > 1

    ch: dict = {}
    if st is not None and hasattr(st, "get_chapter"):
        try:
            ch = st.get_chapter(int(chapter)) or {}
        except Exception:
            ch = {}
    if not isinstance(ch, dict):
        ch = {}
    beats = ch.get("beats") if isinstance(ch.get("beats"), dict) else {}
    if not beats and isinstance(ch.get("beats_meta"), dict):
        beats = ch.get("beats_meta") or {}
    should_vac = False
    has_goal = bool(str(beats.get("goal") or "").strip())
    has_conflict = bool(str(beats.get("conflict") or "").strip())
    try:
        from scribe3.drama_beats import should_inject_drama_vacuum
        should_vac = bool(should_inject_drama_vacuum(beats if beats else ch))
    except Exception:
        should_vac = (not has_goal) and (not has_conflict)

    if is_revision is None:
        try:
            from scribe3.api.services.write_assemble_blocks import is_revision_request
            is_rev = bool(is_revision_request(
                phase=phase or "",
                request_text=request_text or "",
                extra_instructions=extra_instructions or "",
            ))
        except Exception:
            is_rev = False
    else:
        is_rev = bool(is_revision)

    move_on = False
    move_ok = False
    try:
        from scribe3.story_move import move_library_enabled, plan_from_chapter, validate_story_move_plan
        move_on = bool(move_library_enabled())
        plan = plan_from_chapter(ch)
        val = plan.get("validation") if isinstance(plan.get("validation"), dict) else validate_story_move_plan(plan)
        move_ok = bool(plan.get("approved")) and bool(val.get("ok"))
    except Exception:
        move_on = _truthy_flag("SCRIBE3_MOVE_LIBRARY", "0")

    try:
        from scribe3.novel_quality_flags import narrative_engine_enabled
        engine_on = bool(narrative_engine_enabled())
    except Exception:
        engine_on = True

    try:
        from scribe3.structure_style import structure_diversity_inject_enabled
        sd_on = bool(structure_diversity_inject_enabled())
    except Exception:
        sd_on = True

    try:
        from scribe3.storyline_inject_polish import storyline_inject_enabled
        sl_on = bool(storyline_inject_enabled())
    except Exception:
        sl_on = False

    try:
        from scribe3.benchmark_lib import benchmark_inject_enabled
        bench_on = bool(benchmark_inject_enabled())
    except Exception:
        bench_on = False

    try:
        from scribe3.injection_compact import volume_intro_compact_enabled
        vol_flag = bool(volume_intro_compact_enabled())
    except Exception:
        vol_flag = False

    try:
        from scribe3.context_budget import envelope_v2_enabled, resolve_write_caps
        env_v2 = bool(envelope_v2_enabled())
        caps = resolve_write_caps(work)
    except Exception:
        env_v2 = True
        caps = {
            "prompt_hard": 48000,
            "prompt_hard_profile": "novel_48k",
            "supplemental_soft": 14000,
            "supplemental_hard": 18000,
            "novel_wide": False,
            "model_context_window": "",
        }

    try:
        from scribe3.injection_registry import registry_mode
        reg = str(registry_mode() or "active")
    except Exception:
        reg = "active"

    reread_ok = True
    try:
        from scribe3.experience import exp_state as _exp
        w = work or "main"
        reread_ok = bool(
            _exp.has_reread_ack(w, chapter) or not _exp.get_require_reread(w)
        )
    except Exception:
        reread_ok = True

    drama_vac_flag = True
    try:
        import os
        raw = os.environ.get("SCRIBE3_DRAMA_VACUUM_WARN", "1")
        drama_vac_flag = str(raw).strip().lower() not in ("0", "false", "off", "no")
    except Exception:
        drama_vac_flag = True

    discourse_on = _truthy_flag("SCRIBE3_DISCOURSE_ADVISORY", "0") or _truthy_flag(
        "SCRIBE3_DISCOURSE_RASHOMON", "0",
    )

    synopsis = str(ch.get("synopsis") or "").strip()
    has_beats = bool(beats) or bool(ch.get("beats"))
    seeds = ch.get("seed_words") or ch.get("seeds") or []
    extra = extra_instructions or ""

    return make_facts(
        work=work or "main",
        chapter=int(chapter or 0),
        phase=phase or "draft",
        normalized_phase=np or "draft",
        with_tools=bool(with_tools),
        is_revision=is_rev,
        has_focalizer=bool((focalizer or "").strip()),
        contract_has_scene=bool(has_scene),
        contract_field_present=present_fields,
        trace_count=len([t for t in traces if str(t).strip()]),
        has_prev_chapter=bool(has_prev),
        prev_end_hook=bool(prev_hook),
        beats_has_goal=has_goal,
        beats_has_conflict=has_conflict,
        should_drama_vacuum=should_vac,
        secret_guard_nonempty=bool(hold.get("secret_guard_nonempty")),
        has_unpublished_markers=bool(hold.get("has_unpublished_markers")),
        has_synopsis=bool(synopsis),
        has_beats=bool(has_beats),
        has_seed_words=bool(seeds),
        has_volume_intro=bool(ch.get("volume_intro") or ch.get("volume")),
        has_brief_must=bool(
            ch.get("brief_must") or ch.get("must") or synopsis or has_beats
        ),
        has_pressure_drive=bool(ch.get("pressure_drive") or ch.get("pressure")),
        has_author_prefs=bool(ch.get("author_prefs")),
        has_voice_anchor=bool(inp.get("voice") or ch.get("voice_anchor")),
        has_purpose=bool(ch.get("purpose") or ch.get("intent")),
        has_materials=bool(ch.get("materials") or (hasattr(st, "list_materials") and False)),
        has_reference_briefs=bool(ch.get("reference_briefs")),
        has_storyline_meta=bool(
            ch.get("storyline") or ch.get("storyline_meta") or sl_on
        ),
        has_discourse=bool(ch.get("discourse") or discourse_on),
        has_deduction=bool(
            ch.get("deduction_final") or ch.get("deduction") or ch.get("deductions")
        ),
        has_scene_truth=bool(ch.get("scene_truth")),
        has_extra_instructions=bool(str(extra).strip()),
        has_craft_rules=True,  # build_craft_block 默认引擎恒注入
        reread_ok=reread_ok,
        registry_mode=reg,
        move_library=move_on,
        move_plan_approved=move_ok,
        narrative_engine=engine_on,
        drama_vacuum_flag=drama_vac_flag,
        storyline_inject=sl_on,
        discourse_advisory=discourse_on,
        structure_diversity=sd_on,
        volume_intro_flag=vol_flag,
        benchmark_inject=bench_on,
        envelope_v2=env_v2,
        novel_wide=bool(caps.get("novel_wide")),
        prompt_hard=int(caps.get("prompt_hard") or 48000),
        prompt_hard_profile=str(caps.get("prompt_hard_profile") or "novel_48k"),
        supplemental_soft=int(caps.get("supplemental_soft") or 14000),
        supplemental_hard=int(caps.get("supplemental_hard") or 18000),
        model_context_window=str(caps.get("model_context_window") or ""),
        contract_slogan_fields=tuple(slogan_fields),
    )
