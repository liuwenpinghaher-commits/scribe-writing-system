"""Write-path story constraints (R8) — pure, zero store IO.

Do NOT import format_contract_block here. Author field lines stay verbatim.
"""
from __future__ import annotations

import re
from typing import Any

CONTRACT_META_BAN = frozenset({
    "conflict_beats", "shape_ok", "validation.ok", "narrative_contract.v1",
})
DIALOGUE_CLAUSE_BAN = frozenset({"勾半笔", "减半笔", "暂不深探"})
_FIELD_LABELS = (("desire", "欲望"), ("obstacle", "阻力"), ("turn", "回合"), ("cost", "代价"))


def field_line(kind: str, text: str, *, max_chars: int = 0) -> str:
    """四义行 = 作者原文。只删英文字段名/机检 id，不做同义改写。默认不截断。"""
    raw = str(text or "").strip()
    for ban in CONTRACT_META_BAN:
        raw = raw.replace(ban, "")
    raw = re.sub(r"\bnarrative_contract\b", "", raw)
    raw = raw.strip()
    if max_chars and len(raw) > max_chars:
        raw = raw[:max_chars]
    return raw


def load_evidence_must_show(ch: dict | None) -> list[str]:
    """bindings.evidence_must_show → pressure stairs → []."""
    c = ch if isinstance(ch, dict) else {}
    contract = c.get("narrative_contract") if isinstance(c.get("narrative_contract"), dict) else c
    bindings = contract.get("bindings") if isinstance(contract, dict) else {}
    traces = []
    if isinstance(bindings, dict):
        raw = bindings.get("evidence_must_show")
        if isinstance(raw, list):
            traces = [str(x).strip() for x in raw if str(x).strip()]
        elif isinstance(raw, str) and raw.strip():
            traces = [raw.strip()]
    if traces:
        return traces[:3]
    pd = c.get("pressure_drive") if isinstance(c.get("pressure_drive"), dict) else {}
    irr = pd.get("irreversible") if isinstance(pd, dict) else None
    if isinstance(irr, dict):
        ev = irr.get("evidence_must_show")
        if isinstance(ev, list):
            return [str(x).strip() for x in ev if str(x).strip()][:3]
        if isinstance(ev, str) and ev.strip():
            return [ev.strip()]
    stairs = None
    prog = pd.get("progress") if isinstance(pd.get("progress"), dict) else None
    if isinstance(prog, dict):
        stairs = prog.get("stairs")
    if stairs is None:
        stairs = pd.get("stairs") if isinstance(pd, dict) else None
    if isinstance(stairs, list):
        out = []
        for s in stairs:
            if isinstance(s, dict):
                t = str(s.get("evidence_must_show") or "").strip()
                if t:
                    out.append(t)
        if out:
            return out[:3]
    return []


# 96k 窗下燃料段配额（窗口护栏，不是「写够才算」）
FUEL_CAP_EMBER = 1500
FUEL_CAP_RECALL = 4000
FUEL_CAP_CAUSAL = 2500


def format_story_contract_head(
    contract: dict | None = None,
    *,
    evidence_must_show: list[str] | None = None,
    voice: dict | None = None,
) -> str:
    """L0 场面头。四义原文；痕迹最多 3 条；禁止节不复贴四行。"""
    c = contract if isinstance(contract, dict) else {}
    fields = {k: field_line(k, c.get(k) or "") for k, _ in _FIELD_LABELS}
    if not any(fields.values()):
        return ""
    lines: list[str] = ["【本章必须发生的场面】（写戏，不要念条款）"]
    for key, label in _FIELD_LABELS:
        val = fields[key]
        if val:
            lines.append(f"{label}：{val}")
    traces = [str(x).strip() for x in (evidence_must_show or []) if str(x).strip()][:3]
    if traces:
        lines.append("必须留下的痕迹：")
        for t in traces:
            lines.append(f"- {t}")
    lines.append("禁止：")
    lines.append("- 角色嘴里不得复述上面四行原句，也不得把「勾半笔」「减半笔」「暂不深探」当出口语")
    lines.append("- 对白里不得用「——」做中句急转（迟疑用「……」或把话掐断另起一句）")
    lines.append("限知：角色嘴里不能知道焦点者此刻看不见/听不见/摸不到的；叙述者可以评点")
    if isinstance(voice, dict) and (voice.get("register") or voice.get("label")):
        lab = str(voice.get("register") or voice.get("label") or "").strip()
        if lab:
            lines.append(f"声口：{lab}")
    return "\n".join(lines)


def _clip_fuel(text: str, cap: int) -> str:
    raw = (text or "").strip()
    if cap and len(raw) > cap:
        return raw[: cap - 1] + "…"
    return raw


def format_story_fuel_parts(
    *,
    prior_consequences: str = "",
    recall_context: str = "",
    causal_graph: str = "",
) -> dict[str, str]:
    """可后裁燃料段。默认给全文，仅按段配额封顶（窗硬顶 48k，本函数不焊 L0）。"""
    out: dict[str, str] = {}
    pc = _clip_fuel(prior_consequences, FUEL_CAP_EMBER)
    if pc:
        out["story_ember"] = "【上章余烬】\n" + pc
    rec = _clip_fuel(recall_context, FUEL_CAP_RECALL)
    if rec:
        out["story_recall"] = "【世界此刻】（经限知投影）\n" + rec
    cg = _clip_fuel(causal_graph, FUEL_CAP_CAUSAL)
    if cg:
        out["story_causal"] = "【前因后果】\n" + cg
    return out


def format_story_constraint_block(
    contract: dict | None = None,
    *,
    evidence_must_show: list[str] | None = None,
    prior_consequences: str = "",
    voice: dict | None = None,
    recall_context: str = "",
    causal_graph: str = "",
    max_chars: int = 0,
) -> str:
    """兼容封装：默认只出场面头（span / 旧测）。燃料走 format_story_fuel_parts。"""
    head = format_story_contract_head(
        contract, evidence_must_show=evidence_must_show, voice=voice)
    if not head:
        return ""
    if max_chars and len(head) > int(max_chars):
        return head[: int(max_chars) - 1] + "…"
    return head


def span_revise_system() -> str:
    """System for /revise-span。不人为砍预算。"""
    return (
        "只改给出的选区，不要重写全章。保持说话人身份：老太婆说短白话，"
        "不要合同术语，不要对白中句破折号急转。只输出改后的那一句或几句。"
    )
