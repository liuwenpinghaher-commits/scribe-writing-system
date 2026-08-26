"""Run R2 on holdout. Clean reuses R1 cards; negatives are extracted from mutated source."""
from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

from scribe3.eval import verify_holdout_hash
from scribe3.eval.extract_card import extract_card
from scribe3.eval.pool import run_jobs
from scribe3.eval.run_r1 import live_complete, unwrap_md
from scribe3.eval.score_r1 import scored_seqs
from scribe3.eval.score_r2 import KINDS, gold_turned, score_item, source_for

EVAL = Path(__file__).resolve().parent


def _summarize(rows: list[dict]) -> dict:
    n = len(rows)
    hits = sum(1 for r in rows if r["ok"])
    by_kind = {}
    for kind in KINDS:
        sub = [r for r in rows if r["kind"] == kind]
        by_kind[kind] = round(sum(1 for r in sub if r["ok"]) / len(sub), 4) if sub else 0.0
    return {
        "n": n,
        "hits": hits,
        "score": round(hits / n, 4) if n else 0.0,
        "by_kind": by_kind,
        "rows": rows,
    }


def run_r2(
    *,
    complete_fn,
    out_dir: Path | None = None,
    pred_dir: Path | None = None,
    clean_dir: Path | None = None,
    label: str = "before",
    resume: bool = True,
    seqs: list[int] | None = None,
    jobs: int = 1,
) -> dict:
    holdout_hash = verify_holdout_hash()
    dest = Path(out_dir) if out_dir is not None else EVAL
    cards = Path(pred_dir) if pred_dir is not None else dest / "preds" / f"r2_{label}"
    clean = Path(clean_dir) if clean_dir is not None else dest / "preds" / "r1_before"
    cards.mkdir(parents=True, exist_ok=True)
    todo = [s for s in (seqs if seqs is not None else scored_seqs()) if gold_turned(s) is True]
    items = [(seq, kind) for seq in todo for kind in KINDS]
    summary_path = dest / f"r2_{label}.json"
    total = len(items)
    lock = threading.Lock()
    collected: list[dict | None] = [None] * total

    def work(i: int, item: tuple[int, str]) -> dict:
        seq, kind = item
        r1_clean = clean / f"{seq}.md"
        reused_clean = kind == "clean" and r1_clean.exists() and r1_clean.stat().st_size > 0
        path = r1_clean if reused_clean else cards / f"{seq}_{kind}.md"
        if reused_clean or (resume and path.exists() and path.stat().st_size > 0):
            print(f"R2 {seq}/{kind} resume {i + 1}/{total}", flush=True)
            md = path.read_text(encoding="utf-8")
        else:
            print(f"R2 {seq}/{kind} start {i + 1}/{total}", flush=True)
            md = unwrap_md(
                extract_card(
                    seq,
                    complete_fn=complete_fn,
                    source=source_for(kind, seq),
                    use_fewshot=False,
                )
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(md, encoding="utf-8")
        return score_item(seq, kind, complete_fn, card_md=md)

    def done(i: int, item: tuple[int, str], row: dict | None, err: BaseException | None) -> None:
        seq, kind = item
        with lock:
            if err is not None:
                print(f"R2 {seq}/{kind} FAIL {type(err).__name__}: {err}", flush=True)
                return
            collected[i] = row
            sofar = [r for r in collected if r is not None]
            print(f"R2 {seq}/{kind} ok={row['ok']} score={_summarize(sofar)['score']}", flush=True)
            summary_path.write_text(
                json.dumps(
                    {"label": label, "holdout_sha256": holdout_hash, **_summarize(sofar)},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    _, errors = run_jobs(items, work, jobs=jobs, on_done=done)
    rows = [r for r in collected if r is not None]
    missing = [f"{items[i][0]}/{items[i][1]}" for i, e in enumerate(errors) if e is not None]
    doc = {"label": label, "holdout_sha256": holdout_hash, **_summarize(rows)}
    summary_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if missing:
        print(f"R2_MISSING {missing}", flush=True)
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
    out = run_r2(
        complete_fn=live_complete,
        label=args.label,
        resume=not args.no_resume,
        seqs=seqs,
        jobs=args.jobs,
    )
    need = 4 * len([s for s in seqs if gold_turned(s) is True])
    if out["n"] < need:
        raise SystemExit(1)
    return out


if __name__ == "__main__":
    out = main()
    print(json.dumps({"n": out["n"], "score": out["score"], "by_kind": out["by_kind"]}, ensure_ascii=False))
