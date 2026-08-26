"""Blind-judge existing system cards against gold; compare to mechanical R1.

Does not re-extract. Does not change score_r1. Holdout gold is the answer key.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scribe3.eval import verify_holdout_hash
from scribe3.eval.card_schema import R1_HARD_FIELDS
from scribe3.eval.extract_card import parse_card
from scribe3.eval.pool import run_jobs
from scribe3.eval.run_r1 import live_complete, unwrap_md
from scribe3.eval.score_r1 import load_label_card, score_pair, scored_seqs

EVAL = Path(__file__).resolve().parent


def _prompt(seq: int, pred_md: str, gold_md: str) -> str:
    pred, gold = parse_card(pred_md), parse_card(gold_md)
    blocks = []
    for name in R1_HARD_FIELDS:
        blocks.append(
            f"### {name}\n金卡：\n{(gold.get(name) or '')[:900]}\n\n系统卡：\n{(pred.get(name) or '')[:900]}"
        )
    joined = "\n\n".join(blocks)
    return f"""你只做对照，不改分数规则。判断系统卡五个硬字段是否与金卡说的是同一件事。
每行一个字段，格式严格为：字段名<TAB>是 或 字段名<TAB>否。不要解释，不要其它行。

序号 {seq}。

{joined}
"""


def parse_blind(text: str) -> dict[str, bool | None]:
    out: dict[str, bool | None] = {name: None for name in R1_HARD_FIELDS}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            name, _, ans = line.partition("\t")
        elif "：" in line:
            name, _, ans = line.partition("：")
        elif ":" in line:
            name, _, ans = line.partition(":")
        else:
            continue
        name, ans = name.strip(), ans.strip()
        for field in R1_HARD_FIELDS:
            if field in name or name in field:
                if ans.startswith("是") or ans.lower() in {"yes", "true", "1"}:
                    out[field] = True
                elif ans.startswith("否") or ans.lower() in {"no", "false", "0"}:
                    out[field] = False
                break
    return out


def run_blind(
    *,
    complete_fn,
    pred_dir: Path | None = None,
    out_path: Path | None = None,
    jobs: int = 1,
) -> dict:
    holdout_hash = verify_holdout_hash()
    cards = Path(pred_dir) if pred_dir is not None else EVAL / "preds" / "r1_before"
    dest = Path(out_path) if out_path is not None else EVAL / "blind_r1_before.json"
    todo = [s for s in scored_seqs() if (cards / f"{s}.md").exists()]
    collected: list[dict | None] = [None] * len(todo)

    def work(_i: int, seq: int) -> dict:
        pred_md = (cards / f"{seq}.md").read_text(encoding="utf-8")
        gold_md = load_label_card(seq)
        mech = score_pair(pred_md, gold_md)
        raw = unwrap_md(complete_fn(_prompt(seq, pred_md, gold_md)))
        blind = parse_blind(raw)
        fields = {}
        hits = 0
        n = 0
        agree = 0
        for name in R1_HARD_FIELDS:
            b = blind[name]
            m = bool(mech["fields"][name]["ok"])
            if b is not None:
                n += 1
                hits += int(b)
                agree += int(b == m)
            fields[name] = {"blind": b, "mechanical": m, "agree": b == m if b is not None else None}
        return {
            "seq": seq,
            "mechanical_score": mech["score"],
            "blind_score": hits / n if n else None,
            "agree_n": agree,
            "judged_n": n,
            "fields": fields,
        }

    def done(i: int, seq: int, row: dict | None, err: BaseException | None) -> None:
        if err is not None:
            print(f"BLIND {seq} FAIL {type(err).__name__}: {err}", flush=True)
            return
        collected[i] = row
        print(f"BLIND {seq} mech={row['mechanical_score']} blind={row['blind_score']}", flush=True)

    run_jobs(todo, work, jobs=jobs, on_done=done)
    rows = [r for r in collected if r is not None]
    judged = [r for r in rows if r["judged_n"]]
    agree = sum(r["agree_n"] for r in judged)
    judged_n = sum(r["judged_n"] for r in judged)
    blind_scores = [r["blind_score"] for r in judged if r["blind_score"] is not None]
    doc = {
        "label": "r1_before",
        "holdout_sha256": holdout_hash,
        "n": len(rows),
        "mechanical_mean": round(sum(r["mechanical_score"] for r in rows) / len(rows), 4) if rows else 0.0,
        "blind_mean": round(sum(blind_scores) / len(blind_scores), 4) if blind_scores else None,
        "agree_rate": round(agree / judged_n, 4) if judged_n else None,
        "rows": rows,
    }
    dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser()
    p.add_argument("--jobs", type=int, default=4)
    args = p.parse_args(argv)
    return run_blind(complete_fn=live_complete, jobs=args.jobs)


if __name__ == "__main__":
    out = main()
    print(json.dumps(
        {"n": out["n"], "mechanical_mean": out["mechanical_mean"], "blind_mean": out["blind_mean"], "agree_rate": out["agree_rate"]},
        ensure_ascii=False,
    ))
