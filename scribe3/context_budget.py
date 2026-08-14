# scribe3/context_budget.py
"""Novel-first 写路径预算与 L2 裁剪纯函数（无 I/O · 可单测）。

第一原则：戏剧信号密度 / 注意力质量；禁止以 tokens_saved 为 KPI。
设计：docs/plans/2026-08-11-novel-first-injection-quality-optimal.md rev.3.1
"""
from __future__ import annotations

import os
from typing import Any, Iterable

# ── 现网默认（V1 · flag 关）──────────────────────────────────────────
# rev.1.2：provenance 出生成 prompt；freed 回灌 canon 60% / recent 40%
BLOCK_BUDGETS_V1: dict[str, int] = {
    "focus": 800,
    "global": 1200,
    "canonical": 3280,  # +480（原 provenance 800×0.6）
    "recent": 1920,     # +320（800×0.4）
    "procedural": 900,
    "reference": 1400,
    "uncertainty": 500,
    "provenance": 0,
}
DEFAULT_ENVELOPE_TOKEN_BUDGET_V1 = 10_000
assert sum(BLOCK_BUDGETS_V1.values()) == DEFAULT_ENVELOPE_TOKEN_BUDGET_V1

# ── Novel-first 目标表（V2 · flag 开）────────────────────────────────
BLOCK_BUDGETS_V2: dict[str, int] = {
    "focus": 1000,
    "global": 1600,
    "canonical": 7400,  # +600
    "recent": 4400,     # +400
    "procedural": 1200,
    "reference": 1600,
    "uncertainty": 800,
    "provenance": 0,
}
DEFAULT_ENVELOPE_TOKEN_BUDGET_V2 = 18_000
assert sum(BLOCK_BUDGETS_V2.values()) == DEFAULT_ENVELOPE_TOKEN_BUDGET_V2

# Novel 可选再抬（仅 high-signal 块；须同步 PROMPT_HARD=48k）
BLOCK_BUDGETS_NOVEL: dict[str, int] = {
    "focus": 1000,
    "global": 1800,
    "canonical": 9200,  # +600
    "recent": 6000,     # +400
    "procedural": 1400,
    "reference": 1800,
    "uncertainty": 800,
    "provenance": 0,
}
NOVEL_ENVELOPE_TOKEN_BUDGET = 22_000
assert sum(BLOCK_BUDGETS_NOVEL.values()) == NOVEL_ENVELOPE_TOKEN_BUDGET

# ── literary / epic（设计 §3 整数表 · 与 V2 并存 · 由 FIDELITY 旗选择）──
BLOCK_BUDGETS_LITERARY: dict[str, int] = {
    "focus": 1100,
    "global": 2000,
    "canonical": 4500,
    "recent": 4500,
    "procedural": 1000,
    "reference": 1200,
    "uncertainty": 700,
    "provenance": 0,  # 默认不进模型（容量归 0；trace 仍可有）
}
LITERARY_ENVELOPE_TOKEN_BUDGET = 15_000
assert sum(BLOCK_BUDGETS_LITERARY.values()) == LITERARY_ENVELOPE_TOKEN_BUDGET

BLOCK_BUDGETS_EPIC: dict[str, int] = {
    "focus": 1200,
    "global": 2400,
    "canonical": 5500,
    "recent": 5500,
    "procedural": 1100,
    "reference": 1400,
    "uncertainty": 900,
    "provenance": 0,
}
EPIC_ENVELOPE_TOKEN_BUDGET = 18_000
assert sum(BLOCK_BUDGETS_EPIC.values()) == EPIC_ENVELOPE_TOKEN_BUDGET

# 场景自适应：同总额重配，禁止砍半 envelope
# V2/epic 档（18k）· provenance 回灌 canon 60% / recent 40%
SCENE_BUDGET_PROFILES: dict[str, dict[str, int]] = {
    "dialogue_heavy": {
        "focus": 1200, "global": 1400, "canonical": 6920, "recent": 5280,
        "procedural": 1000, "reference": 1400, "uncertainty": 800, "provenance": 0,
    },
    "action_heavy": {
        "focus": 1400, "global": 1600, "canonical": 6480, "recent": 5320,
        "procedural": 1200, "reference": 1200, "uncertainty": 800, "provenance": 0,
    },
    "exposition": {
        "focus": 800, "global": 2000, "canonical": 7680, "recent": 3920,
        "procedural": 1000, "reference": 1800, "uncertainty": 800, "provenance": 0,
    },
}
for _name, _tbl in SCENE_BUDGET_PROFILES.items():
    assert sum(_tbl.values()) == 18_000, _name
    assert int(_tbl.get("provenance", 0) or 0) == 0, _name

# Novel 档（22k）：provenance=0 + 回灌
SCENE_BUDGET_PROFILES_NOVEL: dict[str, dict[str, int]] = {
    "dialogue_heavy": {
        "focus": 1100, "global": 1600, "canonical": 8380, "recent": 7120,
        "procedural": 1300, "reference": 1700, "uncertainty": 800, "provenance": 0,
    },
    "action_heavy": {
        "focus": 1300, "global": 1700, "canonical": 8520, "recent": 6680,
        "procedural": 1500, "reference": 1500, "uncertainty": 800, "provenance": 0,
    },
    "exposition": {
        "focus": 900, "global": 2200, "canonical": 9680, "recent": 5120,
        "procedural": 1300, "reference": 2000, "uncertainty": 800, "provenance": 0,
    },
}
for _name, _tbl in SCENE_BUDGET_PROFILES_NOVEL.items():
    assert sum(_tbl.values()) == NOVEL_ENVELOPE_TOKEN_BUDGET, (
        f"SCENE_BUDGET_PROFILES_NOVEL[{_name}] sum={sum(_tbl.values())}"
    )
    assert int(_tbl.get("provenance", 0) or 0) == 0, _name

DEFAULT_CODEX_INJECT_CAP = 4_500
DEFAULT_SUPPLEMENTAL_SOFT = 14_000
DEFAULT_SUPPLEMENTAL_HARD = 18_000
# 质量优先：标准 V2 回滚档仍可用 42k；生产默认 novel 时 get_prompt_hard→48k
DEFAULT_PROMPT_HARD = 42_000
NOVEL_PROMPT_HARD = 48_000
# 升窗档。模型窗够大（≥192k）时走这条；48k 只留给未知/小窗，不是产品终态。
NOVEL_PROMPT_HARD_WIDE = 96_000
WIDE_SUPPLEMENTAL_SOFT = 28_000
WIDE_SUPPLEMENTAL_HARD = 36_000
WIDE_MIN_MODEL_WINDOW = 2 * NOVEL_PROMPT_HARD_WIDE  # 192_000
# 96k 档燃料帽：余烬/召回/前因随窗加长，否则升窗作者感觉不到
WIDE_FUEL_CAP_EMBER = 2_500
WIDE_FUEL_CAP_RECALL = 6_000
WIDE_FUEL_CAP_CAUSAL = 4_000

# ── L2 四档 DROP（唯一真源 · rev.1.2 WS-6）──────────────────────────
# 数字越大越先丢；T0/GEN_SEGMENT_PROTECTED 不进 victim 或极低优先级
L2_DROP_TIER: dict[str, tuple[str, ...]] = {
    # SL2：storyline_polish 进 T3（与 material_recall/reference_craft 同档，先可裁）
    "T3": ("codex_cards", "material_recall", "discourse_soft", "story_move", "storyline_polish", "reference_craft", "seed_words", "author_prefs"),
    "T2": ("craft", "phase_role", "avoid", "volume_intro", "request_constraint"),
    "T1": ("purpose", "pressure_drive"),
    # 故事燃料：T3→T2→T1 之后才裁；段内先丢 recall，最后丢 ember
    "T1_fuel": ("story_recall", "story_causal", "story_ember"),
}
# 生成段保护集（outline 等）：超 cap 时后于 T3→T2→T1 才考虑半裁
GEN_SEGMENT_PROTECTED: frozenset[str] = frozenset({
    "outline", "brief_must", "voice_anchor",
    "draft_full", "deduction_final", "codex_named",
})


def _build_l2_drop_priority() -> dict[str, int]:
    """由 L2_DROP_TIER 派生 priority map（禁止另写第二份 14 键真源）。"""
    pri: dict[str, int] = {}
    # T3 先丢：90, 88, 86, …
    for i, name in enumerate(L2_DROP_TIER["T3"]):
        pri[name] = 90 - i
    for i, name in enumerate(L2_DROP_TIER["T2"]):
        pri[name] = 60 - i
    for i, name in enumerate(L2_DROP_TIER["T1"]):
        pri[name] = 30 - i
    for i, name in enumerate(L2_DROP_TIER.get("T1_fuel") or ()):
        pri[name] = 22 - i
    # 保护段：仅在 T* 裁尽后才可被选为 victim（priority 极低但仍 > envelope 的 12）
    for name in GEN_SEGMENT_PROTECTED:
        pri[name] = 8
    return pri


# 兼容旧名：运行时唯一由四档派生
L2_DROP_PRIORITY: dict[str, int] = _build_l2_drop_priority()

# 永不作为 L2 victim
L0_NEVER_CUT: frozenset[str] = frozenset({
    "identity", "write_protocol", "revision", "anti_slop",
    "continue_snapshot", "secret_guard", "request_position",
    "tool_scope", "craft_skills_index", "focalizer",
    "narrative_contract",
    "event_drive", "drama_contract", "drama_vacuum", "envelope",
    "revelation_discipline", "sincerity", "final_reminder",
    "deduction_final", "scene_truth_proj",
    # prefix / structure_diversity 等同 redline 待遇
    "prefix", "structure_diversity",
})

# O1 全域硬顶：默认跟 PROMPT_HARD；SCRIBE3_TOTAL_BUDGET=999999 禁用
DEFAULT_TOTAL_PROMPT_BUDGET = 42_000


def get_total_prompt_budget(*, work: str | None = None) -> int:
    """全局 prompt 硬顶（token 估算口径同 estimate_tokens）。

    env ``SCRIBE3_TOTAL_BUDGET``：正整数；``>=900000`` 视为关闭全域裁剪。
    未设时回落 ``get_prompt_hard(work=)``（与 L2 总顶一致）。
    禁止把 wide 缺窗的 RuntimeError 吞成 42k。
    """
    raw = (os.environ.get("SCRIBE3_TOTAL_BUDGET") or "").strip()
    if raw.isdigit():
        return int(raw)
    return get_prompt_hard(work=work)


def enforce_total_prompt_budget(
    segments: list[dict[str, Any]],
    *,
    budget: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """全域预算裁剪：红线/L0 永不整段丢；优先砍 supplemental（按 L2_DROP_PRIORITY）。

    **禁止**对最终 joined 串 ``rendered[:budget]`` 尾截。
    """
    segs = [dict(s) for s in segments if (s.get("text") or "")]
    cap = get_total_prompt_budget() if budget is None else int(budget)
    before = sum(estimate_tokens(s.get("text")) for s in segs)
    report: dict[str, Any] = {
        "total_budget": cap,
        "enabled": 0 < cap < 900_000,
        "dropped": [],
        "dropped_ops": [],
        "before_est": before,
    }
    if not report["enabled"]:
        report["after_est"] = before
        report["over_budget"] = False
        return segs, report

    def _total() -> int:
        return sum(estimate_tokens(s.get("text")) for s in segs)

    def _victim_idx() -> int | None:
        # 先裁 T3→T2→T1；GEN_SEGMENT_PROTECTED 仅当无更高 priority victim 时才选
        best_i, best_pri = None, -1
        protected_i, protected_pri = None, -1
        for i, s in enumerate(segs):
            name = str(s.get("name") or "")
            layer = str(s.get("layer") or "")
            if name in L0_NEVER_CUT or layer == "redline":
                continue
            if layer == "envelope":
                pri = 12
            else:
                pri = int(L2_DROP_PRIORITY.get(name, 55))
            if name in GEN_SEGMENT_PROTECTED:
                if pri > protected_pri:
                    protected_pri = pri
                    protected_i = i
                continue
            if pri > best_pri:
                best_pri = pri
                best_i = i
        if best_i is not None:
            return best_i
        return protected_i

    unsqueezable: set[str] = set()
    while _total() > cap:
        vi = _victim_idx()
        if vi is None:
            break
        name = str(segs[vi].get("name") or "?")
        if name in unsqueezable:
            break
        text = segs[vi].get("text") or ""
        if len(text) > 200:
            new = _half_cut_segment(name, text)
            if new == text or len(new) >= len(text):
                report["dropped"].append(f"{name}:no_shrink")
                if name in GEN_SEGMENT_PROTECTED:
                    unsqueezable.add(name)
                    continue
                report["dropped_ops"].append({
                    "name": name, "op": "total_drop",
                    "text_before": text, "text_after": "",
                    "chars_before": len(text), "chars_after": 0,
                })
                segs.pop(vi)
                continue
            segs[vi]["text"] = new
            tag = "keep_beats" if name == "outline" else "total_half"
            report["dropped"].append(f"{name}:{tag}")
            report["dropped_ops"].append({
                "name": name, "op": tag,
                "text_before": text, "text_after": new,
                "chars_before": len(text), "chars_after": len(new),
            })
        else:
            report["dropped"].append(f"{name}:total_drop")
            report["dropped_ops"].append({
                "name": name, "op": "total_drop",
                "text_before": text, "text_after": "",
                "chars_before": len(text), "chars_after": 0,
            })
            segs.pop(vi)

    after = _total()
    report["after_est"] = after
    report["over_budget"] = after > cap
    return segs, report


def _env_truthy(name: str, default: str = "0") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw in ("1", "true", "yes", "on")


def envelope_v2_enabled() -> bool:
    """生产默认开：18k/V2 物理序+L2（质量优先）。

    关：SCRIBE3_ENVELOPE_V2_ENABLE=0 回滚 10k。
    literary/epic/novel 保真档也隐含启用 V2。
    """
    if _env_truthy("SCRIBE3_ENVELOPE_V2_ENABLE", "1"):
        return True
    fid = (os.environ.get("SCRIBE3_CONTEXT_FIDELITY") or "").strip().lower()
    return fid in ("literary", "epic", "novel", "v2")


def novel_envelope_enabled() -> bool:
    """质量优先：默认开 novel 信封 22k（须与 V2 同开，PROMPT_HARD→48k）。

    关：SCRIBE3_ENVELOPE_NOVEL=0 退回标准 V2 18k。
    """
    return _env_truthy("SCRIBE3_ENVELOPE_NOVEL", "1")


def context_fidelity() -> str:
    """compat | v2 | literary | epic | novel — 默认 novel（质量优先）。"""
    raw = (os.environ.get("SCRIBE3_CONTEXT_FIDELITY") or "").strip().lower()
    if raw in ("compat", "v1", "literary", "epic", "novel", "v2"):
        if raw == "v1":
            return "compat"
        return raw
    if novel_envelope_enabled() and envelope_v2_enabled():
        return "novel"
    if envelope_v2_enabled():
        return "v2"
    return "compat"


# beat_type → SCENE_BUDGET_PROFILES 键（O2）
BEAT_TYPE_TO_SCENE_PROFILE: dict[str, str] = {
    "dialogue": "dialogue_heavy",
    "dialogue_heavy": "dialogue_heavy",
    "action": "action_heavy",
    "action_heavy": "action_heavy",
    "interior": "dialogue_heavy",  # 内心戏偏 recent
    "worldbuild": "exposition",
    "exposition": "exposition",
    "worldbuilding": "exposition",
}


def adaptive_budget_enabled() -> bool:
    """SCRIBE3_ADAPTIVE_BUDGET=1 时允许 beat_type 自动选 profile（默认开）。"""
    return _env_truthy("SCRIBE3_ADAPTIVE_BUDGET", "1")


def scene_budget_profile() -> str | None:
    """SCRIBE3_SCENE_BUDGET_PROFILE=dialogue_heavy|action_heavy|exposition；空=关。"""
    raw = (os.environ.get("SCRIBE3_SCENE_BUDGET_PROFILE") or "").strip().lower()
    # 名称在 18k / novel 表均可
    if raw in SCENE_BUDGET_PROFILES or raw in SCENE_BUDGET_PROFILES_NOVEL:
        return raw
    return None


def select_budget_profile(beat_type: str | None = None) -> str | None:
    """解析场景预算 profile 名：显式 env 优先，否则 adaptive+beat_type。"""
    explicit = scene_budget_profile()
    if explicit:
        return explicit
    if not adaptive_budget_enabled():
        return None
    key = BEAT_TYPE_TO_SCENE_PROFILE.get((beat_type or "").strip().lower())
    if key and (key in SCENE_BUDGET_PROFILES or key in SCENE_BUDGET_PROFILES_NOVEL):
        return key
    return None


def _scene_table_for_fidelity(fid: str) -> dict[str, dict[str, int]]:
    """按保真档选场景重配表：novel→22k 表；其余有 18k 表的用 V2 表。"""
    if fid == "novel":
        return SCENE_BUDGET_PROFILES_NOVEL
    return SCENE_BUDGET_PROFILES


def get_block_budgets(*, beat_type: str | None = None) -> dict[str, int]:
    fid = context_fidelity()
    if fid == "novel":
        base = dict(BLOCK_BUDGETS_NOVEL)
    elif fid == "literary":
        base = dict(BLOCK_BUDGETS_LITERARY)
    elif fid == "epic":
        base = dict(BLOCK_BUDGETS_EPIC)
    elif fid == "v2" or envelope_v2_enabled():
        base = dict(BLOCK_BUDGETS_V2)
    else:
        base = dict(BLOCK_BUDGETS_V1)

    prof = select_budget_profile(beat_type)
    if not prof:
        return base

    # novel 必须用 22k 场景表，禁止被 18k 表静默覆盖
    if fid == "novel":
        tbl = SCENE_BUDGET_PROFILES_NOVEL.get(prof)
        if tbl:
            return dict(tbl)
        return base

    # literary 暂无场景重配（总额 15k 无对应表）
    if fid == "literary":
        return base

    # v2 / epic / compat+V2：18k 场景表
    if prof in SCENE_BUDGET_PROFILES:
        # 仅当基表总额为 18k，或 V2 已开（兼容旧 force 路径但不再盖 novel）
        if sum(base.values()) == 18_000 or envelope_v2_enabled():
            return dict(SCENE_BUDGET_PROFILES[prof])
    return base


def get_envelope_token_budget() -> int:
    budgets = get_block_budgets()
    total = sum(budgets.values())
    # 允许 env 覆盖总额（仍要求与块表一致时由调用方 assert）
    override = (os.environ.get("SCRIBE3_ENVELOPE_TOKEN_BUDGET") or "").strip()
    if override.isdigit():
        return int(override)
    return total


def resolve_assembler_budgets(
    token_budget: int | None = None,
    block_budgets: dict[str, int] | None = None,
    *,
    beat_type: str | None = None,
) -> tuple[int, dict[str, int]]:
    """Engine/Assembler 共用的预算解析（无 I/O 外 env · 可单测）。

    返回 ``(token_budget, block_budgets)``，保证 ``sum(block_budgets)`` 在未显式
    覆盖 token_budget 时与 flag 表一致。``beat_type`` 参与 O2 场景重配。
    """
    if block_budgets is not None:
        bb = dict(block_budgets)
    else:
        bb = get_block_budgets(beat_type=beat_type)
    if token_budget is not None:
        tb = int(token_budget)
    elif block_budgets is not None:
        tb = sum(bb.values())
    else:
        # 与块表同 profile（勿再走无 beat_type 的 get_envelope_token_budget）
        tb = sum(bb.values())
    return tb, bb


# 写路径 V2 段序 SSOT：write_assemble._render_final_input 必须经
# ``ordered_generation_segments`` 接线，禁止另写平行序。
GENERATION_SEGMENT_LAYERS: dict[str, str] = {
    "identity": "redline",
    "prefix": "redline",
    "revision": "redline",
    "structure_diversity": "redline",
    "continue_snapshot": "redline",
    "tool_scope": "redline",
    "craft_skills_index": "supplemental",
    "secret_guard": "redline",
    "focalizer": "redline",
    "narrative_contract": "redline",
    "story_ember": "supplemental",
    "story_recall": "supplemental",
    "story_causal": "supplemental",
    "event_drive": "redline",
    "event_drive_hook": "supplemental",
    "drama_contract": "redline",
    "drama_vacuum": "redline",
    "envelope": "envelope",
    "codex_named": "supplemental",
    "codex_cards": "supplemental",
    "seed_words": "supplemental",
    "craft": "supplemental",
    "phase_role": "supplemental",
    "avoid": "supplemental",
    "revelation_discipline": "redline",
    "sincerity": "redline",
    "purpose": "supplemental",
    "outline": "supplemental",
    "volume_intro": "supplemental",
    "brief_must": "supplemental",
    "pressure_drive": "supplemental",
    "author_prefs": "supplemental",
    "voice_anchor": "supplemental",
    "reference_craft": "supplemental",
    "deduction_final": "redline",
    "draft_full": "supplemental",
    "material_recall": "supplemental",
    "final_reminder": "redline",
    "scene_truth_proj": "redline",
    "request_constraint": "supplemental",
}


def ordered_generation_segments(
    pieces: Iterable[dict[str, Any]] | list[dict[str, Any]],
    *,
    v2: bool = True,
    order_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    """按 production 物理序整理段列表；同名多段保持相对顺序（reference_craft 等）。

    每段 dict 至少含 name/text；缺 layer 时查 GENERATION_SEGMENT_LAYERS。
    ``order_names`` 非空时用其作为序（active 注册表注入）；否则
    ``generation_physical_order_names``。
    """
    items = [dict(s) for s in pieces if (s.get("text") or "")]
    order = list(order_names) if order_names else generation_physical_order_names(v2=v2)
    # 主干序；附加名插在 final_reminder 前
    rank = {n: i for i, n in enumerate(order)}
    extra_base = len(order)

    # stable: decorate with original index
    decorated = []
    for i, s in enumerate(items):
        name = str(s.get("name") or "")
        if not s.get("layer"):
            s["layer"] = GENERATION_SEGMENT_LAYERS.get(name, "supplemental")
        if name in rank:
            decorated.append((rank[name], i, s))
        else:
            # 未列名：尽量靠 final_reminder 前
            fr = rank.get("final_reminder", extra_base)
            decorated.append((fr - 1, i, s))
    decorated.sort(key=lambda t: (t[0], t[1]))
    return [t[2] for t in decorated]


def join_generation_segments(
    pieces: list[dict[str, Any]],
    *,
    v2: bool = True,
    work: str | None = None,
    supplemental_hard: int | None = None,
    prompt_hard: int | None = None,
    total_budget: int | None = None,
    supplemental_soft: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """生产路径用的段 join：V2 走 L2 裁剪；随后 O1 全域硬顶；V1 仅全域硬顶可选。

    返回 (joined, report)。**禁止**对最终 joined 串尾截。
    L2 与 O1 使用同一组 ``resolve_write_caps(work)`` 数字，禁止各算各的。
    active 注册表：``order_names`` 取 ``registry_physical_order_names``，
    真正参与 ``ordered_generation_segments`` 排序（非 no-op）。
    """
    caps = resolve_write_caps(work)
    sh = int(supplemental_hard) if supplemental_hard is not None else caps["supplemental_hard"]
    ph = int(prompt_hard) if prompt_hard is not None else caps["prompt_hard"]
    tb = int(total_budget) if total_budget is not None else caps["total_budget"]
    ss = int(supplemental_soft) if supplemental_soft is not None else caps["supplemental_soft"]
    order_names: list[str] | None = None
    order_source = "generation_physical_order"
    try:
        from scribe3.injection_registry import (
            active_registry_orders_join,
            registry_physical_order_names,
        )
        if active_registry_orders_join():
            order_names = registry_physical_order_names(v2=v2)
            order_source = "injection_registry"
    except Exception:
        order_names = None
    segs = ordered_generation_segments(pieces, v2=v2, order_names=order_names)
    l2_rep: dict[str, Any] = {}
    if v2:
        # active：L3 段优先进入 material 裁剪池（预算策略参与，不只观测）
        if order_source == "injection_registry":
            try:
                from scribe3.injection_registry import registry_l3_names
                l3 = registry_l3_names()
                for s in segs:
                    if str(s.get("name") or "") in l3 and s.get("layer") != "redline":
                        s["layer"] = "supplemental"
                        s["registry_tier"] = "L3"
            except Exception:
                pass
        _joined_l2, l2_rep = apply_l2_trim(
            segs,
            supplemental_hard=sh,
            prompt_hard=ph,
            supplemental_soft=ss,
        )
        del _joined_l2
        segs = list(l2_rep.get("segments") or segs)

    segs, total_rep = enforce_total_prompt_budget(segs, budget=tb)
    joined = "".join(str(s.get("text") or "") for s in segs)
    order_idx: dict[str, int] = {}
    for i, s in enumerate(segs):
        n = str(s.get("name") or "")
        if n in physical_order_markers() and n not in order_idx:
            order_idx[n] = i
    rep = build_budget_report(
        domain_lengths={
            str(s.get("name")): estimate_tokens(s.get("text")) for s in segs
        },
        order_indices=order_idx,
        l2_report=l2_rep,
        work=work,
    )
    rep["total_enforce"] = total_rep
    rep["order_source"] = order_source
    rep["registry_active"] = order_source == "injection_registry"
    # 校验 final_reminder 仍在
    names = [str(s.get("name") or "") for s in segs]
    rep["final_reminder_kept"] = "final_reminder" in names
    return joined, rep


def get_codex_inject_cap(work: str | None = None) -> int:
    """点名包软顶。必须带 work 才能分档；无 work 走 resolve_write_caps 的窄档。"""
    from scribe3.iceberg import named_pack_soft_cap
    return named_pack_soft_cap(work=work)


def _wide_switch() -> str:
    """升窗开关：on / off / auto。

    空或未设 = auto：模型窗 ≥192k 就 96k（产品默认）。
    1 = on：必须有够大的窗，否则炸（运维显式要 96k）。
    0 = off：强制 48k（回滚）。
    """
    raw_num = (os.environ.get("SCRIBE3_NOVEL_PROMPT_HARD") or "").strip()
    if raw_num:
        if raw_num != str(NOVEL_PROMPT_HARD_WIDE):
            raise RuntimeError(
                f"SCRIBE3_NOVEL_PROMPT_HARD={raw_num!r} 非法；只接受空或 {NOVEL_PROMPT_HARD_WIDE}"
            )
        return "on"
    raw = os.environ.get("SCRIBE3_NOVEL_WIDE")
    if raw is None or str(raw).strip() == "":
        return "auto"
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off"):
        return "off"
    if s in ("1", "true", "yes", "on"):
        return "on"
    raise RuntimeError(f"SCRIBE3_NOVEL_WIDE={raw!r} 非法；只接受空/0/1")


def _parse_wide_request() -> bool:
    """兼容旧名：是否『显式请求』升窗（不含 auto）。"""
    return _wide_switch() == "on"


def _model_window_int() -> int | None:
    raw_win = (os.environ.get("SCRIBE3_MODEL_CONTEXT_WINDOW") or "").strip()
    if not raw_win:
        return None
    if not raw_win.isdigit():
        raise RuntimeError(
            f"SCRIBE3_MODEL_CONTEXT_WINDOW={raw_win!r} 非法；须正整数"
        )
    return int(raw_win)


def novel_wide_enabled() -> bool:
    """进程是否走 96k。

    auto：窗够大就开，窗未知/太小走 48k（不炸）。
    on：窗不够则 fail-loud，禁止假装升窗。
    off：强制 48k。
    """
    switch = _wide_switch()
    if switch == "off":
        return False
    win = _model_window_int()
    if switch == "on":
        if win is None:
            raise RuntimeError("已请求 novel_wide 但未设正整数 SCRIBE3_MODEL_CONTEXT_WINDOW")
        if win < WIDE_MIN_MODEL_WINDOW:
            raise RuntimeError(
                f"SCRIBE3_MODEL_CONTEXT_WINDOW={win} < {WIDE_MIN_MODEL_WINDOW}，拒绝升窗"
            )
        return True
    return win is not None and win >= WIDE_MIN_MODEL_WINDOW


def wide_works_slugs() -> frozenset[str]:
    allow = (os.environ.get("SCRIBE3_NOVEL_WIDE_WORKS") or "").strip()
    if not allow:
        return frozenset()
    return frozenset(p.strip() for p in allow.split(",") if p.strip())


def novel_wide_for_work(work: str | None) -> bool:
    if not novel_wide_enabled():
        return False
    slugs = wide_works_slugs()
    if not slugs:
        return True  # 全站；PR3 浸泡禁止空名单
    return (work or "").strip() in slugs


def get_prompt_hard(*, work: str | None = None) -> int:
    if novel_envelope_enabled() and envelope_v2_enabled():
        if novel_wide_for_work(work):
            return NOVEL_PROMPT_HARD_WIDE
        return NOVEL_PROMPT_HARD
    raw = (os.environ.get("SCRIBE3_PROMPT_HARD") or "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_PROMPT_HARD


def get_supplemental_hard(*, work: str | None = None) -> int:
    raw = (os.environ.get("SCRIBE3_SUPPLEMENTAL_HARD") or "").strip()
    if raw.isdigit():
        return int(raw)
    return WIDE_SUPPLEMENTAL_HARD if novel_wide_for_work(work) else DEFAULT_SUPPLEMENTAL_HARD


def get_supplemental_soft(*, work: str | None = None) -> int:
    raw = (os.environ.get("SCRIBE3_SUPPLEMENTAL_SOFT") or "").strip()
    if raw.isdigit():
        return int(raw)
    return WIDE_SUPPLEMENTAL_SOFT if novel_wide_for_work(work) else DEFAULT_SUPPLEMENTAL_SOFT


def resolve_write_caps(work: str | None = None) -> dict[str, Any]:
    """一次算齐写路径硬顶，供 join / L2 / O1 / probe 共用。"""
    wide = novel_wide_for_work(work)
    return {
        "prompt_hard": get_prompt_hard(work=work),
        "supplemental_soft": get_supplemental_soft(work=work),
        "supplemental_hard": get_supplemental_hard(work=work),
        "total_budget": get_total_prompt_budget(work=work),
        "novel_wide": wide,
        "work": work,
        "prompt_hard_profile": (
            "novel_96k" if wide
            else ("novel_48k" if novel_envelope_enabled() and envelope_v2_enabled() else "standard")
        ),
        "wide_works": sorted(wide_works_slugs()),
        "model_context_window": (os.environ.get("SCRIBE3_MODEL_CONTEXT_WINDOW") or "").strip(),
        "work_unspecified_narrow": bool(wide_works_slugs()) and not (work or "").strip(),
    }


def estimate_tokens(text: str | None) -> int:
    """与 context_assembler 同口径：len(text) 保守上界。"""
    return len(text or "")


def subtract_canonical_lines_in_codex(
    env_text: str | None, codex: str | None,
) -> tuple[str, int]:
    """从 envelope 的 canonical 块丢掉已在 codex 出现的整行（≥8 字）。其它块不动。"""
    src = str(env_text or "")
    cx = str(codex or "")
    if not src or not cx:
        return src, 0
    out: list[str] = []
    in_canon = False
    dropped = 0
    for line in src.splitlines(keepends=True):
        body = line.strip()
        if body.startswith("## "):
            in_canon = "权威事实" in body
            out.append(line)
            continue
        payload = body.lstrip("-*• ").strip()
        if in_canon and len(payload) >= 8 and (body in cx or payload in cx):
            dropped += 1
            continue
        out.append(line)
    return "".join(out), dropped


def subtract_codex_canonical_echoes(codex: str | None, canonical: str | None) -> str:
    """去掉已在 canonical/envelope 全文中出现的整行（≥8 字），再交给 cap。"""
    src = str(codex or "")
    can = str(canonical or "")
    if not src or not can:
        return src
    kept: list[str] = []
    for line in src.splitlines(keepends=True):
        body = line.strip()
        if len(body) >= 8 and body in can:
            continue
        kept.append(line)
    return "".join(kept)


def cap_codex_text(text: str | None, cap: int | None = None) -> str:
    s = text or ""
    limit = DEFAULT_CODEX_INJECT_CAP if cap is None else int(cap)
    if limit <= 0 or len(s) <= limit:
        return s
    return s[: max(0, limit - 1)] + "…"


def effective_l2_cap(
    l0_est: int,
    l1_est: int,
    *,
    supplemental_hard: int,
    prompt_hard: int,
) -> int:
    """effective_L2_cap = min(HARD, PROMPT_HARD - L0 - L1)。两帽必填，内部零 getter。"""
    hard, ph = int(supplemental_hard), int(prompt_hard)
    room = max(0, int(ph) - max(0, int(l0_est)) - max(0, int(l1_est)))
    return min(max(0, int(hard)), room)


def physical_order_markers() -> tuple[str, ...]:
    """写路径关键标记（用于序断言 / budget_report）。"""
    return (
        "narrative_contract",
        "event_drive",
        "drama_contract",
        "envelope",
        "codex_named",
        "final_reminder",
    )


def assert_physical_order_indices(indices: dict[str, int]) -> None:
    """indices: domain → first index in assembled string or segment list.

    narrative_contract 可缺；有合同时允许 event_drive 缺席、改认 event_drive_hook。
    """
    ed = indices.get("event_drive")
    hook = indices.get("event_drive_hook")
    dr = indices.get("drama_contract")
    env = indices.get("envelope")
    cx = indices.get("codex_named")
    if cx is None:
        cx = indices.get("codex")
    fr = indices.get("final_reminder")
    drive_slot = ed if ed is not None else hook
    if None in (drive_slot, dr, env, cx, fr):
        missing = [
            k for k in (
                "event_drive", "drama_contract", "envelope", "codex_named", "final_reminder",
            )
            if indices.get(k) is None and not (k == "codex_named" and indices.get("codex") is not None)
        ]
        if not (ed is None and hook is not None):
            raise AssertionError(f"missing order markers: {missing}")
    nc = indices.get("narrative_contract")
    if nc is not None and drive_slot is not None and not (nc < drive_slot):
        raise AssertionError(
            f"bad physical order: narrative_contract={nc} must precede drive/hook={drive_slot}")
    if hook is not None and fr is not None and not (hook < fr):
        raise AssertionError(
            f"bad physical order: event_drive_hook={hook} must precede final_reminder={fr}")
    if not (drive_slot < dr < env < cx < fr):
        raise AssertionError(
            f"bad physical order: drive/hook={drive_slot} drama={dr} "
            f"envelope={env} codex_named={cx} final_reminder={fr}"
        )


def _split_outline_for_half_cut(text: str) -> tuple[str, str, str, str]:
    """切 outline 为 header / 〔大纲〕 / 〔节拍〕 / 尾契约。缺标记则空串。"""
    syn_at = text.find("〔大纲〕")
    beat_at = text.find("〔节拍〕")
    tail_idx = [i for i in (text.find("写作要求:"), text.find("(以上为作者视角大纲")) if i >= 0]
    tail_at = min(tail_idx) if tail_idx else -1
    marks: list[tuple[int, str]] = []
    if syn_at >= 0:
        marks.append((syn_at, "syn"))
    if beat_at >= 0:
        marks.append((beat_at, "beat"))
    if tail_at >= 0:
        marks.append((tail_at, "tail"))
    marks.sort()
    if not marks:
        return text, "", "", ""
    header = text[: marks[0][0]]
    parts = {"syn": "", "beat": "", "tail": ""}
    for i, (pos, kind) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        parts[kind] = text[pos:end]
    return header, parts["syn"], parts["beat"], parts["tail"]


def _half_cut_segment(name: str, text: str) -> str:
    """半裁。短大纲（≤800）不砍纲；长大纲才保拍砍纲。演绎/排演不半裁。"""
    s = str(text or "")
    if not s:
        return s
    if name in ("draft_full", "deduction_final", "codex_named"):
        return s
    if name != "outline":
        return s[: max(1, len(s) // 2)] + "…"
    header, syn, beat, tail = _split_outline_for_half_cut(s)
    syn_body = syn.replace("〔大纲〕", "")
    from scribe3.iceberg import cn_len
    if cn_len(syn_body) <= 800:
        return s
    target = max(1, len(s) // 2)
    if not beat:
        return s[:target] + "…"
    placeholder = "〔大纲〕大纲已裁，以节拍为准。"

    def pack(syn_txt: str, beat_txt: str, tail_txt: str) -> str:
        return "".join(p for p in (header, syn_txt, beat_txt, tail_txt) if p)

    for cand in (
        pack(placeholder if syn else "", beat, tail),
        pack("", beat, tail),
    ):
        if len(cand) <= target:
            return cand
    room = target - len(header) - len(tail)
    if room > 8:
        clipped = beat[:room]
        if len(clipped) < len(beat):
            clipped = clipped[:-1] + "…"
        cand = pack("", clipped, tail)
        if len(cand) <= target:
            return cand
    room = target - len(header)
    if room > 8:
        return pack("", beat[: room - 1] + "…", "")
    return (header + beat)[:target] + "…"


def apply_l2_trim(
    segments: list[dict[str, Any]],
    *,
    l0_est: int | None = None,
    l1_est: int | None = None,
    supplemental_hard: int | None = None,
    prompt_hard: int | None = None,
    supplemental_soft: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """对 segment 列表做 L2 有序裁剪后 join。

    每个 segment: {name, layer, text}
      layer: redline | envelope | supplemental

    **禁止**对最终 joined 串做 rendered[:hard] 尾截。
    """
    segs = [dict(s) for s in segments if (s.get("text") or "")]
    if l0_est is None:
        l0_est = sum(
            estimate_tokens(s.get("text"))
            for s in segs if s.get("layer") == "redline"
        )
    if l1_est is None:
        l1_est = sum(
            estimate_tokens(s.get("text"))
            for s in segs if s.get("layer") == "envelope"
        )
    hard = get_supplemental_hard() if supplemental_hard is None else int(supplemental_hard)
    ph = get_prompt_hard() if prompt_hard is None else int(prompt_hard)
    cap = effective_l2_cap(l0_est, l1_est, supplemental_hard=hard, prompt_hard=ph)
    soft = get_supplemental_soft() if supplemental_soft is None else int(supplemental_soft)

    def _l2_total() -> int:
        return sum(
            estimate_tokens(s.get("text"))
            for s in segs if s.get("layer") == "supplemental"
        )

    dropped: list[str] = []
    dropped_ops: list[dict[str, Any]] = []
    soft_exceeded = _l2_total() > soft

    def _victim_idx() -> int | None:
        best_i = None
        best_pri = -1
        protected_i = None
        protected_pri = -1
        for i, s in enumerate(segs):
            if s.get("layer") != "supplemental":
                continue
            name = str(s.get("name") or "")
            if name in L0_NEVER_CUT:
                continue
            pri = L2_DROP_PRIORITY.get(name, 55)
            if name in GEN_SEGMENT_PROTECTED:
                if pri > protected_pri:
                    protected_pri = pri
                    protected_i = i
                continue
            if pri > best_pri:
                best_pri = pri
                best_i = i
        if best_i is not None:
            return best_i
        return protected_i

    # hard: while L2 > cap
    unsqueezable: set[str] = set()
    while _l2_total() > cap:
        vi = _victim_idx()
        if vi is None:
            break
        name = str(segs[vi].get("name") or "?")
        if name in unsqueezable:
            break
        text = segs[vi].get("text") or ""
        # 尝试半裁；过短则整段丢弃。短大纲/draft_full 可能拒绝缩小。
        if len(text) > 200:
            new = _half_cut_segment(name, text)
            if new == text or len(new) >= len(text):
                dropped.append(f"{name}:no_shrink")
                if name in GEN_SEGMENT_PROTECTED:
                    unsqueezable.add(name)
                    continue
                dropped_ops.append({
                    "name": name, "op": "drop",
                    "text_before": text, "text_after": "",
                    "chars_before": len(text), "chars_after": 0,
                })
                segs.pop(vi)
                continue
            segs[vi]["text"] = new
            tag = "keep_beats" if name == "outline" else "tail_half"
            dropped.append(f"{name}:{tag}")
            dropped_ops.append({
                "name": name, "op": tag,
                "text_before": text, "text_after": new,
                "chars_before": len(text), "chars_after": len(new),
            })
        else:
            dropped.append(f"{name}:drop")
            dropped_ops.append({
                "name": name, "op": "drop",
                "text_before": text, "text_after": "",
                "chars_before": len(text), "chars_after": 0,
            })
            segs.pop(vi)

    # total prompt hard
    def _total() -> int:
        return sum(estimate_tokens(s.get("text")) for s in segs)

    while _total() > ph:
        vi = _victim_idx()
        if vi is None:
            break
        name = str(segs[vi].get("name") or "?")
        if name in GEN_SEGMENT_PROTECTED:
            dropped.append(f"{name}:prompt_hard_keep")
            break
        dropped.append(f"{name}:prompt_hard_drop")
        dropped_ops.append({
            "name": name, "op": "prompt_hard_drop",
            "text_before": str(segs[vi].get("text") or ""), "text_after": "",
            "chars_before": len(str(segs[vi].get("text") or "")), "chars_after": 0,
        })
        segs.pop(vi)

    joined = "".join(str(s.get("text") or "") for s in segs)
    report = {
        "l0_est": l0_est,
        "l1_est": l1_est,
        "l2_est": _l2_total(),
        "total_est": estimate_tokens(joined),
        "effective_l2_cap": cap,
        "supplemental_hard": hard,
        "prompt_hard": ph,
        "soft_exceeded": soft_exceeded,
        "dropped": dropped,
        "dropped_ops": dropped_ops,
        "segment_names": [s.get("name") for s in segs],
        "segments": segs,  # 供 join 继续 O1 全域硬顶（副本列表）
        "envelope_v2": envelope_v2_enabled(),
        "signal_density_note": "primary metric is drama signal density, not tokens_saved",
    }
    return joined, report


def generation_physical_order_names(*, v2: bool = True) -> list[str]:
    """目标物理序域名列表（V2）；与 join_generation_segments / write_assemble 同 SSOT。

    默认（SCRIBE3_OUTLINE_AFTER_DRAMA=1）：outline 紧随 drama_vacuum、envelope 前
    （高注意力区 · 第一原则收尾 U4）。
    """
    outline_after = True
    try:
        from scribe3.quality_enablement_flags import outline_after_drama_enabled
        outline_after = bool(outline_after_drama_enabled())
    except Exception:
        import os as _os
        raw = (_os.environ.get("SCRIBE3_OUTLINE_AFTER_DRAMA") or "1").strip().lower()
        outline_after = raw not in ("0", "false", "no", "off", "")

    base = [
        "identity",
        "write_protocol",
        "prefix",
        "revision",
        "structure_diversity",
        "continue_snapshot",
        "secret_guard",
        "focalizer",
        "narrative_contract",
        "story_ember",
        "story_recall",
        "story_causal",
        "event_drive",
        "event_drive_hook",
        "drama_contract",
        "drama_vacuum",
    ]
    if outline_after:
        base.append("outline")
    base.append("envelope")
    if v2:
        base.append("codex_named")
    mid = [
        "seed_words",
        "craft",
        "phase_role",
        "avoid",
        "revelation_discipline",
        "sincerity",
        "purpose",
    ]
    if not outline_after:
        mid.append("outline")
    mid.extend([
        "volume_intro",
        "brief_must",
        "pressure_drive",
        "author_prefs",
        "voice_anchor",
        "draft_full",
        "reference_craft",
        "storyline_polish",  # SL2 · 紧邻 reference_craft 后
        "discourse_soft",  # W2 · KD-D28 紧邻 storyline_polish 后
        "story_move",  # 招式：polish/discourse 后、final_reminder 前
        "deduction_final",
        "material_recall",
        "final_reminder",
        "scene_truth_proj",
        "request_constraint",
    ])
    base.extend(mid)
    return base


def build_budget_report(
    *,
    domain_lengths: dict[str, int] | None = None,
    order_indices: dict[str, int] | None = None,
    l2_report: dict[str, Any] | None = None,
    beat_type: str | None = None,
    event_graph_k: int | None = None,
    work: str | None = None,
) -> dict[str, Any]:
    """观测报告（不含成本 KPI）。固定含 registry/fidelity/prompt_hard 等可观测字段。"""
    fid = context_fidelity()
    prof = select_budget_profile(beat_type)
    reg_mode = "off"
    try:
        from scribe3.injection_registry import registry_mode
        reg_mode = str(registry_mode() or "off")
    except Exception:
        pass
    eg_k = event_graph_k
    if eg_k is None:
        try:
            raw_k = (os.environ.get("SCRIBE3_EVENT_GRAPH_K") or "2").strip()
            eg_k = int(raw_k) if raw_k.isdigit() else 2
        except Exception:
            eg_k = 2
    caps = resolve_write_caps(work)
    return {
        "envelope_token_budget": get_envelope_token_budget(),
        "block_budgets": get_block_budgets(beat_type=beat_type),
        "envelope_v2_enabled": envelope_v2_enabled(),
        "codex_inject_cap": get_codex_inject_cap(),
        "domain_lengths": dict(domain_lengths or {}),
        "order_indices": dict(order_indices or {}),
        "l2": dict(l2_report or {}),
        "primary_metric": "signal_density_for_drama",
        "not_a_kpi": "tokens_saved",
        # H9 可观测
        "registry_mode": reg_mode,
        "adaptive_profile": prof,
        "fidelity": fid,
        "prompt_hard": caps["prompt_hard"],
        "prompt_hard_profile": caps["prompt_hard_profile"],
        "novel_wide": caps["novel_wide"],
        "supplemental_soft": caps["supplemental_soft"],
        "supplemental_hard": caps["supplemental_hard"],
        "model_context_window": caps["model_context_window"],
        "wide_works": list(caps["wide_works"]),
        "work": work,
        "work_unspecified_narrow": caps["work_unspecified_narrow"],
        "event_graph": {"k": int(eg_k or 0)},
        "novel_envelope": novel_envelope_enabled(),
        "adaptive_budget": adaptive_budget_enabled(),
    }


def signal_density_proxy(
    domain_lengths: dict[str, int] | None = None,
) -> dict[str, float | int]:
    """小说向密度代理：戏剧+红线 / 总长（非 cost KPI）。"""
    d = dict(domain_lengths or {})
    drama_keys = (
        "event_drive", "drama_contract", "revelation_discipline",
        "sincerity", "final_reminder", "secret_guard",
    )
    num = sum(int(d.get(k) or 0) for k in drama_keys)
    den = sum(int(v) for v in d.values()) or 1
    return {
        "drama_redline_tokens": num,
        "total_tokens": den,
        "signal_density_proxy": round(num / den, 4),
        "primary_metric": "signal_density_for_drama",
    }
