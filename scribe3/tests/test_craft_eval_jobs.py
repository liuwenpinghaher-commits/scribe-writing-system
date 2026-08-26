"""--jobs must not change eval results: parallel == serial, resume still skips."""
from __future__ import annotations

import threading

from scribe3.eval.extract_card import empty_shell_card
from scribe3.eval.pool import run_jobs
from scribe3.eval.run_r2 import run_r2


def _turned_card() -> str:
    return empty_shell_card(1, "x").replace("没翻。正文几乎没有。", "翻了。")


def test_run_jobs_keeps_input_order_and_isolates_failures():
    def worker(i: int, item: int) -> int:
        if item == 3:
            raise ValueError("boom")
        return item * 10

    results, errors = run_jobs([1, 2, 3, 4], worker, jobs=4)
    assert results == [10, 20, None, 40]
    assert errors[2] is not None and errors[0] is None


def _run(tmp_path, name: str, jobs: int, calls: dict) -> dict:
    clean = tmp_path / f"{name}-r1"
    clean.mkdir()
    (clean / "1.md").write_text(_turned_card(), encoding="utf-8")
    lock = threading.Lock()

    def fn(prompt: str) -> str:
        with lock:
            calls["n"] += 1
        return empty_shell_card(1, "x")

    return run_r2(
        complete_fn=fn,
        out_dir=tmp_path / name,
        pred_dir=tmp_path / name / "r2",
        clean_dir=clean,
        label="before",
        resume=False,
        seqs=[1],
        jobs=jobs,
    )


def test_parallel_matches_serial(tmp_path):
    (tmp_path / "serial").mkdir()
    (tmp_path / "par").mkdir()
    serial_calls = {"n": 0}
    par_calls = {"n": 0}
    serial = _run(tmp_path, "serial", 1, serial_calls)
    par = _run(tmp_path, "par", 4, par_calls)
    assert serial_calls["n"] == par_calls["n"] == 3
    assert serial["rows"] == par["rows"]
    assert serial["score"] == par["score"]
    assert serial["by_kind"] == par["by_kind"]


def test_parallel_resume_does_not_recall_llm(tmp_path):
    (tmp_path / "one").mkdir()
    calls = {"n": 0}
    first = _run(tmp_path, "one", 4, calls)
    assert calls["n"] == 3

    clean = tmp_path / "one-r1"
    again_calls = {"n": 0}

    def fn(prompt: str) -> str:
        again_calls["n"] += 1
        return empty_shell_card(1, "x")

    again = run_r2(
        complete_fn=fn,
        out_dir=tmp_path / "one",
        pred_dir=tmp_path / "one" / "r2",
        clean_dir=clean,
        label="before",
        resume=True,
        seqs=[1],
        jobs=4,
    )
    assert again_calls["n"] == 0
    assert again["rows"] == first["rows"]
