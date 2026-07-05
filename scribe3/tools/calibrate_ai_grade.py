#!/usr/bin/env python3
"""整章 AI 味定档聚合(aggregate_ai_grade)6 指标真机标定脚本(真机冒烟修复配套,2026-07-04)。

背景:真机冒烟对 6 个已人工验收达标章跑 aggregate_ai_grade,全部误判 grade=heavy——
罪魁是 parallel_run 语义 bug(见 critique.py aggregate_ai_grade ②parallel_run 计算处
注释:find_structural_repeats 的 anaphora/short count 是"全章总命中条数",被误当"最大
连排数"喂给 parallel_run;已改为只采信 find_parallelism 的真连排计数)。语义修好后,
_AI_GRADE_* 六组阈值仍是"临时标定,先把骨架跑通"的宽松占位值,需要真机重标定。

本脚本:经 REST 拉取各 work 已存章节正文,逐章跑 quality_flags + aggregate_ai_grade,
打印 6 指标 {value, tier},汇总每项指标的 P50/P90/P99 分位数,供人工回填 critique.py
里的 _AI_GRADE_*_LIGHT/_MEDIUM 六对常量。

后端(:3321)不在线时打印提示、exit(0)——不算失败(标定是锦上添花,不阻塞 CI)。
"""
import sys
import os
import math

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scribe3.critique import aggregate_ai_grade, quality_flags  # noqa: E402

BASE = "http://127.0.0.1:3321"

INDICATOR_NAMES = ("banned_density", "parallel_run", "psych_ratio",
                   "dialogue_tag_density", "repeat_density")
# rhythm_uniform 是二值枚举(ok/uniform),不参与分位数统计,单独计数。


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    """线性插值分位数(与 numpy 默认 percentile 同口径)。sorted_vals 须已升序。"""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def main() -> int:
    try:
        r = requests.get(f"{BASE}/health", timeout=2)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"后端({BASE})不在线,跳过真机标定:{e}")
        print("_AI_GRADE_* 六组阈值保留 critique.py 里的现有值(未重新标定)。")
        return 0

    try:
        works = requests.get(f"{BASE}/works", timeout=10).json()
    except requests.exceptions.RequestException as e:
        print(f"GET /works 失败,跳过真机标定:{e}")
        return 0

    samples: dict[str, list[float]] = {name: [] for name in INDICATOR_NAMES}
    uniform_count = 0
    n_judged = 0

    for w in works:
        slug = w.get("slug")
        try:
            chapters = requests.get(f"{BASE}/chapters", params={"work": slug}, timeout=10).json()
        except requests.exceptions.RequestException as e:
            print(f"[{slug}] GET /chapters 失败,跳过此 work:{e}")
            continue
        for ch in chapters:
            seq = ch.get("seq")
            try:
                data = requests.get(f"{BASE}/chapter", params={"seq": seq, "work": slug}, timeout=10).json()
            except requests.exceptions.RequestException as e:
                print(f"[{slug}] 章{seq} GET /chapter 失败,跳过:{e}")
                continue
            prose = data.get("prose") or ""
            if not prose.strip():
                continue
            flags = quality_flags(prose)
            g = aggregate_ai_grade(flags, prose)
            n_judged += 1
            ind = g["indicators"]
            for name in INDICATOR_NAMES:
                samples[name].append(ind[name]["value"])
            if ind["rhythm_uniform"]["value"] == "uniform":
                uniform_count += 1
            tiers = {name: ind[name]["tier"] for name in INDICATOR_NAMES}
            values_str = ", ".join(f"{k}={ind[k]['value']}" for k in INDICATOR_NAMES)
            print(f"{{work: {slug}, chapter: {seq}, grade: {g['grade']}, "
                  f"values: {{{values_str}}}, tiers: {tiers}}}")

    print()
    print(f"=== 汇总:{n_judged} 章已判定,rhythm_uniform=uniform 命中 {uniform_count} 章 ===")
    if n_judged == 0:
        print("无可用样本(全书均无正文),保留 critique.py 里的现有阈值(未重新标定)。")
        return 0

    print()
    print("标定建议(以 P90 作为'中'档上界、P99 或明显离群值作为'重'档下界——")
    print("样本是当前系统里全部已存章节,不是刻意挑选的干净样本):")
    for name in INDICATOR_NAMES:
        vals = sorted(samples[name])
        p50, p90, p99 = (_percentile(vals, p) for p in (0.50, 0.90, 0.99))
        vmax = vals[-1]
        print(f"  {name:22s} n={len(vals):3d}  P50={p50:.2f}  P90={p90:.2f}  "
              f"P99={p99:.2f}  max={vmax:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
