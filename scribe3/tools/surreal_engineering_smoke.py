"""Surreal 工程加强冒烟（demo 已部署栈；可写探针数据到 --db）。

覆盖：
  S-rrf   search::rrf 对象列表 + hybrid flag
  S-cdc   真表 proposition SHOW CHANGES 前进 + cache_watch
  S-lock  DISTRIBUTED chapter_lock 二次 busy + ingest kind
  S-feed  health-shaped status dict

用法::

  python -m scribe3.tools.surreal_engineering_smoke --db main
  python -m scribe3.tools.surreal_engineering_smoke --db main --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid


def _ok(name: str, passed: bool, detail: dict | None = None) -> dict:
    return {"name": name, "ok": bool(passed), "detail": detail or {}}


def run_smoke(db: str, *, ns: str = "scribe3") -> dict:
    from scribe3.store import SurrealStore
    from scribe3.chapter_lock import acquire_chapter_lock, release_chapter_lock
    from scribe3.concurrency_lock import distributed_lock_enabled
    from scribe3.surreal_flags import hybrid_search_native, changefeed_cache
    from scribe3.changefeed_consumer import poll_table_changes, apply_changes_to_cache
    from scribe3.context_cache import TTLCache, emit_invalidation

    checks: list[dict] = []
    st = SurrealStore(ns=ns, db=db)
    try:
        # ── flags ──
        checks.append(_ok("flags.hybrid", hybrid_search_native(), {
            "hybrid_search_native": hybrid_search_native(),
            "changefeed_cache": changefeed_cache(),
            "distributed_lock": distributed_lock_enabled(),
        }))

        # ── A2 search::rrf ──
        rrf_ok = False
        rrf_detail: dict = {}
        try:
            rrf = st._query(
                "RETURN search::rrf([$a, $b], $lim, 60);",
                {
                    "a": [{"id": "fact:1"}, {"id": "fact:2"}],
                    "b": [{"id": "fact:2"}, {"id": "fact:3"}],
                    "lim": 5,
                },
            )
            raw = rrf[0] if isinstance(rrf, list) and rrf else rrf
            ids = []
            if isinstance(raw, list):
                for x in raw:
                    if isinstance(x, dict) and x.get("id") is not None:
                        ids.append(str(x["id"]))
            rrf_ok = bool(ids) and ids[0] == "fact:2"
            rrf_detail = {"ids": ids, "raw_type": type(raw).__name__}
        except Exception as e:
            rrf_detail = {"error": str(e)[:200]}
        checks.append(_ok("rrf.object_lists", rrf_ok, rrf_detail))

        # ── seed props for hybrid (minimal, no embed required for rrf path) ──
        tag = uuid.uuid4().hex[:8]
        try:
            st._execute_write(
                "CREATE proposition SET entity_id=$e, attribute=$a, value=$v, "
                "valid_from=1, tokens=$tok;",
                {
                    "e": f"role:smoke_{tag}",
                    "a": "name",
                    "v": f"铜炉探针{tag}",
                    "tok": f"铜炉 探针 {tag}",
                },
            )
            checks.append(_ok("seed.proposition", True, {"tag": tag}))
        except Exception as e:
            checks.append(_ok("seed.proposition", False, {"error": str(e)[:200]}))

        # ── CDC: SHOW CHANGES on proposition after write ──
        cdc_ok = False
        cdc_detail: dict = {}
        try:
            before = poll_table_changes(st, "proposition", 0)
            last_vs = 0
            if before:
                last = before[-1]
                if isinstance(last, dict) and "versionstamp" in last:
                    last_vs = last["versionstamp"]
            st._execute_write(
                "CREATE proposition SET entity_id=$e, attribute=$a, value=$v, valid_from=1;",
                {"e": f"role:cdc_{tag}", "a": "k", "v": f"cdc-{tag}"},
            )
            time.sleep(0.05)
            after = poll_table_changes(st, "proposition", last_vs)
            s = json.dumps(after, default=str)
            cdc_ok = bool(after) and (f"cdc-{tag}" in s or "proposition:" in s or len(after) > 0)
            cdc_detail = {
                "since": last_vs,
                "n_after": len(after) if isinstance(after, list) else 0,
                "sample": s[:280],
            }
        except Exception as e:
            cdc_detail = {"error": str(e)[:200]}
        checks.append(_ok("cdc.proposition_show_changes", cdc_ok, cdc_detail))

        # ── dual-write cache_watch + apply ──
        dual_ok = False
        dual_detail: dict = {}
        try:
            c = TTLCache(60, maxsize=4, name="eng_smoke", tables={"proposition"})
            c.set("k", 1, work=db)
            emit_invalidation("proposition", work=db, store=st)
            rows = poll_table_changes(st, "cache_watch", 0)
            c.set("k", 1, work=db)
            touched = apply_changes_to_cache(rows or [], db)
            dual_ok = "proposition" in touched or c.get("k") is None
            dual_detail = {
                "show_n": len(rows) if isinstance(rows, list) else 0,
                "touched": sorted(touched)[:8],
                "cache_cleared": c.get("k") is None,
            }
        except Exception as e:
            dual_detail = {"error": str(e)[:200]}
        checks.append(_ok("cdc.cache_watch_dual_apply", dual_ok, dual_detail))

        # ── locks ──
        lock_ok = False
        lock_detail: dict = {}
        try:
            r1 = acquire_chapter_lock("loop", db, 999001, store=st, ttl_seconds=30)
            r2 = acquire_chapter_lock("loop", db, 999001, store=st, ttl_seconds=30)
            r3 = acquire_chapter_lock("ingest", db, 999002, store=st, ttl_seconds=30)
            r4 = acquire_chapter_lock("ingest", db, 999002, store=st, ttl_seconds=30)
            lock_ok = r1.ok and (not r2.ok) and r3.ok and (not r4.ok)
            lock_detail = {
                "loop": [r1.status, r2.status],
                "ingest": [r3.status, r4.status],
                "distributed": distributed_lock_enabled(),
            }
            release_chapter_lock("loop", db, 999001, store=st)
            release_chapter_lock("ingest", db, 999002, store=st)
        except Exception as e:
            lock_detail = {"error": str(e)[:200]}
        checks.append(_ok("locks.chapter_double_busy", lock_ok, lock_detail))

        # ── emit coverage contract (source) ──
        try:
            from pathlib import Path
            root = Path(__file__).resolve().parents[1]
            cov = {
                "add_fact": "_emit_cache_invalidation(\"proposition\"" in
                (root / "store" / "facts_knowledge.py").read_text(encoding="utf-8"),
                "save_chapter": "_emit_cache_invalidation(\"chapter\"" in
                (root / "store" / "chapters.py").read_text(encoding="utf-8"),
                "add_event": "_emit_cache_invalidation(\"event\"" in
                (root / "store" / "events.py").read_text(encoding="utf-8"),
                "add_entity_character": "_emit_cache_invalidation(\"character\"" in
                (root / "store" / "characters.py").read_text(encoding="utf-8"),
                "material": "_emit_cache_invalidation(\"material\"" in
                (root / "store" / "materials.py").read_text(encoding="utf-8"),
            }
            checks.append(_ok("coverage.emit_call_sites", all(cov.values()), cov))
        except Exception as e:
            checks.append(_ok("coverage.emit_call_sites", False, {"error": str(e)[:120]}))

    finally:
        try:
            st.close()
        except Exception:
            pass

    passed = sum(1 for c in checks if c["ok"])
    return {
        "db": db,
        "ns": ns,
        "passed": passed,
        "total": len(checks),
        "ok": passed == len(checks),
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Surreal engineering smoke")
    p.add_argument("--db", default=os.environ.get("SCRIBE3_DEFAULT_WORK") or "main")
    p.add_argument("--ns", default="scribe3")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    report = run_smoke(args.db, ns=args.ns)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"surreal_engineering_smoke db={report['db']} "
              f"{report['passed']}/{report['total']} ok={report['ok']}")
        for c in report["checks"]:
            mark = "PASS" if c["ok"] else "FAIL"
            print(f"  [{mark}] {c['name']} {json.dumps(c.get('detail') or {}, ensure_ascii=False)[:160]}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
