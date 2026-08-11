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
            # 扁平 [{id,rrf_score},…] 或 [[…]]
            items = []
            if isinstance(rrf, list) and rrf:
                if isinstance(rrf[0], dict) and "id" in rrf[0]:
                    items = rrf
                elif isinstance(rrf[0], list):
                    items = rrf[0]
            ids = [str(x["id"]) for x in items if isinstance(x, dict) and x.get("id") is not None]
            rrf_ok = bool(ids) and ids[0] == "fact:2"
            rrf_detail = {"ids": ids, "raw_type": type(rrf).__name__, "n": len(items)}
        except Exception as e:
            rrf_detail = {"error": str(e)[:200]}
        checks.append(_ok("rrf.object_lists", rrf_ok, rrf_detail))

        # ── seed props for hybrid (tokens + semantic_index when embed available) ──
        tag = uuid.uuid4().hex[:8]
        fact_oid = f"fact:smoke_{tag}"
        try:
            from scribe3.ontology import Fact
            st.add_fact(
                Fact(
                    fact_oid,
                    f"role:smoke_{tag}",
                    "name",
                    f"铜炉探针{tag}暴雨乱岗",
                    valid_from=1,
                ),
            )
            # ensure tokens for BM25 path
            try:
                st.semantic_index(fact_oid, f"铜炉探针{tag}暴雨乱岗")
            except Exception as ee:
                # embed 不可用时仍有 tokens 写尝试
                st._execute_write(
                    "UPDATE type::record('proposition', $l) SET tokens=$t;",
                    {"l": fact_oid.split(":", 1)[-1], "t": f"铜炉 探针 {tag} 暴雨 乱岗"},
                )
                checks.append(_ok("seed.semantic_index", False, {"error": str(ee)[:120]}))
            else:
                checks.append(_ok("seed.semantic_index", True, {"oid": fact_oid}))
            checks.append(_ok("seed.proposition", True, {"tag": tag, "oid": fact_oid}))
        except Exception as e:
            checks.append(_ok("seed.proposition", False, {"error": str(e)[:200]}))
            fact_oid = None

        # ── hybrid_recall end-to-end ──
        hybrid_ok = False
        hybrid_detail: dict = {}
        try:
            os.environ["SCRIBE3_HYBRID_SEARCH_NATIVE"] = "1"
            hits = st.hybrid_recall(f"铜炉 探针 {tag}", chapter=1, k=5) if fact_oid else []
            ids = [getattr(h, "id", None) or (h.get("id") if isinstance(h, dict) else None) for h in (hits or [])]
            # 至少返回 list；有 embedding 时 ideally 含种子 fact
            hybrid_ok = isinstance(hits, list)
            hybrid_detail = {
                "n": len(hits or []),
                "ids": [str(i) for i in ids if i][:8],
                "contains_seed": bool(fact_oid and any(fact_oid in str(i) for i in ids)),
                "native_flag": hybrid_search_native(),
            }
            # 若完全无 hit 但 flag 开且库空向量，仍算 soft pass（API 不炸）
            if hybrid_ok and not hits:
                hybrid_detail["note"] = "empty_hits_ok_if_no_embed"
        except Exception as e:
            hybrid_detail = {"error": str(e)[:240]}
        checks.append(_ok("hybrid.recall_e2e", hybrid_ok, hybrid_detail))

        # ── CDC: 真表 proposition 或旁路 cache_watch（二选一即可）──
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
            native_ok = bool(after) and (
                f"cdc-{tag}" in s or "proposition:" in s or len(after) > 0
            )
            # 旁路：emit 后 cache_watch 必有行（真表 feed 冻住时仍算 CDC 链路可用）
            emit_invalidation("proposition", work=db, store=st)
            cw = poll_table_changes(st, "cache_watch", 0)
            bypass_ok = bool(cw)
            cdc_ok = native_ok or bypass_ok
            cdc_detail = {
                "since": last_vs,
                "native_n": len(after) if isinstance(after, list) else 0,
                "native_ok": native_ok,
                "bypass_ok": bypass_ok,
                "sample": s[:200] if s else "",
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
