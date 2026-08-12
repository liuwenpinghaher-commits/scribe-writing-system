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

# ── L2 四档 DROP（唯一真源 · rev.1.2 WS-6）──────────────────────────
# 数字越大越先丢；T0/GEN_SEGMENT_PROTECTED 不进 victim 或极低优先级
L2_DROP_TIER: dict[str, tuple[str, ...]] = {
    # SL2：storyline_polish 进 T3（与 material_recall/reference_craft 同档，先可裁）
    "T3": ("material_recall", "storyline_polish", "reference_craft", "seed_words", "author_prefs"),
    "T2": ("craft", "phase_role", "avoid", "volume_intro", "request_constraint"),
    "T1": ("codex", "purpose", "pressure_drive"),
}
# 生成段保护集（outline 等）：超 cap 时后于 T3→T2→T1 才考虑半裁
GEN_SEGMENT_PROTECTED: frozenset[str] = frozenset({
    "outline", "brief_must", "voice_anchor",
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
    "event_drive", "drama_contract", "drama_vacuum", "envelope",
    "revelation_discipline", "sincerity", "final_reminder",
    "deduction_final", "scene_truth_proj",
    # prefix / structure_diversity 等同 redline 待遇
    "prefix", "structure_diversity",
})

# O1 全域硬顶：默认跟 PROMPT_HARD；SCRIBE3_TOTAL_BUDGET=999999 禁用
DEFAULT_TOTAL_PROMPT_BUDGET = 42_000


def get_total_prompt_budget() -> int:
    """全局 prompt 硬顶（token 估算口径同 estimate_tokens）。

    env ``SCRIBE3_TOTAL_BUDGET``：正整数；``>=900000`` 视为关闭全域裁剪。
    未设时回落 ``get_prompt_hard()``（与 L2 总顶一致）。
    """
    raw = (os.environ.get("SCRIBE3_TOTAL_BUDGET") or "").strip()
    if raw.isdigit():
        return int(raw)
    try:
        return get_prompt_hard()
    except Exception:
        return DEFAULT_TOTAL_PROMPT_BUDGET


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

    while _total() > cap:
        vi = _victim_idx()
        if vi is None:
            break
        name = str(segs[vi].get("name") or "?")
        text = segs[vi].get("text") or ""
        if len(text) > 200:
            segs[vi]["text"] = text[: len(text) // 2] + "…"
            report["dropped"].append(f"{name}:total_half")
        else:
            report["dropped"].append(f"{name}:total_drop")
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
    "prefix": "redline",
    "event_drive": "redline",
    "drama_contract": "redline",
    "envelope": "envelope",
    "codex": "supplemental",
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
    supplemental_hard: int | None = None,
    prompt_hard: int | None = None,
    total_budget: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """生产路径用的段 join：V2 走 L2 裁剪；随后 O1 全域硬顶；V1 仅全域硬顶可选。

    返回 (joined, report)。**禁止**对最终 joined 串尾截。
    active 注册表：``order_names`` 取 ``registry_physical_order_names``，
    真正参与 ``ordered_generation_segments`` 排序（非 no-op）。
    """
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
            supplemental_hard=supplemental_hard,
            prompt_hard=prompt_hard,
        )
        del _joined_l2
        segs = list(l2_rep.get("segments") or segs)

    segs, total_rep = enforce_total_prompt_budget(segs, budget=total_budget)
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
    )
    rep["total_enforce"] = total_rep
    rep["order_source"] = order_source
    rep["registry_active"] = order_source == "injection_registry"
    # 校验 final_reminder 仍在
    names = [str(s.get("name") or "") for s in segs]
    rep["final_reminder_kept"] = "final_reminder" in names
    return joined, rep


def get_codex_inject_cap() -> int:
    raw = (os.environ.get("SCRIBE3_CODEX_INJECT_CAP") or "").strip()
    if raw.isdigit():
        return max(500, int(raw))
    return DEFAULT_CODEX_INJECT_CAP


def get_prompt_hard() -> int:
    if novel_envelope_enabled() and envelope_v2_enabled():
        return NOVEL_PROMPT_HARD
    raw = (os.environ.get("SCRIBE3_PROMPT_HARD") or "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_PROMPT_HARD


def get_supplemental_hard() -> int:
    raw = (os.environ.get("SCRIBE3_SUPPLEMENTAL_HARD") or "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_SUPPLEMENTAL_HARD


def get_supplemental_soft() -> int:
    raw = (os.environ.get("SCRIBE3_SUPPLEMENTAL_SOFT") or "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_SUPPLEMENTAL_SOFT


def estimate_tokens(text: str | None) -> int:
    """与 context_assembler 同口径：len(text) 保守上界。"""
    return len(text or "")


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
    supplemental_hard: int | None = None,
    prompt_hard: int | None = None,
) -> int:
    """effective_L2_cap = min(HARD, PROMPT_HARD - L0 - L1)."""
    hard = DEFAULT_SUPPLEMENTAL_HARD if supplemental_hard is None else int(supplemental_hard)
    ph = DEFAULT_PROMPT_HARD if prompt_hard is None else int(prompt_hard)
    room = max(0, int(ph) - max(0, int(l0_est)) - max(0, int(l1_est)))
    return min(max(0, int(hard)), room)


def physical_order_markers() -> tuple[str, ...]:
    """写路径关键标记（用于序断言 / budget_report）。"""
    return (
        "event_drive",
        "drama_contract",
        "envelope",
        "codex",
        "final_reminder",
    )


def assert_physical_order_indices(indices: dict[str, int]) -> None:
    """indices: domain → first index in assembled string or segment list."""
    ed = indices.get("event_drive")
    dr = indices.get("drama_contract")
    env = indices.get("envelope")
    cx = indices.get("codex")
    fr = indices.get("final_reminder")
    if None in (ed, dr, env, cx, fr):
        missing = [k for k in physical_order_markers() if indices.get(k) is None]
        raise AssertionError(f"missing order markers: {missing}")
    if not (ed < dr < env < cx < fr):
        raise AssertionError(
            f"bad physical order: event_drive={ed} drama={dr} "
            f"envelope={env} codex={cx} final_reminder={fr}"
        )


def apply_l2_trim(
    segments: list[dict[str, Any]],
    *,
    l0_est: int | None = None,
    l1_est: int | None = None,
    supplemental_hard: int | None = None,
    prompt_hard: int | None = None,
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
    soft = get_supplemental_soft()

    def _l2_total() -> int:
        return sum(
            estimate_tokens(s.get("text"))
            for s in segs if s.get("layer") == "supplemental"
        )

    dropped: list[str] = []
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
    while _l2_total() > cap:
        vi = _victim_idx()
        if vi is None:
            break
        name = str(segs[vi].get("name") or "?")
        text = segs[vi].get("text") or ""
        # 尝试尾部裁半；过短则整段丢弃
        if len(text) > 200:
            segs[vi]["text"] = text[: len(text) // 2] + "…"
            dropped.append(f"{name}:tail_half")
        else:
            dropped.append(f"{name}:drop")
            segs.pop(vi)

    # total prompt hard
    def _total() -> int:
        return sum(estimate_tokens(s.get("text")) for s in segs)

    while _total() > ph:
        vi = _victim_idx()
        if vi is None:
            break
        name = str(segs[vi].get("name") or "?")
        dropped.append(f"{name}:prompt_hard_drop")
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
        "prefix",
        "event_drive",
        "drama_contract",
        "drama_vacuum",
    ]
    if outline_after:
        base.append("outline")
    base.append("envelope")
    if v2:
        base.append("codex")
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
        "reference_craft",
        "storyline_polish",  # SL2 · 紧邻 reference_craft 后
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
        "prompt_hard": get_prompt_hard(),
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
