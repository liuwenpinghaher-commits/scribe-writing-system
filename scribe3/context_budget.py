# scribe3/context_budget.py
"""Novel-first 写路径预算与 L2 裁剪纯函数（无 I/O · 可单测）。

第一原则：戏剧信号密度 / 注意力质量；禁止以 tokens_saved 为 KPI。
设计：docs/plans/2026-08-11-novel-first-injection-quality-optimal.md rev.3.1
"""
from __future__ import annotations

import os
from typing import Any, Iterable

# ── 现网默认（V1 · flag 关）──────────────────────────────────────────
BLOCK_BUDGETS_V1: dict[str, int] = {
    "focus": 800,
    "global": 1200,
    "canonical": 2800,
    "recent": 1600,
    "procedural": 900,
    "reference": 1400,
    "uncertainty": 500,
    "provenance": 800,
}
DEFAULT_ENVELOPE_TOKEN_BUDGET_V1 = 10_000
assert sum(BLOCK_BUDGETS_V1.values()) == DEFAULT_ENVELOPE_TOKEN_BUDGET_V1

# ── Novel-first 目标表（V2 · flag 开）────────────────────────────────
BLOCK_BUDGETS_V2: dict[str, int] = {
    "focus": 1000,
    "global": 1600,
    "canonical": 6800,
    "recent": 4000,
    "procedural": 1200,
    "reference": 1600,
    "uncertainty": 800,
    "provenance": 1000,
}
DEFAULT_ENVELOPE_TOKEN_BUDGET_V2 = 18_000
assert sum(BLOCK_BUDGETS_V2.values()) == DEFAULT_ENVELOPE_TOKEN_BUDGET_V2

# Novel 可选再抬（仅 high-signal 块；须同步 PROMPT_HARD=48k）
BLOCK_BUDGETS_NOVEL: dict[str, int] = {
    "focus": 1000,
    "global": 1800,
    "canonical": 8600,
    "recent": 5600,
    "procedural": 1400,
    "reference": 1800,
    "uncertainty": 800,
    "provenance": 1000,
}
NOVEL_ENVELOPE_TOKEN_BUDGET = 22_000
assert sum(BLOCK_BUDGETS_NOVEL.values()) == NOVEL_ENVELOPE_TOKEN_BUDGET

DEFAULT_CODEX_INJECT_CAP = 4_500
DEFAULT_SUPPLEMENTAL_SOFT = 14_000
DEFAULT_SUPPLEMENTAL_HARD = 18_000
DEFAULT_PROMPT_HARD = 42_000
NOVEL_PROMPT_HARD = 48_000

# L2 可裁段优先级（数字越大越先丢）
L2_DROP_PRIORITY: dict[str, int] = {
    "material_recall": 90,
    "reference_craft": 85,
    "author_prefs": 80,
    "seed_words": 75,
    "craft": 70,
    "pressure_drive": 60,
    "brief_must": 55,
    "volume_intro": 50,
    "outline": 40,
    "purpose": 35,
    "phase_role": 30,
    "avoid": 28,
    "codex": 25,  # 已有 cap；仍可进一步裁
    "request_constraint": 20,
}

# 永不作为 L2 victim
L0_NEVER_CUT: frozenset[str] = frozenset({
    "identity", "write_protocol", "revision", "anti_slop",
    "continue_snapshot", "secret_guard", "request_position",
    "tool_scope", "craft_skills_index", "focalizer",
    "event_drive", "drama_contract", "envelope",
    "revelation_discipline", "sincerity", "final_reminder",
    "deduction_final", "scene_truth_proj",
})


def _env_truthy(name: str, default: str = "0") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw in ("1", "true", "yes", "on")


def envelope_v2_enabled() -> bool:
    """生产默认关：仅接线后仍 10k，直至物理序+L2 同列车打开。"""
    return _env_truthy("SCRIBE3_ENVELOPE_V2_ENABLE", "0")


def novel_envelope_enabled() -> bool:
    return _env_truthy("SCRIBE3_ENVELOPE_NOVEL", "0")


def get_block_budgets() -> dict[str, int]:
    if novel_envelope_enabled() and envelope_v2_enabled():
        return dict(BLOCK_BUDGETS_NOVEL)
    if envelope_v2_enabled():
        return dict(BLOCK_BUDGETS_V2)
    return dict(BLOCK_BUDGETS_V1)


def get_envelope_token_budget() -> int:
    budgets = get_block_budgets()
    total = sum(budgets.values())
    # 允许 env 覆盖总额（仍要求与块表一致时由调用方 assert）
    override = (os.environ.get("SCRIBE3_ENVELOPE_TOKEN_BUDGET") or "").strip()
    if override.isdigit():
        return int(override)
    return total


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
        for i, s in enumerate(segs):
            if s.get("layer") != "supplemental":
                continue
            name = str(s.get("name") or "")
            if name in L0_NEVER_CUT:
                continue
            pri = L2_DROP_PRIORITY.get(name, 55)
            if pri > best_pri:
                best_pri = pri
                best_i = i
        return best_i

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
        "envelope_v2": envelope_v2_enabled(),
        "signal_density_note": "primary metric is drama signal density, not tokens_saved",
    }
    return joined, report


def generation_physical_order_names(*, v2: bool = True) -> list[str]:
    """目标物理序域名列表（V2）；供单测与 report 对照。"""
    base = [
        "prefix",
        "event_drive",
        "drama_contract",
        "envelope",
    ]
    if v2:
        base.append("codex")
    base.extend([
        "seed_words",
        "craft",
        "phase_role",
        "avoid",
        "revelation_discipline",
        "sincerity",
        "purpose",
        "outline",
        "volume_intro",
        "brief_must",
        "pressure_drive",
        "author_prefs",
        "final_reminder",
    ])
    return base


def build_budget_report(
    *,
    domain_lengths: dict[str, int] | None = None,
    order_indices: dict[str, int] | None = None,
    l2_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """观测报告（不含成本 KPI）。"""
    return {
        "envelope_token_budget": get_envelope_token_budget(),
        "block_budgets": get_block_budgets(),
        "envelope_v2_enabled": envelope_v2_enabled(),
        "codex_inject_cap": get_codex_inject_cap(),
        "domain_lengths": dict(domain_lengths or {}),
        "order_indices": dict(order_indices or {}),
        "l2": dict(l2_report or {}),
        "primary_metric": "signal_density_for_drama",
        "not_a_kpi": "tokens_saved",
    }
