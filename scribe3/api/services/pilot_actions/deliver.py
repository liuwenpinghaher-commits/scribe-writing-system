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
        _row0 = (
            st.get_chapter_qc_and_pilot_card(seq)
            if hasattr(st, "get_chapter_qc_and_pilot_card")
            else {}
        )
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
        st.set_pilot_card(seq, json.dumps(card, ensure_ascii=False))
        return {"card": card}


    return {"deliver": deliver}
