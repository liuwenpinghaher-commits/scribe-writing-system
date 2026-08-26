"""R1 holdout runner: resume, no gold leak into extract prompt."""
from __future__ import annotations

from scribe3.eval.extract_card import empty_shell_card, extract_card, load_source_slice
from scribe3.eval.run_r1 import run_holdout
from scribe3.eval.score_r1 import load_label_card, scored_seqs


def test_extract_prompt_omits_holdout_gold_voice():
    seq = 8
    gold = load_label_card(seq)
    source = load_source_slice(seq)
    marker = "必须拿回去堵缺口的东西"
    assert marker in gold
    assert marker not in source
    seen = []

    def fn(prompt: str) -> str:
        seen.append(prompt)
        return empty_shell_card(seq, "x")

    extract_card(seq, complete_fn=fn)
    assert seen
    assert marker not in seen[0]


def test_run_holdout_fake_is_floor(tmp_path):
    seqs = scored_seqs()[:2]
    calls = {"n": 0}

    def fn(prompt: str) -> str:
        calls["n"] += 1
        return empty_shell_card(8, "x")

    doc = run_holdout(
        complete_fn=fn,
        out_dir=tmp_path,
        pred_dir=tmp_path / "preds",
        label="before",
        resume=False,
        seqs=seqs,
    )
    assert doc["n"] == 2
    assert doc["mean"] < 0.3
    assert calls["n"] == 2
    assert (tmp_path / "r1_before.json").exists()

    calls["n"] = 0
    again = run_holdout(
        complete_fn=fn,
        out_dir=tmp_path,
        pred_dir=tmp_path / "preds",
        label="before",
        resume=True,
        seqs=seqs,
    )
    assert again["n"] == 2
    assert calls["n"] == 0


def test_run_holdout_skips_failed_seq(tmp_path):
    seqs = scored_seqs()[:2]
    calls = {"n": 0}

    def fn(prompt: str) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return empty_shell_card(seqs[1], "x")

    doc = run_holdout(
        complete_fn=fn,
        out_dir=tmp_path,
        pred_dir=tmp_path / "preds",
        label="before",
        resume=False,
        seqs=seqs,
    )
    assert doc["n"] == 1
    assert (tmp_path / "preds" / f"{seqs[1]}.md").exists()
    assert not (tmp_path / "preds" / f"{seqs[0]}.md").exists()
