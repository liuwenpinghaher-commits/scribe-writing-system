#!/usr/bin/env python3
"""过程记忆闭环：capture → memory_item → prefetch/vector/bm25。

  python -m scribe3.tools.memory_e2e_s32 --work main
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid


def run(work: str) -> dict:
    from scribe3.memory_capture import MemoryCapture, turn_event
    from scribe3.memory_retrieval import MemoryRetriever
    from scribe3.store import SurrealStore

    st = SurrealStore(db=work)
    st.apply_schema()
    before = st._query("SELECT count() AS c FROM memory_item GROUP ALL")
    c0 = int((before or [{}])[0].get("c") or 0)

    cap = MemoryCapture(st)
    tid = f"e2e-{uuid.uuid4().hex[:8]}"
    texts = [
        "备忘：下一场戏测角在乱岗密室里不敢碰铜炉，先写犹豫与环境寒意。",
        "备忘：伏笔线——玉佩纹路与铜炉底部暗纹同源，本章只露一角。",
        "备忘：对话节奏放慢，避免解释腔，用动作顶替心理标签。",
    ]
    results = []
    t0 = time.perf_counter()
    for i, text in enumerate(texts):
        ev = turn_event(
            text,
            event_id=f"{tid}-{i}",
            work=work,
            thread_id=tid,
            classification="episodic",
            known_from=1,
        )
        results.append(cap.capture_event(ev))
    capture_ms = round((time.perf_counter() - t0) * 1000, 2)

    after = st._query("SELECT count() AS c FROM memory_item GROUP ALL")
    c1 = int((after or [{}])[0].get("c") or 0)

    # channel probes
    bm25_ids = st.memory_bm25(work, "铜炉 密室", k=5, chapter=3)
    vec_ids = st.memory_vector(work, "铜炉 密室 玉佩", k=5, chapter=3)

    prefetch_n = None
    prefetch_err = None
    prefetch_ms = None
    try:
        from scribe3.memory_models import RetrievalQuery
        retr = MemoryRetriever(st)
        rq = RetrievalQuery(
            work=work,
            snapshot={"chapter": 3, "focalizer": None},
            query="铜炉 密室 玉佩",
            k=8,
        )
        t1 = time.perf_counter()
        res = retr.retrieve_full(rq)
        prefetch_ms = round((time.perf_counter() - t1) * 1000, 2)
        prefetch_n = len(getattr(res, "selected", None) or getattr(res, "candidates", None) or [])
    except Exception as e:
        prefetch_err = f"{type(e).__name__}: {e}"

    ok = (
        c1 > c0
        and any(r.get("status") == "complete" for r in results)
        and (bool(bm25_ids) or bool(vec_ids) or (prefetch_n or 0) > 0)
    )
    return {
        "ok": ok,
        "work": work,
        "thread_id": tid,
        "memory_item_before": c0,
        "memory_item_after": c1,
        "capture_results": results,
        "capture_ms": capture_ms,
        "bm25_ids": bm25_ids,
        "vector_ids": vec_ids,
        "prefetch_n": prefetch_n,
        "prefetch_ms": prefetch_ms,
        "prefetch_err": prefetch_err,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--work", default="main")
    args = p.parse_args(argv)
    out = run(args.work)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
