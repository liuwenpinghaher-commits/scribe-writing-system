"""R2：系统能不能判出削/灌/说明书不是处境翻。"""
from __future__ import annotations

from scribe3.eval.extract_card import extract_card, parse_card
from scribe3.eval.negatives import make_cut, make_lecture, make_pump
from scribe3.eval.score_r1 import load_label_card, turned

KINDS = ("clean", "cut", "pump", "lecture")


def gold_turned(seq: int) -> bool | None:
    gold = parse_card(load_label_card(seq))
    return turned(gold.get("这场戏有没有翻", ""))


def expected_turn(kind: str, seq: int) -> bool | None:
    g = gold_turned(seq)
    if kind == "clean":
        return g
    return False


def source_for(kind: str, seq: int) -> str:
    if kind == "cut":
        return make_cut(seq)
    if kind == "pump":
        return make_pump(seq)
    if kind == "lecture":
        return make_lecture(seq)
    from scribe3.eval.extract_card import load_source_slice

    return load_source_slice(seq)


def judge_turn(card_md: str) -> bool | None:
    return turned(parse_card(card_md).get("这场戏有没有翻", ""))


def score_item(seq: int, kind: str, complete_fn, card_md: str | None = None) -> dict:
    if card_md is None:
        card_md = extract_card(
            seq, complete_fn=complete_fn, source=source_for(kind, seq), use_fewshot=False
        )
    pred = judge_turn(card_md)
    exp = expected_turn(kind, seq)
    ok = pred is not None and pred == exp
    return {"seq": seq, "kind": kind, "pred": pred, "expected": exp, "ok": ok}


def score_r2(seqs: list[int], complete_fn) -> dict:
    """Only chapters whose gold is 翻了：clean 应判翻，三类负样本应判没翻。"""
    rows = []
    for seq in seqs:
        if gold_turned(seq) is not True:
            continue
        for kind in KINDS:
            rows.append(score_item(seq, kind, complete_fn))
    n = len(rows)
    hits = sum(1 for r in rows if r["ok"])
    return {"n": n, "hits": hits, "score": hits / n if n else 0.0, "rows": rows}
