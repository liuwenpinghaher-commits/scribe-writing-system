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

    def _merge_keep_author_deductions(existing, incoming):
        from scribe3.deduce_helpers import normalize_role_id
        by = {}
        order = []
        for d in list(existing or []):
            if not isinstance(d, dict):
                continue
            key = normalize_role_id(
                d.get("character_id") or d.get("character") or d.get("role")
            )
            if not key:
                continue
            if key not in by:
                order.append(key)
            by[key] = d
        for d in list(incoming or []):
            if not isinstance(d, dict):
                continue
            key = normalize_role_id(
                d.get("character_id") or d.get("character") or d.get("role")
            )
            if not key:
                continue
            old = by.get(key)
            if old and str(old.get("prose") or "").strip():
                continue
            if key not in by:
                order.append(key)
            by[key] = d
        return [by[k] for k in order]

    def _persist_deductions_gated(st, seq, fields, *, keep_truth=True):
        from scribe3.iceberg import persist_fields_blocked
        cur = st.get_chapter(seq) or {}
        out = {}
        if fields.get("scene_truth") and not (
            keep_truth and str(cur.get("scene_truth") or "").strip()
        ):
            out["scene_truth"] = fields["scene_truth"]
        if "deductions" in fields:
            merged = _merge_keep_author_deductions(
                cur.get("deductions"), fields.get("deductions"),
            )
            blocked = persist_fields_blocked({"deductions": merged})
            if blocked:
                return blocked
            out["deductions"] = merged
        if out:
            st.update_chapter_meta(seq, out)
        return None

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
        from scribe3.iceberg import persist_fields_blocked
        from scribe3.stage_generate import (
            STAGE_MAX_TOKENS,
            iceberg_ok_for,
            stage_ready,
            thicken_deduce,
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
        if iceberg_ok_for(ch, "deduction") and have_truth and not missing_roles(involved, ch.get("deductions")):
            return pilot_deduce_observation(
                skipped="演绎已达覆盖地板,按既有推进(不覆盖)",
                made=0, missing=[], stale=[],
                truth_revision=truth_revision(ch),
                scene_truth_chars=len(str(ch.get("scene_truth") or "")),
                deductions_count=len(ch.get("deductions") or []),
                inferred_involved=inferred_involved,
                involved_written=involved_written,
            )

        ch_work = dict(ch)
        if inferred_involved:
            ch_work["involved_characters"] = list(inferred_involved)
        ready = stage_ready(ch_work, "deduce")
        if ready.get("ok"):
            def llm_fn(prompt, max_tokens=STAGE_MAX_TOKENS["deduce"]):
                return _pilot_llm_gen(
                    st, work, seq, "deduce", prompt, max_tokens=max_tokens,
                )

            thick = thicken_deduce(
                ch_work,
                llm_fn=llm_fn,
                persist_fn=None,
                seq=seq,
                extra="",
                st=st, work=work, focalizer="",
            )
            if thick.get("skipped"):
                return thick
            if thick.get("ok"):
                blocked = _persist_deductions_gated(
                    st, seq,
                    {k: thick[k] for k in ("deductions", "scene_truth") if k in thick},
                )
                if blocked:
                    return pilot_deduce_observation(
                        park=blocked.get("message") or "演绎合计未达 5000，禁止把口号投影当已齐",
                        made=0, missing=missing_roles(involved, ch.get("deductions")),
                        stale=[], truth_revision=truth_revision(ch),
                        scene_truth_chars=len(str(ch.get("scene_truth") or "")),
                        deductions_count=len(ch.get("deductions") or []),
                        inferred_involved=inferred_involved,
                        involved_written=involved_written,
                    )
                final_ch = st.get_chapter(seq) or ch
                return pilot_deduce_observation(
                    made=len(thick.get("deductions") or []),
                    missing=missing_roles(involved, final_ch.get("deductions")),
                    stale=[],
                    truth_revision=truth_revision(final_ch),
                    scene_truth_chars=len(str(final_ch.get("scene_truth") or "")),
                    deductions_count=len(final_ch.get("deductions") or []),
                    inferred_involved=inferred_involved,
                    involved_written=involved_written,
                )
            if thick.get("code") != "stage_not_ready":
                return pilot_deduce_observation(
                    park=thick.get("message") or "演绎 LLM 未达覆盖地板",
                    made=0, missing=missing_roles(involved, ch.get("deductions")),
                    stale=[], truth_revision=truth_revision(ch),
                    scene_truth_chars=len(str(ch.get("scene_truth") or "")),
                    deductions_count=len(ch.get("deductions") or []),
                    inferred_involved=inferred_involved,
                    involved_written=involved_written,
                )

        # 上一层未齐时仍可补缺失投影，但落库必须过 persist 闸。
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

        for cid in involved:
            key = normalize_role_id(cid)
            if key in existing:
                continue
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
            blocked = persist_fields_blocked({"deductions": deds})
            if blocked:
                return pilot_deduce_observation(
                    park=blocked.get("message") or "演绎合计未达 5000，禁止把口号投影当已齐",
                    made=0, missing=missing_roles(involved, ch.get("deductions")),
                    stale=[], truth_revision=rev, scene_truth_chars=len(truth),
                    deductions_count=len(ch.get("deductions") or []),
                    inferred_involved=inferred_involved,
                    involved_written=involved_written,
                )
            st.update_chapter_meta(seq, {"deductions": deds})
            ch = st.get_chapter(seq) or ch
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
            if iceberg_ok_for(final_ch, "deduction"):
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
                park="演绎合计未达 5000，禁止把口号投影当已齐",
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
