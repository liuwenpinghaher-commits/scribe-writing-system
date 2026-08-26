"""Run R1 on holdout: extract from source only, then score against gold.

Pred cards live under eval/preds/ (gitignored). The mean JSON is the before/after artifact.
"""
from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

from scribe3.eval import verify_holdout_hash
from scribe3.eval.card_schema import R1_HARD_FIELDS
from scribe3.eval.extract_card import extract_card
from scribe3.eval.pool import run_jobs
from scribe3.eval.score_r1 import load_label_card, score_pair, scored_seqs

EVAL = Path(__file__).resolve().parent


def unwrap_md(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3].rstrip()
    return t.strip()


def live_complete(prompt: str) -> str:
    import time

    from scribe3.deepseek_client import DeepSeekError, DeepSeekHTTPError
    from scribe3.llm import hermes_complete

    last: Exception | None = None
    for attempt in range(8):
        try:
            return unwrap_md(
                hermes_complete(prompt, max_tokens=12288, temperature=0.2, timeout=600)
            )
        except DeepSeekError as e:
            last = e
            wait = 2.0
            if isinstance(e, DeepSeekHTTPError) and e.status_code == 429:
                wait = min(180.0, 15.0 * (2 ** attempt))
            print(
                f"R1_LLM_RETRY attempt={attempt + 1} {type(e).__name__}: {e} sleep={wait}",
                flush=True,
            )
            time.sleep(wait)
    raise last if last else RuntimeError("live_complete failed")


def _summarize(rows: list[dict]) -> dict:
    n = len(rows)
    mean = sum(r["score"] for r in rows) / n if n else 0.0
    fields = {}
    for name in R1_HARD_FIELDS:
        fields[name] = (
            round(sum(1 for r in rows if r["fields"][name]["ok"]) / n, 4) if n else 0.0
        )
    return {"n": n, "mean": round(mean, 4), "fields": fields, "rows": rows}


def run_holdout(
    *,
    complete_fn,
    out_dir: Path | None = None,
    pred_dir: Path | None = None,
    label: str = "before",
    resume: bool = True,
    seqs: list[int] | None = None,
    jobs: int = 1,
) -> dict:
    holdout_hash = verify_holdout_hash()
    dest = Path(out_dir) if out_dir is not None else EVAL
    cards = Path(pred_dir) if pred_dir is not None else dest / "preds" / f"r1_{label}"
    cards.mkdir(parents=True, exist_ok=True)
    todo = list(seqs) if seqs is not None else scored_seqs()
    summary_path = dest / f"r1_{label}.json"
    lock = threading.Lock()
    collected: list[dict | None] = [None] * len(todo)

    def work(i: int, seq: int) -> dict:
        path = cards / f"{seq}.md"
        if resume and path.exists() and path.stat().st_size > 0:
            print(f"R1_SEQ {seq} resume {i + 1}/{len(todo)}", flush=True)
            pred = path.read_text(encoding="utf-8")
        else:
            print(f"R1_SEQ {seq} start {i + 1}/{len(todo)}", flush=True)
            pred = unwrap_md(extract_card(seq, complete_fn=complete_fn))
            path.write_text(pred, encoding="utf-8")
        scored = score_pair(pred, load_label_card(seq))
        scored["seq"] = seq
        return scored

    def done(i: int, seq: int, scored: dict | None, err: BaseException | None) -> None:
        with lock:
            if err is not None:
                print(f"R1_SEQ {seq} FAIL {type(err).__name__}: {err}", flush=True)
                return
            collected[i] = scored
            sofar = [r for r in collected if r is not None]
            print(f"R1_SEQ {seq} score={scored['score']} mean={_summarize(sofar)['mean']}", flush=True)
            summary_path.write_text(
                json.dumps(
                    {"label": label, "holdout_sha256": holdout_hash, **_summarize(sofar)},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    run_jobs(todo, work, jobs=jobs, on_done=done)
    rows = [r for r in collected if r is not None]
    doc = {"label": label, "holdout_sha256": holdout_hash, **_summarize(rows)}
    summary_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing = [s for s in todo if not (cards / f"{s}.md").exists()]
    if missing:
        print(f"R1_MISSING {missing}", flush=True)
    return doc


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser()
    p.add_argument("--label", default="before")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--jobs", type=int, default=1)
    args = p.parse_args(argv)
    seqs = scored_seqs()
    if args.limit:
        seqs = seqs[: args.limit]
    out = run_holdout(
        complete_fn=live_complete,
        label=args.label,
        resume=not args.no_resume,
        seqs=seqs,
        jobs=args.jobs,
    )
    pred_dir = EVAL / "preds" / f"r1_{args.label}"
    missing = [s for s in seqs if not (pred_dir / f"{s}.md").exists()]
    if missing:
        raise SystemExit(1)
    return out


if __name__ == "__main__":
    out = main()
    print(json.dumps({"n": out["n"], "mean": out["mean"], "fields": out["fields"]}, ensure_ascii=False))
