"""压力驱动章合同（PDC）· 纯函数：校验 / 渲染 / flag / load 合并。

真源：chapter.pressure_drive JSON。力学字段不双写进 chapter.beats。
注入硬顶：MAX_PDC_BLOCK = 400（Python len 字符）。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

PDC_VERSION = "pdc.v1"
MAX_PDC_BLOCK = 400
MAX_FIELD = 80
MAX_COST = 60

_HIGH_ROLES = frozenset({"高压", "推进"})
_LOW_ROLES = frozenset({"低压", "关系回收", "修炼", "信息整理"})


def pdc_flag_enabled() -> bool:
    v = (os.environ.get("SCRIBE3_PDC") or "0").strip().lower()
    return v in ("1", "true", "yes", "on")


def pdc_gate_enabled() -> bool:
    v = (os.environ.get("SCRIBE3_PDC_GATE") or "0").strip().lower()
    return v in ("1", "true", "yes", "on")


def pdc_blocking_env_enabled() -> bool:
    v = (os.environ.get("SCRIBE3_PDC_BLOCKING") or "0").strip().lower()
    return v in ("1", "true", "yes", "on")


def _clip(s: Any, n: int) -> str:
    t = str(s or "").strip()
    return t if len(t) <= n else t[:n]


def parse_pressure_drive(raw: Any) -> dict | None:
    """解析落库字段 → dict；status=missing 视为无合同。"""
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        d = raw
    elif isinstance(raw, str):
        try:
            d = json.loads(raw)
        except (ValueError, TypeError):
            return None
        if not isinstance(d, dict):
            return None
    else:
        return None
    if d.get("status") == "missing":
        return None
    return d


def load_pdc(chapter: dict | None) -> dict | None:
    """合并章表 beats 文案到 pressure_drive 投影（力学真源仍是 pressure_drive）。"""
    if not chapter or not isinstance(chapter, dict):
        return None
    raw = parse_pressure_drive(chapter.get("pressure_drive"))
    if not raw:
        return None
    out = dict(raw)
    beats_proj = list(out.get("beats") or [])
    ch_beats = chapter.get("beats") or []
    if isinstance(ch_beats, str):
        try:
            ch_beats = json.loads(ch_beats) if ch_beats else []
        except (ValueError, TypeError):
            ch_beats = []
    if not isinstance(ch_beats, list):
        ch_beats = []
    for i, b in enumerate(ch_beats):
        if not isinstance(b, dict):
            continue
        text = b.get("text")
        if text is None:
            continue
        if i < len(beats_proj) and isinstance(beats_proj[i], dict):
            if beats_proj[i].get("text") != text:
                beats_proj[i] = {**beats_proj[i], "text": text, "stale_text": True}
            else:
                beats_proj[i] = {**beats_proj[i], "text": text}
        elif i >= len(beats_proj):
            beats_proj.append({"text": text})
    out["beats"] = beats_proj
    return out


def _chapter_pressure(contract: dict, role: str | None = None) -> int:
    try:
        p = int(contract.get("chapter_pressure") or 0)
    except (TypeError, ValueError):
        p = 0
    if p:
        return max(1, min(5, p))
    return 0


def _role_of(contract: dict, role: str | None = None) -> str:
    r = (role or contract.get("role") or "").strip()
    return r


def validate_pdc(
    contract: dict | None,
    *,
    role: str | None = None,
    chapter_beats_count: int | None = None,
) -> dict:
    """三态校验。

    返回 ``{"ok": True|False|None, "errors": [...], "warnings": [...]}``
    - ok=None：无合同 / missing
    - ok=False：有完整意图但结构非法
    - ok=True：结构合法
    """
    if not contract or not isinstance(contract, dict):
        return {"ok": None, "errors": [], "warnings": ["pdc_missing"]}
    if contract.get("status") == "missing":
        return {"ok": None, "errors": [], "warnings": ["pdc_status_missing"]}

    errors: list[str] = []
    warnings: list[str] = []

    fork = contract.get("fork") if isinstance(contract.get("fork"), dict) else {}
    irrev = contract.get("irreversible") if isinstance(contract.get("irreversible"), dict) else {}
    choice = str(fork.get("choice") or "").strip()
    evidence = str(irrev.get("evidence_must_show") or "").strip()

    # 完备子集 ⑦⑧：缺则视为「非 present 完整合同」→ ok=None（bootstrap 降级）
    # 若作者显式写了 version 且缺 ⑦⑧，仍 ok=False 促补全（有 version + 任意力学意图）
    has_version = bool(contract.get("version"))
    incomplete_core = len(choice) < 1 or len(evidence) < 2
    if incomplete_core and not has_version:
        return {"ok": None, "errors": [], "warnings": ["pdc_incomplete_core"]}
    if incomplete_core:
        if len(choice) < 1:
            errors.append("fork.choice 必填")
        if len(evidence) < 2:
            errors.append("irreversible.evidence_must_show 至少 2 字")
        return {"ok": False, "errors": errors, "warnings": warnings}

    beats = contract.get("beats") if isinstance(contract.get("beats"), list) else []
    if chapter_beats_count is not None and beats and len(beats) != chapter_beats_count:
        warnings.append(
            f"beats 投影条数 {len(beats)} ≠ 章表 {chapter_beats_count}"
        )

    role_s = _role_of(contract, role)
    pressure = _chapter_pressure(contract)
    high = role_s in _HIGH_ROLES or pressure >= 4
    low = role_s in _LOW_ROLES or (pressure and pressure <= 2)

    peaks = [b for b in beats if isinstance(b, dict) and b.get("is_peak")]
    if beats:
        if len(peaks) != 1 and high:
            errors.append(f"高压/推进章须恰好 1 个 is_peak，当前 {len(peaks)}")
        elif len(peaks) > 1:
            errors.append(f"is_peak 不得超过 1，当前 {len(peaks)}")
        elif len(peaks) == 0 and not low:
            warnings.append("无 is_peak 标记")

    p_levels = []
    for b in beats:
        if not isinstance(b, dict):
            continue
        try:
            p_levels.append(int(b.get("p_level")))
        except (TypeError, ValueError):
            pass
    if high and len(p_levels) >= 2:
        span = max(p_levels) - min(p_levels)
        if span < 2:
            errors.append(f"p_level 跨度须 ≥2，当前 {span}")
        # 方差或相邻 Δ
        mean = sum(p_levels) / len(p_levels)
        var = sum((x - mean) ** 2 for x in p_levels) / len(p_levels)
        adj = any(abs(p_levels[i] - p_levels[i - 1]) >= 2 for i in range(1, len(p_levels)))
        if var < 0.8 and not adj:
            errors.append("p_level 方差过低且无相邻 |Δ|≥2")

    funcs = {
        str(b.get("function") or "")
        for b in beats
        if isinstance(b, dict)
    }
    if high:
        if "force" not in funcs:
            errors.append("function 须含 force")
        if not (funcs & {"choice", "cost"}):
            errors.append("function 须含 choice 或 cost")

    time_roles = {
        str(b.get("time_role") or "")
        for b in beats
        if isinstance(b, dict)
    }
    if beats and time_roles and time_roles <= {"advance", ""}:
        if high:
            errors.append("time_role 不得全为 advance")
        else:
            if not (time_roles & {"hold", "aftermath", "collapse", "flash"}):
                warnings.append("低压章建议 time_role 含 hold|aftermath")

    ritual_n = sum(1 for b in beats if isinstance(b, dict) and b.get("is_ritual"))
    rq = contract.get("ritual_quota") if isinstance(contract.get("ritual_quota"), dict) else {}
    max_full = int(rq.get("max_full") or 1)
    if ritual_n > max_full and not rq.get("second_must_deform"):
        errors.append(f"完整仪式 beats 数 {ritual_n} > max_full={max_full} 且未标 second_must_deform")

    tb = contract.get("time_budget") if isinstance(contract.get("time_budget"), dict) else {}
    mode = str(tb.get("mode") or "")
    if high and mode == "linear":
        errors.append("高压/推进章 time_budget.mode 不得为 linear")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def _format_p0(contract: dict) -> str:
    fork = contract.get("fork") if isinstance(contract.get("fork"), dict) else {}
    irrev = contract.get("irreversible") if isinstance(contract.get("irreversible"), dict) else {}
    choice = _clip(fork.get("choice"), MAX_FIELD)
    costs = fork.get("cost_steps") if isinstance(fork.get("cost_steps"), list) else []
    cost_s = "；".join(_clip(c, MAX_COST) for c in costs[:3] if str(c).strip())
    action = _clip(irrev.get("action"), MAX_FIELD)
    evidence = _clip(irrev.get("evidence_must_show"), MAX_FIELD)
    lines = []
    if choice:
        lines.append(f"- 岔路：{choice}" + (f"；代价：{cost_s}" if cost_s else "") + "。")
    if evidence:
        lines.append(
            f"- 不可逆：正文须出现「{evidence}」"
            + (f"（动作：{action}）" if action else "")
            + "（痕迹，非总结）。"
        )
    return "\n".join(lines)


def _format_p1(contract: dict) -> str:
    tb = contract.get("time_budget") if isinstance(contract.get("time_budget"), dict) else {}
    mode = _clip(tb.get("mode"), 20)
    span = _clip(tb.get("story_span"), 40)
    if not mode and not span:
        return ""
    return f"- 时间：{mode or 'bend'}·{span or '压紧'}；禁止匀速流水账。"


def _format_p2(contract: dict) -> str:
    rq = contract.get("ritual_quota") if isinstance(contract.get("ritual_quota"), dict) else {}
    wp = contract.get("witness_policy") if isinstance(contract.get("witness_policy"), dict) else {}
    cls = _clip(rq.get("class"), 20)
    lines = []
    if cls:
        lines.append(f"- 仪式：「{cls}」完整至多 {int(rq.get('max_full') or 1)} 次；再写须变形。")
    mode = _clip(wp.get("mode"), 20)
    if mode:
        lines.append(f"- 证人：同题完整报知 ≤{int(wp.get('max_same_fact_reporters') or 1)} 人（{mode}）。")
    return "\n".join(lines)


def _format_p3(contract: dict) -> str:
    sp = contract.get("stroke_plan") if isinstance(contract.get("stroke_plan"), dict) else {}
    peak = _clip(sp.get("peak_segment"), 40)
    idle = sp.get("idle_skew") if isinstance(sp.get("idle_skew"), dict) else {}
    lines = []
    if peak:
        lines.append(f"- 正笔：仅「{peak}」全开；其余克制。")
    if idle.get("forbid_even_spread") or idle:
        u = int(idle.get("ultra_idle") or 2)
        h = int(idle.get("ultra_hard") or 1)
        lines.append(f"- 闲笔偏科：{u} 极闲 + {h} 极狠；禁巷志均铺。")
    return "\n".join(lines)


def _format_p4(contract: dict) -> str:
    caps = contract.get("motif_intensity_caps")
    if not isinstance(caps, list) or not caps:
        return ""
    bits = []
    for c in caps[:4]:
        if not isinstance(c, dict):
            continue
        term = _clip(c.get("term"), 12)
        try:
            mx = int(c.get("max_mentions") or 0)
        except (TypeError, ValueError):
            mx = 0
        if term and mx > 0:
            bits.append(f"{term}≤{mx}")
    if not bits:
        return ""
    return "- 意象上限：" + "、".join(bits) + "。"


def render_pressure_drive_block(contract: dict | None) -> str:
    """渲染注入块；硬顶 MAX_PDC_BLOCK；优先保留 P0 钉。"""
    if not contract or not isinstance(contract, dict):
        return ""
    if contract.get("status") == "missing":
        return ""
    header = "## 压力驱动合同（遵守力学，勿复述本段）"
    sections = {
        "P0_fork_irrev": _format_p0(contract),
        "P1_time": _format_p1(contract),
        "P2_ritual_witness": _format_p2(contract),
        "P3_stroke_idle": _format_p3(contract),
        "P4_caps": _format_p4(contract),
    }
    p0 = sections["P0_fork_irrev"]
    if p0 and len(header) + 1 + len(p0) > MAX_PDC_BLOCK:
        # 截断 P0 字段后再拼，不丢整段标题
        budget = MAX_PDC_BLOCK - len(header) - 1
        return header + "\n" + p0[: max(0, budget)]

    parts = [header]
    used = len(header)
    for key in ("P0_fork_irrev", "P1_time", "P2_ritual_witness", "P3_stroke_idle", "P4_caps"):
        s = sections[key]
        if not s:
            continue
        add = 1 + len(s)
        if used + add > MAX_PDC_BLOCK:
            break
        parts.append(s)
        used += add
    out = "\n".join(parts)
    if len(out) > MAX_PDC_BLOCK:
        out = out[:MAX_PDC_BLOCK]
    return out


def beat_pressure_stats(contract: dict | None) -> dict:
    if not contract or not isinstance(contract, dict):
        return {"var": None, "span": None, "n": 0}
    levels = []
    for b in contract.get("beats") or []:
        if isinstance(b, dict):
            try:
                levels.append(int(b.get("p_level")))
            except (TypeError, ValueError):
                pass
    if not levels:
        return {"var": None, "span": None, "n": 0}
    mean = sum(levels) / len(levels)
    var = sum((x - mean) ** 2 for x in levels) / len(levels)
    return {"var": var, "span": max(levels) - min(levels), "n": len(levels)}


def dump_pressure_drive(contract: dict) -> str:
    """序列化落库。"""
    return json.dumps(contract, ensure_ascii=False)


def make_missing_journal(warnings: list[str] | None = None) -> dict:
    """bootstrap 降级 journal；load_pdc / parse 视为无合同。"""
    return {
        "version": PDC_VERSION,
        "status": "missing",
        "warnings": list(warnings or ["pdc_bootstrap_degraded"]),
    }


def bootstrap_pdc_from_texts(
    *,
    synopsis: str = "",
    beat_texts: list[str] | None = None,
    chapter_pressure: int = 4,
    role: str = "推进",
    fork_choice: str = "",
    evidence: str = "",
    irreversible_action: str = "",
    ritual_class: str = "记门",
    peak_segment: str = "抉择",
    motif_caps: list[dict] | None = None,
) -> dict | None:
    """确定性/测试用 bootstrap：字段齐全才返回 present 合同，否则 None（调用方不写 present）。"""
    choice = (fork_choice or "").strip()
    ev = (evidence or "").strip()
    if len(choice) < 1 or len(ev) < 2:
        return None
    texts = list(beat_texts or []) or ["推进", "对峙", "抉择", "余波"]
    n = max(4, min(7, len(texts)))
    while len(texts) < n:
        texts.append(f"节拍{len(texts)+1}")
    texts = texts[:n]
    # 压力台阶
    if n >= 4:
        levels = [2, 3, 5, 3] + [2] * (n - 4)
    else:
        levels = list(range(2, 2 + n))
    peak_i = min(n - 2, max(1, n // 2))
    functions = ["setup", "force", "choice", "cost", "release", "hook", "aftermath"]
    time_roles = ["advance", "hold", "collapse", "advance", "aftermath", "flash", "hold"]
    beats = []
    for i, t in enumerate(texts):
        beats.append({
            "id": f"b{i+1}",
            "text": t,
            "p_level": levels[i] if i < len(levels) else 3,
            "time_role": time_roles[i % len(time_roles)],
            "function": functions[i % len(functions)],
            "is_peak": i == peak_i,
            "is_ritual": i == 1,
            "is_irreversible": i == peak_i,
            "spatial_inventory": False,
        })
    return {
        "version": PDC_VERSION,
        "chapter_pressure": max(1, min(5, int(chapter_pressure or 4))),
        "role": role or "推进",
        "time_budget": {"mode": "bend", "story_span": "≤两刻钟"},
        "fork": {
            "choice": _clip(choice, MAX_FIELD),
            "cost_steps": ["选错则收不回", "不选也是一种选"][:2],
        },
        "irreversible": {
            "action": _clip(irreversible_action or "落下痕迹", MAX_FIELD),
            "evidence_must_show": _clip(ev, MAX_FIELD),
        },
        "ritual_quota": {
            "class": ritual_class or "记门",
            "max_full": 1,
            "second_must_deform": True,
        },
        "witness_policy": {"mode": "info_gap", "max_same_fact_reporters": 1},
        "stroke_plan": {
            "peak_segment": peak_segment or "抉择",
            "idle_skew": {"ultra_idle": 2, "ultra_hard": 1, "forbid_even_spread": True},
        },
        "motif_intensity_caps": motif_caps or [{"term": "铜腥", "max_mentions": 3}],
        "beats": beats,
    }
