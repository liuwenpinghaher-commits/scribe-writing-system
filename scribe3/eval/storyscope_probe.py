"""StoryScope 探针：量人机差落在哪个维度，回答「放弃文笔改做设定」是否成立。

数据集不在仓库里（802MB），默认找 ~/Downloads/storyscope_full，用 --root 改。
61575 行 = 10239 人类 + 五个模型各约 10260，同一批 prompt 配对。
人类正文因版权未附，只有 304 个特征的标注值，够做分布比较。

两种量法：
  TVD  某特征上人类分布与模型分布的全变差距离，0=重合，1=完全不重合。
       看「哪一条写法机器和人不一样」。
  AUC  只喂某几维特征训分类器，看能多准地识破 AI。
       看「藏在这一层里，AI 还剩多少痕迹」。

TVD 大不等于 AUC 高：单项差得狠但只此一项，分类器未必抓得住；
反过来一堆小差累加也能把 AUC 顶上去。两个都要看。

用法：
    python -m scribe3.eval.storyscope_probe --tvd
    python -m scribe3.eval.storyscope_probe --auc          # 慢，约 1 分钟
    python -m scribe3.eval.storyscope_probe --dim setting
    python -m scribe3.eval.storyscope_probe --model deepseek

结论落在 docs/craft-evidence/storyscope.md，改动本文件后请同步那份。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_ROOT = Path.home() / "Downloads" / "storyscope_full"
MODELS = ("gpt", "claude", "deepseek", "kimi", "gemini")
# 设定骨架：世界怎么搭 + 事情怎么排 + 消息怎么放。不含 style/agents/situatedness。
SKELETON = ("setting", "temporal_structure", "events", "revelation", "plot")


def load(root: Path):
    tax = json.loads((root / "taxonomy.json").read_text())["feature_taxonomy"]
    meta = {}
    for dim, d in tax.items():
        for a in d["aspects"].values():
            for feat in a["features"]:
                meta[feat["id"]] = dict(feat, dim=dim, aspect=a["aspect_name"])
    f = pd.read_parquet(root / "storyscope_features.parquet")
    feats = [c for c in f.columns if c in meta]
    return f, meta, feats


def _dist(s: pd.Series) -> pd.Series:
    vc = s.value_counts(dropna=True)
    return vc / vc.sum()


def tvd_table(f, meta, feats) -> pd.DataFrame:
    """每个特征上，各模型与人类的全变差距离。"""
    sub = {s: f[f["source"] == s] for s in ("human",) + MODELS}
    rows = []
    for c in feats:
        ds = {s: _dist(sub[s][c]) for s in sub}
        keys = sorted(set().union(*(set(d.index) for d in ds.values())))
        H = np.array([ds["human"].get(k, 0.0) for k in keys])
        rec = {"fid": c, "dim": meta[c]["dim"], "name": meta[c]["name"]}
        for m in MODELS:
            M = np.array([ds[m].get(k, 0.0) for k in keys])
            rec[m] = float(0.5 * np.abs(H - M).sum())
        rec["ai_mean"] = float(np.mean([rec[m] for m in MODELS]))
        rec["_dists"] = ds
        rec["_keys"] = keys
        rows.append(rec)
    return pd.DataFrame(rows)


def auc_by_group(f, feats, meta, groups: dict[str, list[str]]) -> dict[str, float]:
    """只喂 groups 里的特征训 AI 判别器，AUC 越高＝这一层里 AI 痕迹越重。"""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split

    def cap(s, k=200):
        """multi_select 特征基数上千，HistGBM 只吃 255 类，长尾并成 __other__。"""
        s = s.astype(str)
        top = s.value_counts().index[:k]
        return s.where(s.isin(top), "__other__").astype("category")

    cat = f[feats].apply(cap)
    y = (f["source"] != "human").astype(int).values
    tr, te = train_test_split(np.arange(len(f)), test_size=0.25, random_state=0, stratify=y)
    out = {}
    for tag, cols in groups.items():
        if not cols:
            continue
        clf = HistGradientBoostingClassifier(
            max_iter=200, max_depth=6, learning_rate=0.1, random_state=0,
            categorical_features="from_dtype", early_stopping=True, n_iter_no_change=15,
        )
        clf.fit(cat.iloc[tr][cols], y[tr])
        p = clf.predict_proba(cat.iloc[te][cols])[:, 1]
        out[tag] = float(roc_auc_score(y[te], p))
        print(f"  {tag:<28} n={len(cols):>3}  AUC={out[tag]:.4f}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--tvd", action="store_true", help="维度汇总 + 全局 TOP 差异项")
    ap.add_argument("--auc", action="store_true", help="判别力实验，约 1 分钟")
    ap.add_argument("--dim", help="单个维度全部特征的三方分布")
    ap.add_argument("--model", help="某个模型的专项偏离，如 deepseek")
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()
    if not any((args.tvd, args.auc, args.dim, args.model)):
        args.tvd = True

    f, meta, feats = load(args.root)
    R = tvd_table(f, meta, feats)

    if args.tvd:
        print("\n## 维度汇总（TVD 均值，越大＝人机写法差越远）\n")
        g = R.groupby("dim")[list(MODELS) + ["ai_mean"]].mean().sort_values("ai_mean", ascending=False)
        print(g.round(3).to_string())
        print(f"\n## 全局 TOP {args.top} 差异项\n")
        for _, r in R.sort_values("ai_mean", ascending=False).head(args.top).iterrows():
            print(f"{r['fid']:>14} {r['dim']:<18} TVD={r['ai_mean']:.3f} | {r['name']}")

    if args.dim:
        print(f"\n## {args.dim} 全部特征 · 人 vs deepseek vs claude\n")
        for _, r in R[R.dim == args.dim].sort_values("ai_mean", ascending=False).iterrows():
            ds = r["_dists"]
            print(f"\n{r['fid']} TVD={r['ai_mean']:.3f} | {r['name']}")
            print(f"  Q: {meta[r['fid']].get('question','')[:140]}")
            for k in sorted(r["_keys"], key=lambda k: -ds["human"].get(k, 0))[:6]:
                print(f"    {str(k)[:56]:<56} 人{ds['human'].get(k,0):6.1%}"
                      f" ds{ds['deepseek'].get(k,0):6.1%} cl{ds['claude'].get(k,0):6.1%}")

    if args.model:
        m = args.model
        rest = [x for x in MODELS if x != m]
        R["excess"] = R[m] - R[rest].mean(axis=1)
        print(f"\n## {m} 比其他四个模型更偏离人类的 TOP {args.top}\n")
        for _, r in R.sort_values("excess", ascending=False).head(args.top).iterrows():
            ds = r["_dists"]
            print(f"+{r['excess']:.3f} {r['fid']:>14} {r['dim']:<18} {m}={r[m]:.3f} | {r['name']}")
            for k in sorted(r["_keys"], key=lambda k: -abs(ds["human"].get(k, 0) - ds[m].get(k, 0)))[:2]:
                print(f"{'':>8} '{str(k)[:60]}': 人 {ds['human'].get(k,0):.1%} / {m} {ds[m].get(k,0):.1%}")

    if args.auc:
        d2f = dict(zip(R.fid, R.dim))
        groups = {"全部 304 特征": feats}
        for d in sorted(set(R.dim)):
            groups[f"只用 {d}"] = [c for c in feats if d2f[c] == d]
        groups["去掉 style"] = [c for c in feats if d2f[c] != "style"]
        groups["设定骨架5维"] = [c for c in feats if d2f[c] in SKELETON]
        for pre, tag in (("SET_LOC", "setting·空间结构"), ("SET_ATM", "setting·氛围"), ("SET_TIM", "setting·时间")):
            groups[tag] = [c for c in feats if c.startswith(pre)]
        print("\n## 判别力：藏在这一层里，AI 还剩多少痕迹\n")
        auc_by_group(f, feats, meta, groups)


if __name__ == "__main__":
    main()
