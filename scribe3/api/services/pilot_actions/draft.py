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

    def draft_loop(st, seq):
        import re as _re_dl
        ch = st.get_chapter(seq) or {}
        steer = _pilot_steer(st, seq) or ""
        # 叙事引擎：draft 入口二次 ensure（引导优先；GATE 默认关）
        try:
            from scribe3.novel_quality_flags import (
                narrative_engine_enabled,
                event_drive_gate_enabled,
            )
            if narrative_engine_enabled():
                from scribe3.narrative_drive import (
                    ensure_narrative_drive,
                    format_narrative_park,
                )
                _d_drive = ensure_narrative_drive(st, seq, steer=steer)
                if (
                    event_drive_gate_enabled()
                    and _d_drive
                    and (_d_drive.get("validation") or {}).get("ok") is False
                ):
                    return {"pilot_park": format_narrative_park(_d_drive)}
        except Exception as e:
            logging.getLogger("scribe3").warning(
                "draft_loop ensure_narrative_drive fail-soft: %s", e)
        from scribe3.stage_generate import (
            STAGE_MAX_TOKENS,
            iceberg_ok_for,
            stage_ready,
            thicken_draft,
        )
        ready = stage_ready(ch, "draft")
        if not ready.get("ok"):
            return {
                "pilot_park": ready.get("message") or "排演前一阶段未齐",
                **ready,
            }
        if not iceberg_ok_for(ch, "draft"):
            def _draft_llm(prompt, max_tokens=STAGE_MAX_TOKENS["draft"]):
                return _pilot_llm_gen(
                    st, work, seq, "draft", prompt, max_tokens=max_tokens,
                )
            rehearsed = thicken_draft(
                ch,
                llm_fn=_draft_llm,
                persist_fn=lambda fields: st.save_chapter_draft(seq, fields.get("draft") or ""),
                seq=seq,
                extra=steer,
            )
            if not rehearsed.get("ok") and not rehearsed.get("skipped"):
                return {
                    "pilot_park": rehearsed.get("message") or "排演 LLM 未达覆盖地板",
                    **rehearsed,
                }
            ch = st.get_chapter(seq) or ch
        prose_now = (ch.get("prose") or "").strip()
        # PR-4：有 GCD 戏剧合同时，禁止「仅因字数不足」清稿（宁短勿巷志）
        _has_drama = False
        try:
            from scribe3.drama_beats import beats_have_drama_gcd
            _bm = ch.get("beats_meta") or {}
            _hook = ""
            if isinstance(_bm, dict):
                _hook = str(_bm.get("chapter_hook") or "").strip()
            _has_drama = beats_have_drama_gcd(ch.get("beats") or [], chapter_hook=_hook)
        except Exception:
            _has_drama = False
        # EC：核心决策走 shipped plan_draft_loop（单测真源）
        from scribe3.novel_quality_flags import (
            craft_novel_enabled,
            default_drama_steer_enabled,
            drive_prose_drift_enabled,
            narrative_engine_enabled,
            soft_fulfill_enabled,
            soft_fulfill_resteer_enabled,
        )
        from scribe3.execution_contract import plan_draft_loop
        _drive_ec = ch.get("narrative_drive") if isinstance(ch.get("narrative_drive"), dict) else {}
        _plan = plan_draft_loop(
            prose=prose_now,
            steer=steer,
            has_drama=_has_drama,
            drive=_drive_ec,
            narrative_engine=bool(narrative_engine_enabled()),
            default_drama_steer=bool(default_drama_steer_enabled()),
            soft_fulfill_on=bool(soft_fulfill_enabled()),
            drift_on=bool(drive_prose_drift_enabled()),
            resteer_on=bool(soft_fulfill_resteer_enabled()),
            craft_novel=bool(craft_novel_enabled()),
            seq=int(seq),
        )
        if _plan.get("force_clear"):
            try:
                # SCHEMAFULL prose 是 string，不可 SET NONE；空串才合法
                st.clear_chapter_prose_for_redraft(seq)
                logging.getLogger("scribe3").info(
                    "draft_loop force clear prose work=%s seq=%s", work, seq)
            except Exception as e:
                logging.getLogger("scribe3").warning("force redraft clear prose failed: %s", e)
        if _plan.get("action") == "skip":
            out_skip = {
                "skipped": _plan.get("skipped")
                or "正文已在,跳过生成(advisory 稿手动采纳后走此路)",
            }
            if _plan.get("advisories"):
                out_skip["advisories"] = list(_plan["advisories"])
            return out_skip
        # 生成路径：msg 已由 plan_draft_loop 组装（含 EC Bundle）
        req = LoopChapterReq(
            chapter=seq,
            focalizer=ch.get("focalizer") or "",
            msg=_plan.get("msg") or f"按简报与演绎写第{seq}章完整正文。",
        )
        return loop_chapter(req, work=work)   # 端点函数直调:互斥/journal/回炉/落库全复用


    return {"draft_loop": draft_loop}
