"""Ordered worker pool for eval runs.

`jobs=1` runs strictly serially so results match the pre-parallel runners.
A failing item never aborts the batch: its exception is returned in place.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any


def run_jobs(
    items: Sequence[Any],
    worker: Callable[[int, Any], Any],
    *,
    jobs: int = 1,
    on_done: Callable[[int, Any, Any, BaseException | None], None] | None = None,
) -> tuple[list[Any], list[BaseException | None]]:
    """Run ``worker(index, item)`` over items; results keep the input order.

    ``on_done`` fires as each item finishes and may run on a worker thread,
    so the caller is responsible for locking any shared output.
    """
    n = len(items)
    results: list[Any] = [None] * n
    errors: list[BaseException | None] = [None] * n

    def one(i: int) -> None:
        item = items[i]
        try:
            results[i] = worker(i, item)
        except Exception as exc:  # a bad chapter must not kill the batch
            errors[i] = exc
        if on_done is not None:
            on_done(i, item, results[i], errors[i])

    if jobs <= 1:
        for i in range(n):
            one(i)
    else:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            list(pool.map(one, range(n)))
    return results, errors
