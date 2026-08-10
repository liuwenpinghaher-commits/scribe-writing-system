"""压力驱动章合同（PDC）+ 情节台阶（progress / PSC）· 纯函数。

真源：chapter.pressure_drive JSON。力学字段不双写进 chapter.beats。
注入硬顶：MAX_PDC_BLOCK = 400（Python len 字符）。
progress 校验 fail-soft：永不单独把 ok 改为 False / 永不 GATE park。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

PDC_VERSION = "pdc.v1"
PSC_VERSION = "psc.v1"
MAX_PDC_BLOCK = 400
MIN_RESERVE_P0B = 56
MAX_FIELD = 80
MAX_COST = 60
MAX_BODY_EVIDENCE = 12

_HIGH_ROLES = frozenset({"高压", "推进"})
_LOW_ROLES = frozenset({"低压", "关系回收", "修炼", "信息整理"})
_FUNCTION_WORDS = frozenset(
    "的了着在是和与又都也而及或被把让给对从到得地么呢吧啊呀"
)
_PLACE_CAND = re.compile(r"[\u4e00-\u9fff]{2,6}(?:铺|巷|门|库|房|庄|坊|街|口|檐|摊)")
_COST_CORE = ("空过", "收不回", "三日空过", "装不知道", "接不上", "退则空过", "空过三日")
_CHOICE_CORE = ("拧开", "接名", "退回", "插匙", "空过三日", "半寸")


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


def evidence_ok(s: str) -> bool:
    """台阶/不可逆证据串是否可作正文锚（拒纯虚词、过短）。"""
    t = (s or "").strip()
    if len(t) < 2:
        return False
    chars = [c for c in t if not c.isspace()]
    if not chars:
        return False
    if all(c in _FUNCTION_WORDS for c in chars):
        return False
    return True


def template_bootstrap_evidence(synopsis: str = "") -> str:
    """历史模板兜底：synopsis 含「灰」→ 掌心灰印，否则通用痕迹。"""
    if "灰" in (synopsis or ""):
        return "掌心嵌下的灰印"
    return "收不回的一步痕迹"


def first_ok_bootstrap_evidence(
    beats: list | None = None,
    *,
    template_fallback: str = "",
    synopsis: str = "",
) -> str:
    """PDC bootstrap 证据种子：first_ok(cost, turn, hook, template)。

    按字段优先级扫全部 beats：任一 beat 的 cost 通过 evidence_ok 即用；
    否则 turn，再 hook；全空才回落 template_fallback（或 synopsis 模板）。
    """
    for field in ("cost", "turn", "hook"):
        for b in beats or []:
            if not isinstance(b, dict):
                continue
            val = str(b.get(field) or "").strip()
            if evidence_ok(val):
                return _clip(val, MAX_FIELD)
    fb = (template_fallback or "").strip() or template_bootstrap_evidence(synopsis)
    if evidence_ok(fb):
        return _clip(fb, MAX_FIELD)
    return "收不回的一步痕迹"


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
    return (role or contract.get("role") or "").strip()


def extract_primary_locus(synopsis: str = "", beat_texts: list[str] | None = None) -> str:
    """从大纲/节拍抽主场地名（与 metrics place 启发式同源）。"""
    blob = f"{synopsis or ''}\n" + "\n".join(beat_texts or [])
    hits = _PLACE_CAND.findall(blob)
    if hits:
        # 频次最高
        from collections import Counter
        return Counter(hits).most_common(1)[0][0][:40]
    m = re.search(r"[\u4e00-\u9fff]{2,4}", blob)
    if m:
        return m.group(0)[:40]
    return "主场"


def _body_evidence_from_cost(step: str) -> str | None:
    t = (step or "").strip()
    for core in _COST_CORE:
        if core in t and evidence_ok(core):
            return core[:MAX_BODY_EVIDENCE]
    for c in re.findall(r"[\u4e00-\u9fff]{2,12}", t):
        if c in ("要么", "若是", "不能", "不可") or not evidence_ok(c):
            continue
        return c[:MAX_BODY_EVIDENCE]
    return None


def _body_evidence_from_choice(choice: str) -> str | None:
    t = (choice or "").strip()
    for core in _CHOICE_CORE:
        if core in t and evidence_ok(core):
            return core[:MAX_BODY_EVIDENCE]
    for c in re.findall(r"[\u4e00-\u9fff]{2,12}", t):
        if evidence_ok(c):
            return c[:MAX_BODY_EVIDENCE]
    return None


def _default_progress(
    irrev_evidence: str,
    locus: str,
    *,
    high: bool,
    fork_choice: str = "",
    cost_steps: list[str] | None = None,
) -> dict | None:
    """构造 progress 子合同；字段不齐则返回 None（调用方省略键）。"""
    irrev_ev = (irrev_evidence or "").strip()
    costs = [str(c).strip() for c in (cost_steps or []) if str(c).strip()]
    choice = (fork_choice or "").strip()
    retreatish = bool(costs) or any(k in choice for k in ("退", "不", "或", "要么", "空过"))

    stairs: list[dict] = []
    cost_ev = _body_evidence_from_cost(costs[0]) if costs else None
    if cost_ev:
        stairs.append({
            "id": "s1",
            "kind": "cost",
            "label": "岔路代价",
            "evidence_must_show": cost_ev,
            "is_retreat_cost": bool(retreatish),
        })
    else:
        dec_ev = _body_evidence_from_choice(choice)
        if dec_ev:
            stairs.append({
                "id": "s1",
                "kind": "decision",
                "label": "岔路抉择",
                "evidence_must_show": dec_ev,
                "is_retreat_cost": False,
            })

    if irrev_ev and evidence_ok(irrev_ev):
        if not stairs or stairs[0]["evidence_must_show"] != irrev_ev[:80]:
            stairs.append({
                "id": f"s{len(stairs)+1}",
                "kind": "irreversible",
                "label": "不可逆痕迹",
                "evidence_must_show": irrev_ev[:80],
                "is_retreat_cost": False,
            })

    if not stairs:
        fallback = "局面已变"
        if not evidence_ok(fallback):
            return None
        stairs = [{
            "id": "s1",
            "kind": "info",
            "label": "本章微变",
            "evidence_must_show": fallback,
            "is_retreat_cost": False,
        }]

    if retreatish and not any(s.get("is_retreat_cost") for s in stairs):
        cev = _body_evidence_from_cost(costs[0]) if costs else "三日空过"
        if cev is None:
            cev = "三日空过"
        if evidence_ok(cev) and all(s["evidence_must_show"] != cev for s in stairs):
            stairs.append({
                "id": f"s{len(stairs)+1}",
                "kind": "cost",
                "label": "退的代价",
                "evidence_must_show": cev[:MAX_BODY_EVIDENCE],
                "is_retreat_cost": True,
            })

    stairs = stairs[:4]
    return {
        "version": PSC_VERSION,
        "min_stairs": 1,
        "stairs": stairs,
        "location_grind": {
            "primary_locus": (locus or "主场")[:40],
            "max_contiguous_chars": 900 if high else 1400,
            "max_contiguous_paras": 6 if high else 10,
        },
        "retreat_policy": {
            "allow_retreat": True,
            "require_world_change": True,
            "change_kinds": ["cost", "decision", "irreversible"],
        },
        "main_channel": {
            "forbid_idle_majority": True,
            "hint": "极闲不得连续盖过主抉择段",
        },
    }


def _validate_progress(
    contract: dict,
    *,
    role: str | None = None,
) -> tuple[bool | None, list[str]]:
    """progress 子校验。返回 (progress_ok, warnings)。永不写入 errors。"""
    prog = contract.get("progress")
    if prog is None:
        return None, []
    if not isinstance(prog, dict):
        return False, ["progress_invalid_type"]
    if prog.get("version") and prog.get("version") != PSC_VERSION:
        # 未知版本仍尝试校验
        pass
    warnings: list[str] = []
    try:
        min_stairs = int(prog.get("min_stairs") or 1)
    except (TypeError, ValueError):
        min_stairs = 1
        warnings.append("progress_invalid_min_stairs")
    stairs = prog.get("stairs") if isinstance(prog.get("stairs"), list) else []
    if not stairs:
        return False, warnings + ["progress_invalid_empty_stairs"]
    if len(stairs) > 4:
        return False, warnings + ["progress_invalid_too_many_stairs"]
    if len(stairs) < min_stairs:
        warnings.append("progress_invalid_min")
        return False, warnings
    for i, s in enumerate(stairs):
        if not isinstance(s, dict):
            return False, warnings + [f"progress_invalid_stair_{i}"]
        lab = str(s.get("label") or "").strip()
        ev = str(s.get("evidence_must_show") or "").strip()
        if not lab:
            return False, warnings + [f"progress_invalid_label_{i}"]
        if not evidence_ok(ev):
            return False, warnings + [f"progress_invalid_evidence_{i}"]

    role_s = _role_of(contract, role)
    pressure = _chapter_pressure(contract)
    high = role_s in _HIGH_ROLES or pressure >= 4
    kinds = {str(s.get("kind") or "") for s in stairs if isinstance(s, dict)}
    if high and kinds and kinds <= {"relation", ""}:
        warnings.append("progress_invalid_kinds_relation_only")
        return False, warnings

    lg = prog.get("location_grind") if isinstance(prog.get("location_grind"), dict) else {}
    if high and not str(lg.get("primary_locus") or "").strip():
        warnings.append("progress_invalid_locus")
        return False, warnings

    # §1.2 ⑤ 高压可退岔路：至少一条 is_retreat_cost 或 kind∈{cost,decision,irreversible}
    # 仅 progress_ok=False + warnings；永不写入 errors / 永不改 ok
    if high:
        fork = contract.get("fork") if isinstance(contract.get("fork"), dict) else {}
        choice = str(fork.get("choice") or "").strip()
        costs = fork.get("cost_steps") if isinstance(fork.get("cost_steps"), list) else []
        retreatish = bool(costs) or any(
            k in choice for k in ("退", "不", "或", "要么", "空过")
        )
        if retreatish:
            has_retreat_cost = False
            for s in stairs:
                if not isinstance(s, dict):
                    continue
                kind = str(s.get("kind") or "")
                if s.get("is_retreat_cost") or kind in ("cost", "decision", "irreversible"):
                    has_retreat_cost = True
                    break
            if not has_retreat_cost:
                warnings.append("progress_invalid_retreat_cost")
                return False, warnings

    irrev = contract.get("irreversible") if isinstance(contract.get("irreversible"), dict) else {}
    irrev_ev = str(irrev.get("evidence_must_show") or "").strip()
    if irrev_ev and len(stairs) == 1:
        only = str(stairs[0].get("evidence_must_show") or "").strip()
        if only == irrev_ev:
            warnings.append("progress_redundant_with_irrev")

    return True, warnings


def validate_pdc(
    contract: dict | None,
    *,
    role: str | None = None,
    chapter_beats_count: int | None = None,
) -> dict:
    """三态校验 + progress_ok fail-soft。

    返回 ``{"ok", "errors", "warnings", "progress_ok"}``
    progress 非法只影响 progress_ok / warnings，**永不**单独把 ok 改为 False。
    """
    if not contract or not isinstance(contract, dict):
        return {"ok": None, "errors": [], "warnings": ["pdc_missing"], "progress_ok": None}
    if contract.get("status") == "missing":
        return {"ok": None, "errors": [], "warnings": ["pdc_status_missing"], "progress_ok": None}

    errors: list[str] = []
    warnings: list[str] = []

    fork = contract.get("fork") if isinstance(contract.get("fork"), dict) else {}
    irrev = contract.get("irreversible") if isinstance(contract.get("irreversible"), dict) else {}
    choice = str(fork.get("choice") or "").strip()
    evidence = str(irrev.get("evidence_must_show") or "").strip()

    has_version = bool(contract.get("version"))
    incomplete_core = len(choice) < 1 or len(evidence) < 2
    if incomplete_core and not has_version:
        return {"ok": None, "errors": [], "warnings": ["pdc_incomplete_core"], "progress_ok": None}
    if incomplete_core:
        if len(choice) < 1:
            errors.append("fork.choice 必填")
        if len(evidence) < 2:
            errors.append("irreversible.evidence_must_show 至少 2 字")
        # still attach progress_ok if present
        pok, pw = _validate_progress(contract, role=role)
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings + pw,
            "progress_ok": pok,
        }

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

    progress_ok, pw = _validate_progress(contract, role=role)
    warnings.extend(pw)

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "progress_ok": progress_ok,
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


def _format_p0_minimal(contract: dict) -> str:
    """预算极紧时：只保留 choice + evidence 核心行。"""
    fork = contract.get("fork") if isinstance(contract.get("fork"), dict) else {}
    irrev = contract.get("irreversible") if isinstance(contract.get("irreversible"), dict) else {}
    choice = _clip(fork.get("choice"), 40)
    evidence = _clip(irrev.get("evidence_must_show"), 40)
    lines = []
    if choice:
        lines.append(f"- 岔路：{choice}。")
    if evidence:
        lines.append(f"- 不可逆：正文须出现「{evidence}」。")
    return "\n".join(lines)


def _format_p0b(contract: dict, *, tight: bool = False) -> str:
    """推进钉 P0b：与 irrev 去重。"""
    prog = contract.get("progress") if isinstance(contract.get("progress"), dict) else None
    if not prog:
        return ""
    irrev = contract.get("irreversible") if isinstance(contract.get("irreversible"), dict) else {}
    irrev_ev = str(irrev.get("evidence_must_show") or "").strip()
    stairs = prog.get("stairs") if isinstance(prog.get("stairs"), list) else []
    lg = prog.get("location_grind") if isinstance(prog.get("location_grind"), dict) else {}
    locus = str(lg.get("primary_locus") or "主场")[:20]
    try:
        min_stairs = int(prog.get("min_stairs") or 1)
    except (TypeError, ValueError):
        min_stairs = 1

    distinct_evs = []
    for s in stairs:
        if not isinstance(s, dict):
            continue
        ev = str(s.get("evidence_must_show") or "").strip()
        if not ev or ev == irrev_ev:
            continue
        if ev not in distinct_evs:
            distinct_evs.append(ev)
        if len(distinct_evs) >= 2:
            break

    if tight:
        if distinct_evs:
            return f"- 台阶须现「{distinct_evs[0][:12]}」；退须改局。"
        return "- 同地勿磨；退须改局。"

    lines = []
    if distinct_evs:
        evs = "」「".join(e[:20] for e in distinct_evs)
        lines.append(f"- 台阶：至少 {min_stairs} 格；须现「{evs}」。")
    else:
        lines.append(f"- 台阶：至少 {min_stairs} 格（痕迹见上）；勿只磨不挪。")
    lines.append(f"- 同地：「{locus}」连续主戏勿超长。")
    lines.append("- 退：允许，须代价/决策落地，禁原状空转。")
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
    """渲染注入块；硬顶 MAX_PDC_BLOCK；P0 后强制尝试 P0b 推进钉。"""
    if not contract or not isinstance(contract, dict):
        return ""
    if contract.get("status") == "missing":
        return ""
    header = "## 压力驱动合同（遵守力学，勿复述本段）"
    p0 = _format_p0(contract)
    p0b_full = _format_p0b(contract, tight=False)
    p0b_tight = _format_p0b(contract, tight=True)
    rest = {
        "P1_time": _format_p1(contract),
        "P2_ritual_witness": _format_p2(contract),
        "P3_stroke_idle": _format_p3(contract),
        "P4_caps": _format_p4(contract),
    }

    # 保证 P0b 预留
    used0 = len(header)
    if p0 and used0 + 1 + len(p0) + 1 + MIN_RESERVE_P0B > MAX_PDC_BLOCK:
        p0 = _format_p0_minimal(contract)
    if p0 and used0 + 1 + len(p0) + 1 + MIN_RESERVE_P0B > MAX_PDC_BLOCK:
        # 截断 P0 字段
        budget = MAX_PDC_BLOCK - used0 - 1 - MIN_RESERVE_P0B - 1
        p0 = p0[: max(0, budget)]

    parts = [header]
    used = len(header)
    truncated_p0b = False

    if p0:
        parts.append(p0)
        used += 1 + len(p0)

    # 强制尝试 P0b
    p0b = p0b_full if p0b_full and used + 1 + len(p0b_full) <= MAX_PDC_BLOCK else None
    if p0b is None and p0b_tight:
        if used + 1 + len(p0b_tight) <= MAX_PDC_BLOCK:
            p0b = p0b_tight
            truncated_p0b = True
        else:
            # 尽量塞一行
            one = "- 退须改局。"
            if used + 1 + len(one) <= MAX_PDC_BLOCK:
                p0b = one
                truncated_p0b = True
    if p0b:
        parts.append(p0b)
        used += 1 + len(p0b)

    for key in ("P1_time", "P2_ritual_witness", "P3_stroke_idle", "P4_caps"):
        s = rest[key]
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
    # attach meta only for tests via attribute? return string only; tests check content
    if truncated_p0b and "退" not in out and "台阶" not in out and "同地" not in out:
        # last resort already applied
        pass
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
    return json.dumps(contract, ensure_ascii=False)


def make_missing_journal(warnings: list[str] | None = None) -> dict:
    return {
        "version": PDC_VERSION,
        "status": "missing",
        "warnings": list(warnings or ["pdc_bootstrap_degraded"]),
    }


def bootstrap_pdc_from_texts(
    *,
    synopsis: str = "",
    beat_texts: list[str] | None = None,
    chapter_beats: list | None = None,
    chapter_pressure: int = 4,
    role: str = "推进",
    fork_choice: str = "",
    evidence: str = "",
    irreversible_action: str = "",
    ritual_class: str = "记门",
    peak_segment: str = "抉择",
    motif_caps: list[dict] | None = None,
    cost_steps: list[str] | None = None,
) -> dict | None:
    """确定性 bootstrap：字段齐全才返回 present 合同；含 progress 双台阶。

    evidence 空时：若传入 chapter_beats（含 cost/turn/hook），
    用 first_ok(cost,turn,hook,template) 作种子（PR-7）。
    """
    choice = (fork_choice or "").strip()
    ev = (evidence or "").strip()
    if not evidence_ok(ev) and chapter_beats is not None:
        ev = first_ok_bootstrap_evidence(
            chapter_beats, synopsis=synopsis
        )
    if len(choice) < 1 or len(ev) < 2:
        return None
    texts = list(beat_texts or [])
    if not texts and chapter_beats:
        texts = [
            str(b.get("text") or "")
            for b in chapter_beats
            if isinstance(b, dict)
        ]
    if not texts:
        texts = ["推进", "对峙", "抉择", "余波"]
    n = max(4, min(7, len(texts)))
    while len(texts) < n:
        texts.append(f"节拍{len(texts)+1}")
    texts = texts[:n]
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
    costs = list(cost_steps) if cost_steps else ["选错则收不回", "退则空过三日"]
    cp = max(1, min(5, int(chapter_pressure or 4)))
    role_s = role or "推进"
    high = role_s in _HIGH_ROLES or cp >= 4
    locus = extract_primary_locus(synopsis, texts)
    progress = _default_progress(
        ev,
        locus,
        high=high,
        fork_choice=choice,
        cost_steps=costs,
    )
    out = {
        "version": PDC_VERSION,
        "chapter_pressure": cp,
        "role": role_s,
        "time_budget": {"mode": "bend", "story_span": "≤两刻钟"},
        "fork": {
            "choice": _clip(choice, MAX_FIELD),
            "cost_steps": [_clip(c, MAX_COST) for c in costs[:3]],
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
    if progress:
        out["progress"] = progress
    return out
