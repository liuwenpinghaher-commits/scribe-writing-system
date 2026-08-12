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


    return {"deduce": deduce}
