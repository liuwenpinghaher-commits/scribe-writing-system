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
                truth = _pilot_llm_gen(
                    st, work, seq, "deduce",
                    f"写第{seq}章这一场的「场景真相」:全知冷叙,客观上真正发生了什么。"
                    f"只能使用大纲已有信息,禁止新增人物/物件/规则。"
                    f"只输出真相正文。\n大纲:{syn0}",
                    max_tokens=2048,
                )
            except Exception as e:
                logging.getLogger("scribe3").warning(
                    "scene_truth LLM fail work=%s seq=%s: %s", work, seq, e)
                truth = ""
            # 真相必须 LLM 产出；禁止把大纲复制成真相
            if truth.strip():
                gr_t = _grounding_review(syn0, truth, mode="beats", st=st, work=work, chapter=seq)
                if not gr_t.get("ok"):
                    return pilot_deduce_observation(
                        park="场景真相 LLM 未过接地，禁止用大纲充数",
                        made=0, missing=[], stale=[], truth_revision=0,
                        scene_truth_chars=0, deductions_count=0,
                        inferred_involved=inferred_involved,
                        involved_written=involved_written,
                    )
            else:
                return pilot_deduce_observation(
                    park="场景真相 LLM 未产出，禁止用大纲回退",
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
        from scribe3.iceberg import cn_len
        from scribe3.stage_generate import iceberg_ok_for
        _ded_floor_ok = iceberg_ok_for(ch, "deduction")

        for cid in involved:
            key = normalize_role_id(cid)
            if key in existing:
                old_n = cn_len((existing[key] or {}).get("prose"))
                if _ded_floor_ok or old_n >= 400:
                    continue   # 已厚或作者手编够用——不覆盖
                # 薄投影且全章未达 5000：必须再走 LLM 加厚
            name = key.split(":", 1)[-1] if key else str(cid).split(":")[-1]
            prose = ""
            try:
                prose = _pilot_llm_gen(
                    st, work, seq, "deduce",
                    f"以「{name}」截至第{seq}章的限知,写该角色这一场的限知投影,分五个小标题:"
                    f"看到/听到、知道、以为(误读)、做了/说了、没察觉的;每个小标题用 ### 起行。"
                    f"只含该角色所知所感。严格遵循角色档案已有的称谓和代词;档案未给出时只用角色姓名,不能臆造性别。"
                    f"不得新增场景真相中不存在的人物、物件、动作、时间、物理现象或人物前史。"
                    f"禁止摘录充数、禁止「未能确认」占位。本篇须写厚（建议 ≥800 字）。",
                    focalizer=key or str(cid),
                    max_tokens=4096,
                )
            except Exception as e:
                logging.getLogger("scribe3").warning(
                    "deduction LLM fail work=%s seq=%s role=%s: %s", work, seq, name, e)
                prose = ""
            review = _grounding_review(
                truth, prose, mode="deduction", st=st, work=work, chapter=seq,
            ) if (prose or "").strip() else {"ok": False, "reason": "empty_or_llm_fail"}
            if not review.get("ok"):
                # 只允许再调一次 LLM；禁止摘录/空白五栏充数
                try:
                    prose = _pilot_llm_gen(
                        st, work, seq, "deduce",
                        f"【重试】以「{name}」限知重写五层投影，必须依据场景真相，禁止编造。"
                        f"每个小标题用 ### 起行。只输出投影。",
                        focalizer=key or str(cid),
                    )
                except Exception:
                    prose = ""
                review = _grounding_review(
                    truth, prose, mode="deduction", st=st, work=work, chapter=seq,
                ) if (prose or "").strip() else {"ok": False, "reason": "llm_retry_empty"}
                if not review.get("ok"):
                    obs = pilot_deduce_observation(
                        park=f"事实对齐失败:{name}的限知投影含无来源主张，禁止摘录/空白占位",
                        made=made, missing=missing_roles(involved, deds),
                        stale=[], truth_revision=rev, scene_truth_chars=len(truth),
                        deductions_count=len(deds),
                        inferred_involved=inferred_involved,
                        involved_written=involved_written,
                    )
                    return {**obs, "grounding": review, "character_id": key or str(cid),
                            "candidate": prose}
            stamped = stamp_deduction(
                {"character_id": key or str(cid), "character_name": name, "prose": prose},
                rev,
            )
            replaced = False
            for i, old in enumerate(deds):
                if isinstance(old, dict) and normalize_role_id(
                    old.get("character_id") or old.get("character") or old.get("role")
                ) == key:
                    deds[i] = stamped
                    replaced = True
                    break
            if not replaced:
                deds.append(stamped)
            made += 1
            existing[key] = stamped
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
                skipped="演绎已达覆盖地板,按既有推进(不覆盖)",
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
