"""Pilot action bodies extracted from pilot_runtime (P1-16)."""
from __future__ import annotations

def build_pilot_executor_body(work: str) -> dict:

    from scribe3.api.services import pilot_runtime as pr
    # re-export helpers used as free vars in nested actions into this frame
    g = globals()
    for name in dir(pr):
        if name.startswith("__"):
            continue
        g[name] = getattr(pr, name)
    import json, os, logging
    """action → callable(st, seq)。全部落库走 update_chapter_meta 白名单/既有端点函数。"""
    def propose_outline(st, seq):
        ch0 = st.get_chapter(seq) or {}
        if (ch0.get("synopsis") or "").strip():
            # 审查 P1-2:字段已有内容(可能人工编辑)——跳步推进,绝不覆盖;
            # 想重新提案:清空大纲或走未来 revise 通道。
            return {"skipped": "大纲已有内容,按既有推进(不覆盖)"}
        steer = _pilot_steer(st, seq)
        out = _pilot_llm_gen(st, work, seq, "plan",
                             f"给第{seq}章出大纲提案:3-5句,写清这章发生什么。"
                             f"并在正文后单独标注以下标签行（全角或半角冒号均可，勿省略）:\n"
                             f"压力级:N  （N=1-5，本章戏剧压力）\n"
                             f"chapter_role:高压|推进|修炼|关系回收|低压|信息整理\n"
                             f"stakes:若失败，…  （一句：POV 若失败会失去什么/不可逆代价）\n"
                             f"章末钩子:…  （一句：追读拉力，信息差或未兑现威胁）\n"
                             f"只输出大纲正文与上述标签，不要解释。"
                             + (f"\n作者意图(最高优先):{steer}" if steer else ""))
        st.update_chapter_meta(seq, {"synopsis": out})
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

    def deduce(st, seq):
        from scribe3.deduce_helpers import (
            infer_involved_candidates,
            is_stale_deduction,
            missing_roles,
            normalize_involved,
            normalize_role_id,
            pilot_deduce_observation,
            stamp_deduction,
            truth_revision,
        )
        ch = st.get_chapter(seq) or {}
        have_truth = bool((ch.get("scene_truth") or "").strip())
        involved = normalize_involved(ch.get("involved_characters") or [])
        inferred_involved: list[str] = []
        involved_written = False
        if not involved:
            # D10: 与前端一致——只内存推断，不静默 patch involved_characters
            text = (ch.get("synopsis") or "") + " " + " ".join(
                (b.get("text") if isinstance(b, dict) else str(b)) or "" for b in ch.get("beats") or [])
            inferred_involved = infer_involved_candidates(text, st.characters(), limit=4)
            involved = list(inferred_involved)
        # R1-2:真相已有则复用;投影按 normalize 后 character_id merge 只补缺失(有 prose 的不覆盖)。
        # 禁止「有真相 + 有任意 deductions」整步 skip——否则 1/3 投影时永远补不齐。
        if have_truth:
            truth = (ch.get("scene_truth") or "").strip()
        else:
            syn0 = (ch.get("synopsis") or "").strip()
            truth = ""
            try:
                truth = _pilot_llm_gen(st, work, seq, "deduce",
                                       f"写第{seq}章这一场的「场景真相」:全知冷叙,客观上真正发生了什么。"
                                       f"只能使用大纲已有信息,禁止新增人物/物件/规则。"
                                       f"只输出真相正文。\n大纲:{syn0}")
            except Exception as e:
                logging.getLogger("scribe3").warning(
                    "scene_truth LLM fail work=%s seq=%s: %s", work, seq, e)
                truth = ""
            # 真相须钉回大纲；LLM 失败或未过接地 → 用大纲作真相（零幻觉）
            if truth.strip():
                gr_t = _grounding_review(syn0, truth, mode="beats", st=st, work=work, chapter=seq)
                if not gr_t.get("ok") and syn0:
                    logging.getLogger("scribe3").info(
                        "scene_truth fall back to synopsis work=%s seq=%s", work, seq)
                    truth = syn0
            elif syn0:
                logging.getLogger("scribe3").info(
                    "scene_truth LLM empty/fail → synopsis work=%s seq=%s", work, seq)
                truth = syn0
            else:
                return pilot_deduce_observation(
                    park="场景真相生成失败且无大纲可回退",
                    made=0, missing=[], stale=[], truth_revision=0,
                    scene_truth_chars=0, deductions_count=0,
                    inferred_involved=inferred_involved,
                    involved_written=involved_written,
                )
            st.update_chapter_meta(seq, {"scene_truth": truth})
            ch = st.get_chapter(seq) or ch
        # 刷新 ch 以拿最新 deductions / rev
        ch = st.get_chapter(seq) or ch
        rev = truth_revision(ch)
        existing = {}
        for d in (ch.get("deductions") or []):
            if not isinstance(d, dict):
                continue
            key = normalize_role_id(d.get("character_id") or d.get("character") or d.get("role"))
            if key and (d.get("prose") or "").strip():
                existing[key] = d
        deds = list(ch.get("deductions") or [])
        made = 0
        try:
            from scribe3.api.services.prompt_blocks import _verbatim_deduction_fallback
        except Exception:
            _verbatim_deduction_fallback = None

        for cid in involved:
            key = normalize_role_id(cid)
            if key in existing:
                continue   # 该角色投影已有(可能作者手编)——不覆盖
            name = key.split(":", 1)[-1] if key else str(cid).split(":")[-1]
            prose = ""
            try:
                prose = _pilot_llm_gen(
                    st, work, seq, "deduce",
                    f"以「{name}」截至第{seq}章的限知,写该角色这一场的限知投影,分五个小标题:"
                    f"看到/听到、知道、以为(误读)、做了/说了、没察觉的;每个小标题用 ### 起行。"
                    f"只含该角色所知所感。严格遵循角色档案已有的称谓和代词;档案未给出时只用角色姓名,不能臆造性别。"
                    f"不得新增场景真相中不存在的人物、物件、动作、时间、物理现象或人物前史;信息不足时明确留白。"
                    f"能逐字摘录场景真相的句子优先。", focalizer=key or str(cid))
            except Exception as e:
                logging.getLogger("scribe3").warning(
                    "deduction LLM fail work=%s seq=%s role=%s: %s", work, seq, name, e)
                prose = ""
            review = _grounding_review(
                truth, prose, mode="deduction", st=st, work=work, chapter=seq,
            ) if (prose or "").strip() else {"ok": False, "reason": "empty_or_llm_fail"}
            if not review.get("ok"):
                # 产品最优：可逐字追溯的投影兜底（与 grounded-fallback 同源），禁止编造
                fb = _verbatim_deduction_fallback(truth, key or str(cid)) if _verbatim_deduction_fallback else ""
                if fb and fb.strip():
                    prose = fb.strip()
                    review = _grounding_review(
                        truth, prose, mode="deduction", st=st, work=work, chapter=seq,
                    )
                    logging.getLogger("scribe3").info(
                        "deduction verbatim fallback work=%s seq=%s role=%s ok=%s",
                        work, seq, name, review.get("ok"))
                if not review.get("ok"):
                    # 仍失败：用「未能确认」五栏占位（仅当角色名出现在真相中），否则 park
                    blank = "未能从场景真相确认。"
                    if name and name in (truth or ""):
                        from scribe3.deduce_helpers import DEDUCTION_HEADINGS
                        prose = "\n\n".join(
                            f"### {h}\n{blank}" for h in DEDUCTION_HEADINGS)
                        review = {"ok": True, "fallback": "blank_five_panels"}
                        logging.getLogger("scribe3").info(
                            "deduction blank panels work=%s seq=%s role=%s", work, seq, name)
                    else:
                        obs = pilot_deduce_observation(
                            park=f"事实对齐失败:{name}的限知投影含无来源主张，请修订后再推进",
                            made=made, missing=missing_roles(involved, deds),
                            stale=[], truth_revision=rev, scene_truth_chars=len(truth),
                            deductions_count=len(deds),
                            inferred_involved=inferred_involved,
                            involved_written=involved_written,
                        )
                        return {**obs, "grounding": review, "character_id": key or str(cid),
                                "candidate": prose}
            deds.append(stamp_deduction(
                {"character_id": key or str(cid), "character_name": name, "prose": prose},
                rev,
            ))
            made += 1
            existing[key] = deds[-1]
        if made:
            st.update_chapter_meta(seq, {"deductions": deds})
            ch = st.get_chapter(seq) or ch
        # 全部已有 prose 且真相已有 → 结构化 skip(仍报告 stale)
        miss = missing_roles(involved, ch.get("deductions"))
        stale = [
            normalize_role_id(d.get("character_id"))
            for d in (ch.get("deductions") or [])
            if isinstance(d, dict) and is_stale_deduction(d, truth_revision(ch))
        ]
        stale = [s for s in stale if s]
        final_ch = st.get_chapter(seq) or ch
        n_deds = len(final_ch.get("deductions") or [])
        if not made and have_truth and not miss:
            return pilot_deduce_observation(
                skipped="演绎已有内容,按既有推进(不覆盖)",
                made=0, missing=miss, stale=stale,
                truth_revision=truth_revision(final_ch),
                scene_truth_chars=len(truth),
                deductions_count=n_deds,
                inferred_involved=inferred_involved,
                involved_written=involved_written,
            )
        return pilot_deduce_observation(
            made=made, missing=miss, stale=stale,
            truth_revision=truth_revision(final_ch),
            scene_truth_chars=len(truth),
            deductions_count=n_deds,
            inferred_involved=inferred_involved,
            involved_written=involved_written,
        )

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
                st._execute_write(
                    "UPDATE type::record('chapter',$seq) SET prose=$p, draft=$p, qc_word_count=0",
                    {"seq": seq, "p": ""},
                )
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

    def full_check(st, seq):
        ch = st.get_chapter(seq) or {}
        prose = (ch.get("prose") or "").strip()
        if not prose:
            return {"pilot_park": "正文为空,无从体检(上游未交稿——若在等 advisory 裁决请先处理)"}
        # OI-5/6 + H2 EVENT_LED：soft 日志 only（永不 park / 永不进 S1）
        _drive = ch.get("narrative_drive") if isinstance(ch.get("narrative_drive"), dict) else {}
        try:
            from scribe3.narrative_drive import (
                maybe_event_led_detect,
                maybe_log_metaphor_soft,
                maybe_log_opener_soft_trace,
            )
            maybe_log_opener_soft_trace(prose, _drive, seq=seq)
            maybe_log_metaphor_soft(prose, seq=seq)
            _eld = maybe_event_led_detect(prose, _drive, seq=seq)
            if _eld is not None:
                # 暂存，下方与 soft_fulfill 一并 merge pilot_card
                ch["_event_led_detect_tmp"] = _eld
        except Exception as e:
            logging.getLogger("scribe3").debug("soft narrative traces fail-soft: %s", e)
        # EC-2：soft_fulfill advisory + merge pilot_card（永不 blocking）
        try:
            from scribe3.novel_quality_flags import (
                drive_prose_drift_enabled,
                soft_fulfill_enabled,
            )
            from scribe3.execution_contract import (
                drive_prose_drift,
                merge_pilot_card,
                soft_fulfill_drive,
                summarize_soft_fulfill,
            )
            _patch: dict = {}
            _eld_card = ch.pop("_event_led_detect_tmp", None) if isinstance(ch, dict) else None
            if isinstance(_eld_card, dict):
                _patch["event_led_detect"] = {
                    "ok_soft": _eld_card.get("ok_soft"),
                    "gaps": list(_eld_card.get("gaps") or [])[:12],
                    "hits": list(_eld_card.get("hits") or [])[:12],
                    "note": _eld_card.get("note"),
                    "severity": "advisory",
                }
            if soft_fulfill_enabled():
                _ful = soft_fulfill_drive(prose, _drive)
                logging.getLogger("scribe3").info(
                    "soft_fulfill work=%s seq=%s ok_soft=%s gaps=%s quotes=%s cn=%s",
                    work, seq, _ful.get("ok_soft"), _ful.get("gaps"),
                    _ful.get("quotes"), _ful.get("prose_cn"),
                )
                _patch["soft_fulfill"] = summarize_soft_fulfill(_ful)
                # 写后 stamp：记录 drive/prose 指纹（不 clear）
                try:
                    from scribe3.execution_contract import attach_execution_stamp
                    _stamped = attach_execution_stamp(_drive, prose)
                    st.update_chapter_meta(seq, {"narrative_drive": _stamped})
                    _drive = _stamped
                except Exception as e_st:
                    logging.getLogger("scribe3").debug("execution_stamp fail-soft: %s", e_st)
            if drive_prose_drift_enabled():
                _dr = drive_prose_drift(_drive, prose)
                if _dr.get("drift"):
                    _patch["execution"] = {
                        "drift": True,
                        "reason": _dr.get("reason"),
                        "advisory": _dr.get("advisory"),
                    }
            if _patch:
                merge_pilot_card(st, seq, _patch)
        except Exception as e:
            logging.getLogger("scribe3").debug("soft_fulfill/drift fail-soft: %s", e)
        resp = post_check(PostCheckReq(prose=prose, focalizer=ch.get("focalizer") or ""),
                          seq=seq, work=work)
        # 审查 P1-7:体检结果必须被消费——blocking 停靠,不再"烧一遍然后扔"
        from scribe3.loop import bucket_counts_from_triage, triage
        t = triage(resp)
        # PR-6c: triage buckets 计数随 full_check 产物暂存，deliver 写进 pilot_card
        _bcounts = bucket_counts_from_triage(t)
        if _bcounts is not None:
            resp["_triage_bucket_counts"] = _bcounts

        def _stage_bucket_counts(counts: dict | None) -> None:
            """把 redline/story/style 计数 merge 进 pilot_card（保留 soft_fulfill 等键）。"""
            if not counts:
                return
            try:
                from scribe3.execution_contract import merge_pilot_card
                merge_pilot_card(st, seq, {"buckets": counts})
            except Exception as e:
                logging.getLogger("scribe3").warning(
                    "pilot full_check stage buckets 失败(忽略): %s", e)

        if t["verdict"] == "blocking":
            blocking = t.get("blocking") or []
            dets = sorted({b.get("detector") or "?" for b in blocking})
            # pilot 连载软通过集合（PR-6b · KD-NQ-11）：按双旗动态构建——
            # SOFT_PRESSURE → pressure_metrics/park_stroll；SOFT_AI_GRADE → aggregate_ai_grade。
            # 代码默认双开=现网可达；质量模式关 SOFT_PRESSURE 后压力类可硬停。
            # 限知泄露/退化 S1 等永不 soft；软项记入 quality_warn 供账本。
            from scribe3.novel_quality_flags import (
                LEGACY_SOFT_PASS_KIND,
                LEGACY_SOFT_PASS_LOG_MSG,
                LOG_FIELD_SOFT_AI,
                LOG_FIELD_SOFT_P,
                LOG_FIELD_SOFT_PASS,
                full_check_blocking_is_only_soft,
                full_check_soft_detectors,
                soft_pass_category_flags,
            )
            _soft_dets = full_check_soft_detectors()
            only_soft = full_check_blocking_is_only_soft(blocking, _soft_dets)
            if only_soft:
                cats = soft_pass_category_flags(blocking)
                resp["_triage_verdict"] = "advisory"
                resp["_pilot_quality_warn"] = {
                    "kind": LEGACY_SOFT_PASS_KIND,
                    LOG_FIELD_SOFT_PASS: True,
                    "detectors": dets,
                    LOG_FIELD_SOFT_P: cats[LOG_FIELD_SOFT_P],
                    LOG_FIELD_SOFT_AI: cats[LOG_FIELD_SOFT_AI],
                    "note": (
                        "pilot full_check: 当前 soft 旗下 detector 不硬停，"
                        "仍须交付后读感/质量线把关"
                    ),
                }
                logging.getLogger("scribe3").warning(
                    "%s work=%s seq=%s dets=%s soft_p=%s soft_ai=%s",
                    LEGACY_SOFT_PASS_LOG_MSG,
                    work, seq, dets,
                    cats[LOG_FIELD_SOFT_P], cats[LOG_FIELD_SOFT_AI],
                )
                _stage_bucket_counts(_bcounts)
                return resp
            return {"pilot_park": f"全量体检 blocking({'、'.join(dets)}),请处理后继续",
                    "post_check": resp}
        resp["_triage_verdict"] = t["verdict"]
        _stage_bucket_counts(_bcounts)
        return resp

    def deliver(st, seq):
        ch = st.get_chapter(seq) or {}
        prose = ch.get("prose") or ""
        if not prose.strip():
            return {"pilot_park": "空正文不可交付(审查 P0-1 独立防御)"}
        # 交付卡:低置信段=主编自审(置信度校准,调研:主动暴露不确定处)
        low_conf = ""
        try:
            low_conf = _pilot_llm_gen(
                st, work, seq, "final",
                f"你刚交付第{seq}章。列出你拿不准的地方(≤3处,每处引原文短语+一句为什么拿不准);"
                f"没有就回「无」。只输出清单。\n正文:\n{prose[:3000]}", max_tokens=400)
        except Exception as e:
            low_conf = f"(自审未跑成:{str(e)[:60]})"
        try:
            st.add_chapter_version(seq, prose, label=f"pilot交付", kind="checkpoint",
                                   stage="final", stats=_prose_stats(prose))
        except Exception as e:
            logging.getLogger("scribe3").warning("pilot 交付留版失败(忽略): %s", e)
        _qrows = st._query(
            "SELECT qc_issues, pilot_card FROM type::record('chapter',$seq)",
            {"seq": seq})
        _row0 = _qrows[0] if _qrows else {}
        _qc = _row0.get("qc_issues")
        _qn = len(_qc) if isinstance(_qc, list) else (_qc or 0)
        _prom = []
        try:
            for pr in st.promises_with_lifecycle(max_chapter=seq):
                if pr.get("setup_chapter") == seq:
                    _prom.append(f"埋「{(pr.get('text') or '')[:20]}」")
                if pr.get("payoff_chapter") == seq:
                    _prom.append(f"收「{(pr.get('text') or '')[:20]}」")
        except Exception:
            pass
        card = {"seq": seq, "words": len("".join(prose.split())),
                "qc": _qn, "promises": _prom, "low_confidence": low_conf}
        # PR-6c · KD-NQ-7：deliver 卡带 redline/story/style 三项计数
        # 优先 full_check 暂存；否则 fail-soft 再跑 post_check+triage（不阻断交付）
        from scribe3.loop import (
            bucket_counts_from_triage,
            normalize_bucket_counts,
            triage as _triage_for_card,
        )
        _buckets = None
        _prev_card: dict = {}
        try:
            _prev_card = json.loads(_row0.get("pilot_card") or "{}")
            if not isinstance(_prev_card, dict):
                _prev_card = {}
            if isinstance(_prev_card.get("buckets"), dict):
                _buckets = normalize_bucket_counts(_prev_card["buckets"])
        except Exception:
            _prev_card = {}
        if _buckets is None:
            try:
                _pc = post_check(
                    PostCheckReq(prose=prose, focalizer=ch.get("focalizer") or ""),
                    seq=seq, work=work)
                _buckets = bucket_counts_from_triage(_triage_for_card(_pc))
            except Exception as e:
                logging.getLogger("scribe3").warning(
                    "pilot deliver triage buckets 失败(忽略): %s", e)
        if _buckets is not None:
            card["buckets"] = _buckets
        # R3：structure advisory（不改变 craft finalize）
        try:
            from scribe3.structure_style import evaluate_structure_style
            _ss = evaluate_structure_style(prose or "")
            card["structure_advisory"] = {
                "ending_formula_hit": bool(_ss.get("ending_formula_hit")),
                "isomorphism_hit": bool(_ss.get("isomorphism_hit")),
                "simile_like_per_1k": _ss.get("simile_like_per_1k"),
                "severity": "advisory",
            }
            _hits = sum(1 for k in ("ending_formula_hit", "isomorphism_hit") if _ss.get(k))
            try:
                if float(_ss.get("simile_like_per_1k") or 0) >= 8:
                    _hits += 1
            except Exception:
                pass
            if _hits and isinstance(card.get("buckets"), dict):
                card["buckets"]["style"] = int(card["buckets"].get("style") or 0) + _hits
            if _hits:
                card["structure_note"] = f"结构多样性 advisory {_hits} 项（非阻断）"
        except Exception as e:
            logging.getLogger("scribe3").debug(
                "pilot deliver structure_advisory fail-soft: %s", e)
        # EC：保留 soft_fulfill / execution 摘要键（merge，非整卡抹掉）
        for _k in ("soft_fulfill", "execution"):
            if isinstance(_prev_card.get(_k), dict):
                card[_k] = _prev_card[_k]
        st._execute_write("UPDATE type::record('chapter',$seq) SET pilot_card=$c",
                          {"seq": seq, "c": json.dumps(card, ensure_ascii=False)})
        return {"card": card}

    def finalize(st, seq):
        ch = st.get_chapter(seq) or {}
        prose = ch.get("prose") or ""
        # rev.1.2：写 kind=final 前强制 craft hard + 质控；stamp 单源 try_stamp_kind_final
        try:
            from scribe3.finalize_gate import check_persist_gates, try_stamp_kind_final
            foc = (ch.get("focalizer") or ch.get("pov") or "") or None
            _pg = check_persist_gates(
                st, int(seq), prose or "",
                focalizer=foc, danger_draft=False,
            )
            if not _pg.get("allowed"):
                return {
                    "finalized": False,
                    "error": _pg.get("code") or "persist_gate",
                    "detail": _pg.get("detail") or "",
                    "blocking": list(_pg.get("blocking") or []),
                    "gate": _pg,
                }
            _stamp = try_stamp_kind_final(
                st, int(seq), prose or "",
                label="pilot终选", stage="final", stats=_prose_stats(prose),
            )
            if not _stamp.get("allowed") or (
                not _stamp.get("stamped") and _stamp.get("code") == "craft_finalize"
            ):
                return {
                    "finalized": False,
                    "error": _stamp.get("code") or "craft_finalize",
                    "detail": _stamp.get("detail") or "",
                    "blocking": list(_stamp.get("blocking") or []),
                    "final_stamp": _stamp,
                }
        except Exception as e:
            logging.getLogger("scribe3").warning(
                "pilot finalize persist gates 失败(阻断) seq=%s: %s", seq, e,
            )
            return {
                "finalized": False,
                "error": "persist_gate_error",
                "detail": str(e)[:200],
                "blocking": [],
            }
        # v6.1 §5.2：定稿后强制全类型 PostFinalize（持久化候选；不自动 apply L1）
        post_finalize = None
        try:
            from scribe3.api.services.canon_hooks import body_confirmed_report
            complete_fn = None
            try:
                from scribe3.llm import hermes_complete
                complete_fn = lambda p: hermes_complete(
                    p, timeout=90.0, max_tokens=2000, retries_override=0)
            except Exception:
                complete_fn = None
            post_finalize = body_confirmed_report(
                work=work, seq=seq, prose=prose, st=st,
                complete_fn=complete_fn, persist=True,
            )
        except Exception as e:
            logging.getLogger("scribe3").warning(
                "post_finalize_report failed work=%s seq=%s: %s", work, seq, e)
            post_finalize = {
                "seq": seq,
                "error": str(e)[:200],
                "silent_l1_write": False,
                "sections": {
                    "l2_objective": {"items": [], "modules": [], "auto_applied": False},
                    "l1_requires_approval": {"items": [], "modules": [], "auto_applied": False},
                },
            }
        return {
            "finalized": True,
            "post_finalize_report": post_finalize,
            "canon_loop": {
                "path": "body_confirmed",
                "silent_l1_write": False,
                "next": "POST /canon/change-pack/apply with approved_item_ids for L1 items",
            },
        }

    return {"propose_outline": propose_outline, "expand_beats": expand_beats,
            "deduce": deduce, "draft_loop": draft_loop, "full_check": full_check,
            "deliver": deliver, "finalize": finalize}




