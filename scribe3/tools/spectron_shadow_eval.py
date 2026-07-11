#!/usr/bin/env python3
"""Spectron 影子对比评测 CLI(Task 15 · Step 5)。

作用:把 Spectron 只读影子跑在自建检索旁边做对比,产出对比报告 —— 但**不产生任何
生产写入、绝不替换生产结果**。两个官方包(surrealdb[spectron] +
spectron_integration_hermes_agent)截至交付日均未在 PyPI 发布,故本工具在当前环境
恒输出 `enabled=false, reason=sdk_or_integration_missing` 并 **exit 0**;只有显式
`--require-available` 才因不可用 **exit 2**(供 CI 在"要求已发布"的门禁里用)。

用法:
  scribe3/.venv/bin/python scribe3/tools/spectron_shadow_eval.py \
      --gold scribe3/tests/fixtures/context_memory_gold.json \
      --output /tmp/scribe3-spectron-shadow.json

设计取舍(诚实):
- 包未发布时**不读 gold 也能 exit 0**——直接短路成 disabled 报告,gold 缺失/坏
  JSON 都不影响退出码,不吐裸 traceback。
- 包发布后(enabled 路径)才真正遍历 gold 做影子观测;但把影子候选传给"生产检索"
  做逐例对比,依赖自建检索的生产调用方,属 **Task 16 检索接线**。在此之前 enabled
  路径也只能记录 shadow 观测(无客户端 → no_spectron_client),仍不写生产。
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

# 允许以脚本方式(python scribe3/tools/spectron_shadow_eval.py)运行:补 repo 根到 sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scribe3.spectron_adapter import (  # noqa: E402
    DEFAULT_SAMPLE_RATE,
    AdoptionMetrics,
    SpectronShadowAdapter,
    adoption_gate,
    detect_spectron,
)

DEFAULT_GOLD_PATH = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "context_memory_gold.json"
)


def _disabled_report(availability, adoption) -> dict:
    """包未发布时的 disabled 报告:诚实标注恒关 + 生产结果永不受影响。"""
    return {
        "spectron": {
            "enabled": availability.enabled,
            "reason": availability.reason,
            "sdk_version": availability.sdk_version,
            "integration_version": availability.integration_version,
        },
        "shadow_ran": False,
        "shadow_observations": 0,
        "shadow_errors": [],
        "note": (
            "官方包 surrealdb[spectron] / spectron_integration_hermes_agent 未发布,"
            "影子流恒关;生产检索结果永不受影响。影子采样的生产集成待 Task 16 检索接线。"
        ),
        "adoption": {
            "can_adopt": adoption.can_adopt,
            "unmet": list(adoption.unmet),
            "checks": adoption.checks,
        },
    }


def _shadow_report(availability, adapter: SpectronShadowAdapter, cases, adoption) -> dict:
    """enabled 路径:遍历 gold 做只读影子观测(客户端待接线时多为 no_spectron_client)。

    只记候选 id/排名/延迟/溯源完整性与 shadow error,决不把 context 传生产 LLM、
    决不替换生产结果。逐例"影子 vs 主路"打分对比属 Task 16 检索接线,后续补齐。
    """
    observations = []
    for case in cases:
        obs = adapter.observe(case.get("query", ""), force_sample=True)
        observations.append({
            "case_id": case.get("id"),
            "ran": obs.ran,
            "error": obs.error,
            "candidate_ids": list(obs.candidate_ids),
            "latency_ms": obs.latency_ms,
            "provenance_complete": obs.provenance_complete,
        })
    return {
        "spectron": {
            "enabled": availability.enabled,
            "reason": availability.reason,
            "sdk_version": availability.sdk_version,
            "integration_version": availability.integration_version,
        },
        "shadow_ran": any(o["ran"] for o in observations),
        "shadow_observations": len(observations),
        "shadow_errors": adapter.errors,
        "observations": observations,
        "note": (
            "影子只读对比:未把候选传生产 LLM、未替换生产结果。逐例 nDCG 对比与生产采样"
            "接线属 Task 16。"
        ),
        "adoption": {
            "can_adopt": adoption.can_adopt,
            "unmet": list(adoption.unmet),
            "checks": adoption.checks,
        },
    }


def _load_cases(gold_path: str) -> list[dict]:
    """尽力读 gold;读不到/坏 JSON 一律返回空列表(disabled 路径根本不调用它)。"""
    try:
        raw = json.loads(Path(gold_path).read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spectron 影子对比评测(只读,不写生产)")
    parser.add_argument("--gold", default=str(DEFAULT_GOLD_PATH), help="黄金集 JSON 路径")
    parser.add_argument("--output", default=None, help="对比报告 JSON 输出路径")
    parser.add_argument("--sample-rate", type=float, default=DEFAULT_SAMPLE_RATE,
                        help="影子采样率(默认 0.10;CLI 逐例观测用 force_sample 全采)")
    parser.add_argument("--require-available", action="store_true",
                        help="要求官方包已发布;不可用时 exit 2(默认不可用也 exit 0)")
    args = parser.parse_args(argv)

    availability = detect_spectron()

    # 当前采用度量:包可用性直接来自 detect;其余度量待真实观测期填入,现全默认(不合格)。
    metrics = AdoptionMetrics(
        packages_available=availability.enabled,
        versions_lockable=bool(availability.sdk_version and availability.integration_version),
    )
    adoption = adoption_gate(metrics)

    if not availability.enabled:
        # 恒关正确态:不读 gold 也能 exit 0(--require-available 时 exit 2)。
        report = _disabled_report(availability, adoption)
    else:
        cases = _load_cases(args.gold)
        adapter = SpectronShadowAdapter(availability=availability, sample_rate=args.sample_rate)
        report = _shadow_report(availability, adapter, cases, adoption)

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "enabled": availability.enabled,
        "reason": availability.reason,
        "shadow_ran": report["shadow_ran"],
        "can_adopt": adoption.can_adopt,
        "unmet": list(adoption.unmet),
    }, ensure_ascii=False, indent=2))
    # 冗余打印一行可 grep 的状态(测试与 CI 用)
    print(f"enabled={str(availability.enabled).lower()} reason={availability.reason} "
          f"can_adopt={str(adoption.can_adopt).lower()}")

    if args.require_available and not availability.enabled:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
