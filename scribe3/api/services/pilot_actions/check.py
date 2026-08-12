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


    return {"full_check": full_check}
