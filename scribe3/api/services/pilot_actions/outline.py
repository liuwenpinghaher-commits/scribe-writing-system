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


    return {"propose_outline": propose_outline}
