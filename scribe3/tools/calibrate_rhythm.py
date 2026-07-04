#!/usr/bin/env python3
"""句长方差/burstiness 检测器(find_rhythm_uniformity)真机标定脚本(方案A任务6)。

经 REST 拉取各 work 已存章节正文,逐章跑 find_rhythm_uniformity,打印
{work, chapter, cv, mean_adj_ratio, n_sentences},末尾汇总 CV / mean_adj_ratio
的 P10/P50/P90 分位数,供人工判断 critique.py 里 _RHYTHM_CV_FLOOR /
_RHYTHM_ADJ_FLOOR 两个临时阈值是否需要回填。

后端(:3321)不在线时打印提示、exit(0)——不算失败(标定是锦上添花,不阻塞 CI)。
"""
import sys
import os
import math

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scribe3.critique import find_rhythm_uniformity  # noqa: E402

BASE = "http://127.0.0.1:3321"


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
        print("_RHYTHM_CV_FLOOR/_RHYTHM_ADJ_FLOOR 保留 critique.py 里的现有阈值(未重新标定)。")
        return 0

    try:
        works = requests.get(f"{BASE}/works", timeout=10).json()
    except requests.exceptions.RequestException as e:
        print(f"GET /works 失败,跳过真机标定:{e}")
        return 0

    cvs: list[float] = []
    adj_ratios: list[float] = []
    n_judged = 0
    n_skipped = 0

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
            if not prose:
                continue
            result = find_rhythm_uniformity(prose)
            if result is None:
                n_skipped += 1
                print(f"{{work: {slug}, chapter: {seq}, verdict: skipped(句数不足)}}")
                continue
            n_judged += 1
            cvs.append(result["cv"])
            adj_ratios.append(result["mean_adj_ratio"])
            print(f"{{work: {slug}, chapter: {seq}, cv: {result['cv']}, "
                  f"mean_adj_ratio: {result['mean_adj_ratio']}, "
                  f"n_sentences: {result['n_sentences']}, verdict: {result['verdict']}}}")

    print()
    print(f"=== 汇总:{n_judged} 章已判定,{n_skipped} 章句数不足未判 ===")
    if not cvs:
        print("无可用样本(全书均无正文或句数均不足),保留 critique.py 里的现有阈值(未重新标定)。")
        return 0

    cvs.sort()
    adj_ratios.sort()
    cv_p10, cv_p50, cv_p90 = (_percentile(cvs, p) for p in (0.10, 0.50, 0.90))
    adj_p10, adj_p50, adj_p90 = (_percentile(adj_ratios, p) for p in (0.10, 0.50, 0.90))
    print(f"CV             P10={cv_p10:.3f}  P50={cv_p50:.3f}  P90={cv_p90:.3f}")
    print(f"mean_adj_ratio P10={adj_p10:.3f}  P50={adj_p50:.3f}  P90={adj_p90:.3f}")
    uniform_n = sum(1 for cv, adj in zip(cvs, adj_ratios) if cv < cv_p10 and adj < adj_p10)
    print()
    print("标定建议:取 P10(约一成已验收章节比该值更'均匀')作为 uniform 判定的新地板值——"
          "比公开检测器文献区间的临时值更贴近本系统真实文风。以此地板值复核这批样本,"
          f"预期约一成(实测 {uniform_n}/{len(cvs)})会落在边界以下被判 uniform,"
          "这是 P10 定义的应有结果,非误判;report-only/advisory 性质,可接受:")
    print(f"  _RHYTHM_CV_FLOOR  = {cv_p10:.3f}   (原临时值 0.38)")
    print(f"  _RHYTHM_ADJ_FLOOR = {adj_p10:.3f}   (原临时值 0.45)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
