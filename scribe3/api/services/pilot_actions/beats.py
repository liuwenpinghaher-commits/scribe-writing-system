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
        """展开节拍：v2 GCD 行协议（旗控）+ 全字段接地 + synopsis fallback 旗 + beats_meta。

        - ``SCRIBE3_BEATS_V2``（默认开）：生成 goal/conflict/turn/cost/hook/text
        - 接地候选 = 全 GCD 字段拼接（非仅 text）
        - 接地失败：``SCRIBE3_BEATS_SYNOPSIS_FALLBACK``（默认开）→ 大纲切句；
          否则 park，不写 beats
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
        if ch.get("beats"):
            out = {"skipped": "节拍已有内容,按既有推进(不覆盖)"}
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
            except Exception:
                pass
            return out

        try:
            from scribe3.novel_quality_flags import (
                beats_synopsis_fallback_enabled,
                beats_v2_enabled,
            )
            use_v2 = bool(beats_v2_enabled())
            use_synopsis_fb = bool(beats_synopsis_fallback_enabled())
        except Exception:
            use_v2 = True
            use_synopsis_fb = True

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

        def _v2_prompt(*, strict: bool = False) -> str:
            base = (
                f"据本章大纲展开戏剧节拍（beats.v2）：输出 4–7 行，每行严格用管道分隔，"
                f"字段顺序固定为：\n"
                f"KIND|目标|冲突|结果|代价|钩子|摘要|密度|预算\n"
                f"KIND 仅用 scene 或 bridge；目标=POV场景级欲望；冲突=阻力；"
                f"结果=转折/灾难；代价=不可逆或损失；钩子=读者悬念（可空）；"
                f"摘要=一句叙事；密度=密或疏；预算=整数可空。\n"
                f"最后可另起一行：CHAPTER_HOOK|章末钩子全文\n"
                f"禁止散文段落；禁止新增大纲没有的人物/物件/规则/不可逆设定。\n"
                f"只输出上述行，不要 Markdown。\n大纲:\n{synopsis}"
            )
            if strict:
                base = (
                    "【重试·严格】必须逐行 KIND|目标|冲突|结果|代价|钩子|摘要|密度|预算，"
                    "禁止散文段落与编号说明。\n"
                ) + base
            return base

        def _v1_prompt() -> str:
            return (
                f"据本章大纲展开节拍:4-7条,每条一行一个动作/转折,"
                f"不写成正文。只输出节拍行,每行一条。"
                f"禁止新增大纲没有的人物/物件/规则。\n大纲:{synopsis}"
            )

        def _gen_and_parse(*, strict: bool = False) -> tuple[list[dict], str, str]:
            """返回 (beats, chapter_hook, schema_tag) schema_tag ∈ v2|v1。"""
            # 显式经模块取名：_pilot_executor rebind 后嵌套函数 globals=app_impl，
            # 直接写 parse_beats_v2_output 会 NameError。
            import scribe3.api.services.pilot_runtime as _pr
            if use_v2:
                raw = _pilot_llm_gen(st, work, seq, "plan", _v2_prompt(strict=strict))
                beats, hook = _pr.parse_beats_v2_output(raw)
                # 若无任何 GCD 字段，视为 parse 弱失败 → 可被重试；仍保留 text 行
                has_gcd = any(
                    str(b.get("goal") or b.get("conflict") or b.get("turn") or "").strip()
                    for b in beats if isinstance(b, dict)
                )
                if beats and has_gcd:
                    return beats, hook, "v2"
                if beats and not has_gcd:
                    # 模型回落成纯文本行
                    return beats, hook, "v1"
                return [], "", "v2"
            raw = _pilot_llm_gen(st, work, seq, "plan", _v1_prompt())
            return _pr.parse_beats_v1_lines(raw), "", "v1"

        beats, chapter_hook, schema_tag = _gen_and_parse(strict=False)
        if not beats:
            # parse 失败 → 严格重试 1 次
            beats, chapter_hook, schema_tag = _gen_and_parse(strict=True)

        if not beats:
            return {
                "pilot_park": "节拍解析失败:模型未产出可用节拍行，请修订后再推进",
                "grounding": {"ok": False, "issues": [{"claim": "", "reason": "parse_empty", "evidence": ""}]},
                "candidate_beats": [],
            }

        import scribe3.api.services.pilot_runtime as _pr
        candidate = _pr.grounding_candidate_from_beats(beats)
        review = _grounding_review(
            source, candidate, mode="beats",
            st=st, work=work, chapter=seq,
        )
        if not review.get("ok"):
            # ground 失败 → 重生+重审 1 次
            beats2, hook2, schema2 = _gen_and_parse(strict=True)
            if beats2:
                cand2 = _pr.grounding_candidate_from_beats(beats2)
                review2 = _grounding_review(
                    source, cand2, mode="beats",
                    st=st, work=work, chapter=seq,
                )
                if review2.get("ok"):
                    beats, chapter_hook, schema_tag, review = beats2, hook2, schema2, review2
                else:
                    review = review2
                    beats, chapter_hook, schema_tag = beats2, hook2, schema2

        if not review.get("ok"):
            log = logging.getLogger("scribe3")
            if use_synopsis_fb:
                fb = _pr._beats_from_synopsis_segments(synopsis)
                if len(fb) >= 2:
                    bmeta = _pr._compose_beats_meta(
                        fb,
                        schema="v1",
                        beats_source="synopsis_segments",
                        chapter_hook="",
                        synopsis=synopsis,
                        chapter_pressure=chapter_pressure,
                        role=role,
                    )
                    # 先落库再门检：advisory drama gate **不**擦 beats
                    st.update_chapter_meta(seq, {"beats": fb, "beats_meta": bmeta})
                    log.info(
                        "expand_beats synopsis-segment fallback work=%s seq=%s n=%s "
                        "beats_source=synopsis_segments drama_ok=%s",
                        work, seq, len(fb),
                        (bmeta.get("drama_validation") or {}).get("ok"),
                    )
                    out_fb = {
                        "beats": fb,
                        "beats_meta": bmeta,
                        "grounding": {"ok": True, "fallback": "synopsis_segments"},
                        "llm_rejected": review,
                        "pdc": {"ok": None, "note": "pdc_missing_after_fallback"},
                    }
                    dpark = _pr._drama_gate_park_if_needed(bmeta)
                    if dpark:
                        log.info(
                            "expand_beats drama_gate park(fallback) work=%s seq=%s",
                            work, seq,
                        )
                        return {**out_fb, **dpark}
                    return out_fb
            return {
                "pilot_park": "事实对齐失败:节拍含无来源主张，请修订后再推进",
                "grounding": review,
                "candidate_beats": beats,
            }

        # 接地通过：写 beats + beats_meta；可选 DRAMA_GATE advisory park
        if schema_tag == "v2":
            beats_source = "llm_v2"
            schema = "v2"
        else:
            beats_source = "llm_v1"
            schema = "v1"
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
