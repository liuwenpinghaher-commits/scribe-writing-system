#!/usr/bin/env python3
"""H11：预算头寸采样（无 Surreal · 纯 env+context_budget）。

用法::

  PYTHONPATH=. python -m scribe3.tools.sample_budget_report \\
    --out /tmp/budget_sample.json

可选对 demo 已部署 API 打 assemble 需另传 --url（默认仅本地表）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def sample_local(*, beat_type: str | None = "dialogue") -> dict:
    """从 context_budget 采样 L0/L1/L2 头寸（不连库）。"""
    # 确保 novel 默认路径可复现
    os.environ.setdefault("SCRIBE3_ENVELOPE_V2_ENABLE", "1")
    os.environ.setdefault("SCRIBE3_ENVELOPE_NOVEL", "1")
    os.environ.setdefault("SCRIBE3_ADAPTIVE_BUDGET", "1")

    from scribe3.context_budget import (
        BLOCK_BUDGETS_NOVEL,
        NOVEL_ENVELOPE_TOKEN_BUDGET,
        NOVEL_PROMPT_HARD,
        build_budget_report,
        context_fidelity,
        get_block_budgets,
        get_envelope_token_budget,
        get_prompt_hard,
        get_total_prompt_budget,
    )

    bb = get_block_budgets(beat_type=beat_type)
    rep = build_budget_report(beat_type=beat_type)
    env = get_envelope_token_budget()
    hard = get_prompt_hard()
    total = get_total_prompt_budget()
    # 粗分：envelope≈L1 域预算；prompt_hard - envelope ≈ L2 头寸
    l1 = env
    l2_room = max(0, hard - env)
    effective_l2 = l2_room  # 简化：未跑真实 assemble 时用硬顶差
    conclusion = (
        "48k 头寸够用（novel 22k envelope + L2 余量）"
        if hard >= NOVEL_PROMPT_HARD and env >= NOVEL_ENVELOPE_TOKEN_BUDGET * 0.95
        else "头寸偏紧或 fidelity 非 novel，请查 env"
    )
    return {
        "fidelity": context_fidelity(),
        "beat_type": beat_type,
        "block_budgets": bb,
        "block_sum": sum(bb.values()),
        "novel_base_sum": sum(BLOCK_BUDGETS_NOVEL.values()),
        "L0_note": "redline/L0 永不整段丢（见 L0_NEVER_CUT）",
        "L1_envelope": l1,
        "L2_room_est": l2_room,
        "effective_L2_est": effective_l2,
        "prompt_hard": hard,
        "total_prompt_budget": total,
        "budget_report_keys": sorted(rep.keys()),
        "registry_mode": rep.get("registry_mode"),
        "adaptive_profile": rep.get("adaptive_profile"),
        "event_graph_k": (rep.get("event_graph") or {}).get("k"),
        "conclusion": conclusion,
        "primary_metric": "signal_density_for_drama",
        "not_a_kpi": "tokens_saved",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="sample budget report headroom")
    ap.add_argument("--out", default="", help="write JSON path")
    ap.add_argument("--beat-type", default="dialogue")
    args = ap.parse_args(argv)
    data = sample_local(beat_type=args.beat_type or None)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(f"# wrote {p}", file=sys.stderr)
    print(f"# conclusion: {data['conclusion']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
