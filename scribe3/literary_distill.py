"""文学蒸馏原型（P2 · O-11 · 无 LLM 启发式）。

把多段 recap 收成可审计决策要点；始终带 raw 以便还原。
**禁止**以 tokens_saved / 成本作控制开关。
``SCRIBE3_LITERARY_DISTILL`` 默认关；关时函数仍可调用（纯原型）。
"""
from __future__ import annotations

import os
import re
from typing import Any

# 控制面明确排除的 KPI 名（测试可扫此集合）
DISTILL_FORBIDDEN_KPIS: frozenset[str] = frozenset({
    "tokens_saved",
    "token_saved",
    "cost_usd",
    "cost_cny",
    "api_cost",
})


def literary_distill_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_LITERARY_DISTILL") or "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def _classify_bullet(para: str) -> str:
    """启发式标签：paid_off | open_cost | attitude | beat。"""
    p = para.lower()
    if any(k in para for k in ("代价", "成本", "失去", "牺牲", "伤口", "cost")):
        return "open_cost"
    if any(k in para for k in ("态度", "心境", "决定", "不再", "终于", "改变", "决心")):
        return "attitude"
    if any(k in para for k in ("解决", "了结", "还清", "兑现", "落幕", "paid", "收束")):
        return "paid_off"
    if any(k in p for k in ("conflict", "对抗", "冲突", "对峙")):
        return "paid_off"
    return "beat"


def literary_distill(recap: str, *, max_bullets: int = 12) -> dict[str, Any]:
    """多段 recap → 结构化 bullets + raw/audit。

    控制路径不读 tokens_saved；audit 标明 not_a_kpi。
    """
    raw = recap or ""
    paras = _split_paragraphs(raw)
    if not paras and raw.strip():
        paras = [raw.strip()]
    bullets: list[dict[str, Any]] = []
    for i, para in enumerate(paras[: max(1, int(max_bullets))]):
        # 压成一行要点
        line = re.sub(r"\s+", " ", para).strip()
        if len(line) > 160:
            line = line[:157] + "…"
        kind = _classify_bullet(para)
        bullets.append({
            "index": i,
            "kind": kind,
            "text": line,
        })
    return {
        "bullets": bullets,
        "raw": raw,
        "audit": {
            "paragraph_count": len(paras),
            "bullet_count": len(bullets),
            "source": "literary_distill.heuristic_v0",
            "revert": "use field raw",
            "not_a_kpi": "tokens_saved",
            "forbidden_kpis": sorted(DISTILL_FORBIDDEN_KPIS),
        },
        "control": {
            "flag": literary_distill_enabled(),
            "uses_tokens_saved": False,
            "not_a_kpi": "tokens_saved",
        },
        "mode": "advisory_prototype",
    }
