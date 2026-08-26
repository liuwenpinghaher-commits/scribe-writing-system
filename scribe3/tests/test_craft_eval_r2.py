"""R2 scorer: clean stays turned; cut/pump/lecture are not."""
from __future__ import annotations

from scribe3.eval.extract_card import empty_shell_card
from scribe3.eval.score_r2 import score_r2


def _fn_from_prompt(prompt: str) -> str:
    turned = "收入怀中" in prompt
    body = empty_shell_card(1, "x")
    return body.replace("没翻。正文几乎没有。", "翻了。" if turned else "没翻。")


def test_r2_oracle_on_seq1_is_ceiling():
    doc = score_r2([1], _fn_from_prompt)
    assert doc["n"] == 4
    assert doc["score"] == 1.0


def test_r2_always_turned_is_floor():
    def always_yes(prompt: str) -> str:
        return empty_shell_card(1, "x").replace("没翻。正文几乎没有。", "翻了。")

    doc = score_r2([1], always_yes)
    assert doc["score"] == 0.25


def test_run_r2_reuses_r1_clean(tmp_path):
    from scribe3.eval.extract_card import empty_shell_card
    from scribe3.eval.run_r2 import run_r2

    clean = tmp_path / "r1"
    clean.mkdir()
    (clean / "1.md").write_text(
        empty_shell_card(1, "x").replace("没翻。正文几乎没有。", "翻了。"),
        encoding="utf-8",
    )
    calls = {"n": 0}

    def fn(prompt: str) -> str:
        calls["n"] += 1
        return empty_shell_card(1, "x")

    doc = run_r2(
        complete_fn=fn,
        out_dir=tmp_path,
        pred_dir=tmp_path / "r2",
        clean_dir=clean,
        label="before",
        resume=False,
        seqs=[1],
    )
    assert calls["n"] == 3
    assert doc["n"] == 4
    assert doc["by_kind"]["clean"] == 1.0

    calls["n"] = 0
    again = run_r2(
        complete_fn=fn,
        out_dir=tmp_path,
        pred_dir=tmp_path / "r2",
        clean_dir=clean,
        label="before",
        resume=True,
        seqs=[1],
    )
    assert calls["n"] == 0
    assert again["n"] == 4
