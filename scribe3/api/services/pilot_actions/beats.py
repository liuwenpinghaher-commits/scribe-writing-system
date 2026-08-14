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

    def _pdc_gate_park_if_needed(st, seq) -> dict | None:
        """SCRIBE3_PDC_GATE=1 时：仅 ok=False（完整非法合同）→ pilot_park；ok=None 不 park。"""
        try:
            from scribe3.pressure_drive import load_pdc, pdc_gate_enabled, validate_pdc
            if not pdc_gate_enabled():
                return None
            ch = st.get_chapter(seq) or {}
            contract = load_pdc(ch)
            if contract is None:
                return None  # ok=None
            n_beats = len(ch.get("beats") or []) if isinstance(ch.get("beats"), list) else None
            v = validate_pdc(contract, chapter_beats_count=n_beats)
            if v.get("ok") is False:
                errs = "；".join((v.get("errors") or [])[:3]) or "压力合同结构非法"
                return {
                    "pilot_park": f"压力合同未通过校验：{errs}。请修订 pressure_drive 后再推进。",
                    "pdc": {"ok": False, "errors": v.get("errors")},
                }
            return None
        except Exception as e:
            logging.getLogger("scribe3").warning(
                "pdc_gate check fail-soft work=%s seq=%s: %s", work, seq, e)
            return None

    def _try_bootstrap_pdc(st, seq, synopsis: str, beats: list) -> dict:
        """确定性轻量 bootstrap：从大纲压力级/role 与节拍文生成合同。

        失败或缺核心字段 → 不写 present 合同（ok=None）。
        完整合法 → 写 pressure_drive。力学永不进 grounding 源。
        """
        try:
            from scribe3.brief import parse_chapter_meta
            from scribe3.pressure_drive import (
                bootstrap_pdc_from_texts,
                first_ok_bootstrap_evidence,
                pdc_flag_enabled,
                template_bootstrap_evidence,
                validate_pdc,
            )
            if not pdc_flag_enabled():
                return {"ok": None, "note": "SCRIBE3_PDC off"}
            meta = parse_chapter_meta(synopsis or "") or {}
            try:
                cp = int(meta.get("pressure") or 4)
            except (TypeError, ValueError):
                cp = 4
            role = str(meta.get("role") or "推进")
            texts = [
                str(b.get("text") or "") for b in (beats or []) if isinstance(b, dict)
            ]
            # 确定性：fork 仍用 synopsis 种子；evidence 优先 beat cost→turn→hook
            seed = (synopsis or "").strip().replace("\n", "")[:40]
            fork = f"推进或收束本章核心：{seed[:24]}" if seed else "推进本章核心抉择"
            evidence = first_ok_bootstrap_evidence(
                beats,
                template_fallback=template_bootstrap_evidence(synopsis or ""),
                synopsis=synopsis or "",
            )
            # cost_steps：有 evidence_ok 的 beat.cost 则作阶梯种子
            beat_costs = [
                str(b.get("cost") or "").strip()
                for b in (beats or [])
                if isinstance(b, dict) and str(b.get("cost") or "").strip()
            ]
            contract = bootstrap_pdc_from_texts(
                synopsis=synopsis or "",
                beat_texts=texts,
                chapter_beats=beats if isinstance(beats, list) else None,
                chapter_pressure=cp,
                role=role,
                fork_choice=fork,
                evidence=evidence,
                irreversible_action="留下痕迹",
                cost_steps=beat_costs[:3] if beat_costs else None,
            )
            if not contract:
                logging.getLogger("scribe3").info(
                    "pdc_bootstrap=degraded work=%s seq=%s reason=incomplete_core", work, seq)
                return {"ok": None, "note": "pdc_bootstrap_degraded"}
            v = validate_pdc(contract, chapter_beats_count=len(texts) or None)
            if v.get("ok") is not True:
                logging.getLogger("scribe3").info(
                    "pdc_bootstrap=degraded work=%s seq=%s errors=%s",
                    work, seq, v.get("errors"))
                return {"ok": None, "note": "pdc_bootstrap_invalid", "errors": v.get("errors")}
            st.update_chapter_meta(seq, {"pressure_drive": contract})
            return {"ok": True, "chapter_pressure": cp}
        except Exception as e:
            logging.getLogger("scribe3").warning(
                "pdc_bootstrap fail-soft work=%s seq=%s: %s", work, seq, e)
            return {"ok": None, "note": f"pdc_bootstrap_error:{e}"}

    def expand_beats(st, seq):
        """展开节拍：LLM 场面纸（每拍≥500）+ 接地；薄拍不 skip；禁止切句充数。

        - 仅当 iceberg 节拍地板已齐才 skip
        - 生成走 ``thicken_beats``（必须 LLM）
        - 接地失败：再 LLM 一次，仍失败 park，**不**写大纲切句
        - ``validate_drama_beats`` → ``beats_meta.drama_validation``（含 ``gaps``）
        - ``SCRIBE3_DRAMA_GATE=1``（默认关）：高压章且 ok=False → ``pilot_park``
          ``drama_incomplete`` advisory（可补字段继续；**不**擦 beats）
        - ``SCRIBE3_NARRATIVE_ENGINE=1``：无论是否 skip 都 ensure narrative_drive（引导优先，默认不硬 park）
        """
        # 叙事引擎：skip 分支也须 ensure（设计 KD-NE-2 / expand 含 skip）
        _nd_drive = None
        try:
            from scribe3.novel_quality_flags import narrative_engine_enabled
            if narrative_engine_enabled():
                from scribe3.narrative_drive import ensure_narrative_drive
                _steer_nd = _pilot_steer(st, seq) or ""
                _nd_drive = ensure_narrative_drive(st, seq, steer=_steer_nd)
        except Exception as e:
            logging.getLogger("scribe3").warning(
                "expand_beats ensure_narrative_drive fail-soft: %s", e)
            _nd_drive = None

        ch = st.get_chapter(seq) or {}
        from scribe3.stage_generate import iceberg_ok_for
        if iceberg_ok_for(ch, "beats"):
            out = {"skipped": "节拍已达覆盖地板,按既有推进(不覆盖)"}
            if _nd_drive is not None:
                out["narrative_drive"] = _nd_drive
            # 可选 GATE：默认关；仅作者显式开时高压 invalid 才 park
            try:
                from scribe3.novel_quality_flags import event_drive_gate_enabled
                if event_drive_gate_enabled() and _nd_drive:
                    val = (_nd_drive.get("validation") or {})
                    if val.get("ok") is False:
                        from scribe3.narrative_drive import format_narrative_park
                        out["pilot_park"] = format_narrative_park(_nd_drive)
            except Exception as _sf_e:
                from scribe3.soft_fail import soft_fail
                import logging as _sf_logging
                soft_fail('beats_soft_1', _sf_e, logger='scribe3', level=_sf_logging.DEBUG)
            return out

        synopsis = (ch.get("synopsis") or "").strip()
        try:
            from scribe3.brief import parse_chapter_meta
            _meta = parse_chapter_meta(synopsis) or {}
        except Exception:
            _meta = {}
        try:
            chapter_pressure = int(_meta.get("pressure") or 4)
        except (TypeError, ValueError):
            chapter_pressure = 4
        role = str(_meta.get("role") or "推进")

        source = synopsis
        steer = _pilot_steer(st, seq)
        if steer:
            source += "\n\n作者意图:\n" + steer

        from scribe3.stage_generate import STAGE_MAX_TOKENS, thicken_beats

        def llm_fn(prompt, max_tokens=STAGE_MAX_TOKENS["beats"]):
            return _pilot_llm_gen(
                st, work, seq, "beats", prompt, max_tokens=max_tokens,
            )

        thick = thicken_beats(
            ch,
            llm_fn=llm_fn,
            persist_fn=None,
            seq=seq,
            extra=("作者意图:\n" + steer) if steer else "",
            st=st, work=work, focalizer="",
        )
        if thick.get("skipped"):
            return thick
        if not thick.get("ok"):
            return {
                "pilot_park": thick.get("message") or "节拍 LLM 未达覆盖地板",
                "grounding": {"ok": False, "issues": [{"claim": "", "reason": "llm_thin", "evidence": ""}]},
                "candidate_beats": (thick.get("parsed") or {}).get("beats") or [],
                **{k: v for k, v in thick.items() if k != "parsed"},
            }
        beats = list(thick.get("beats") or [])
        chapter_hook = ""
        schema_tag = "llm_scene"

        import scribe3.api.services.pilot_runtime as _pr
        candidate = _pr.grounding_candidate_from_beats(beats)
        review = _grounding_review(
            source, candidate, mode="beats",
            st=st, work=work, chapter=seq,
        )
        if not review.get("ok"):
            # 接地失败只允许再走一次 LLM，禁止大纲切句充数
            thick2 = thicken_beats(
                ch,
                llm_fn=llm_fn,
                persist_fn=None,
                seq=seq,
                extra="【重试】禁止新增大纲没有的人物/物件/规则。只写场面纸。",
                st=st, work=work, focalizer="",
            )
            if thick2.get("ok") and thick2.get("beats"):
                cand2 = _pr.grounding_candidate_from_beats(thick2["beats"])
                review2 = _grounding_review(
                    source, cand2, mode="beats",
                    st=st, work=work, chapter=seq,
                )
                if review2.get("ok"):
                    beats, review = list(thick2["beats"]), review2
                else:
                    review = review2
                    beats = list(thick2["beats"])

        if not review.get("ok"):
            return {
                "pilot_park": "事实对齐失败:节拍含无来源主张，请修订后再推进（不切句充数）",
                "grounding": review,
                "candidate_beats": beats,
            }

        # 接地通过：写 beats + beats_meta；可选 DRAMA_GATE advisory park
        beats_source = "llm"
        schema = "v2" if any(
            str(b.get("goal") or b.get("conflict") or "").strip()
            for b in beats if isinstance(b, dict)
        ) else "v1"
        if chapter_hook and beats and not str(beats[-1].get("hook") or "").strip():
            beats[-1]["hook"] = chapter_hook

        bmeta = _pr._compose_beats_meta(
            beats,
            schema=schema,
            beats_source=beats_source,
            chapter_hook=chapter_hook,
            synopsis=synopsis,
            chapter_pressure=chapter_pressure,
            role=role,
        )
        st.update_chapter_meta(seq, {"beats": beats, "beats_meta": bmeta})
        logging.getLogger("scribe3").info(
            "expand_beats ok work=%s seq=%s n=%s beats_source=%s drama_ok=%s",
            work, seq, len(beats), beats_source,
            (bmeta.get("drama_validation") or {}).get("ok"),
        )

        pdc_meta = _try_bootstrap_pdc(st, seq, synopsis, beats)
        out = {
            "beats": beats,
            "beats_meta": bmeta,
            "grounding": review,
            "pdc": pdc_meta,
        }
        # 戏剧门优先于 PDC 门：缺口清单对人补节拍更直接
        dpark = _pr._drama_gate_park_if_needed(bmeta)
        if dpark:
            logging.getLogger("scribe3").info(
                "expand_beats drama_gate park work=%s seq=%s gaps=%s",
                work, seq,
                ((bmeta.get("drama_validation") or {}).get("gaps") or {}).get("lines"),
            )
            return {**out, **dpark}
        park = _pdc_gate_park_if_needed(st, seq)
        if park:
            return {**out, **park}
        return out


    return {"expand_beats": expand_beats}
