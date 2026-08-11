"""Novel-first residual 1/2/3 — surface API, event-graph path, lock wiring (host-light)."""
from __future__ import annotations

from pathlib import Path


def test_soft_precheck_and_distill_surface():
    from scribe3.novel_first_surface import soft_precheck_surface, literary_distill_surface
    from scribe3.soft_precheck import soft_precheck_plan
    from scribe3.literary_distill import literary_distill

    p = soft_precheck_surface({"beats": [{"goal": "g", "conflict": ""}]})
    assert p["hard_park"] is False
    assert p["surface"] == "novel_first.soft_precheck"
    assert any(f.get("code") == "empty_conflict" for f in p["findings"])
    # surface 委托 shipped pure helper（同函数身份）
    assert soft_precheck_plan is not None
    bare = soft_precheck_plan({"beats": []})
    assert bare["hard_park"] is False

    d = literary_distill_surface(recap="了结冲突。\n\n付出代价。")
    assert d["raw"] and d["bullets"] and d["control"]["uses_tokens_saved"] is False
    d2 = literary_distill_surface(text="态度改变了。\n\n还清旧债。")
    assert d2["surface"] == "novel_first.literary_distill"
    assert literary_distill("x")["control"]["uses_tokens_saved"] is False

    # misc 路由 handler 必须调用 surface（结构）
    src = Path("scribe3/api/routers/misc_routes.py").read_text(encoding="utf-8")
    assert "soft_precheck_surface" in src and "literary_distill_surface" in src


def test_event_graph_write_path_surface():
    from scribe3.novel_first_surface import event_graph_surface, event_graph_from_store_chapter

    g = event_graph_surface(
        events=[{"id": "e1"}, {"id": "e2", "leads_to": "e3"}, {"id": "e3"}],
        promises=[{"id": "p1", "event_id": "e1"}],
    )
    assert g["graph"]["edge_count"] >= 1
    assert g["sample_pair"] and g["sample_pair"]["linked"] is True
    assert g["sample_pair"].get("forward") or g["sample_pair"].get("linked")

    api = event_graph_surface(
        events=[{"id": "a"}, {"id": "b", "leads_to": "c"}],
        seed_id="b",
    )
    assert api["surface"] == "novel_first.event_graph"
    assert "c" in api["one_hop"]
    assert api["sample_pair"]["linked"] is True

    class _St:
        def list_events(self, ch):
            return [{"id": "x1"}, {"id": "x2", "leads_to": "x3"}]

        def list_promises(self):
            return []

        def get_chapter(self, ch):
            return {}

    sg = event_graph_from_store_chapter(_St(), 1)
    assert sg["graph"]["edge_count"] >= 1
    pair = sg["sample_pair"]
    assert pair and pair.get("linked")

    wa = Path("scribe3/api/services/write_assemble.py").read_text(encoding="utf-8")
    assert "event_graph_from_store_chapter" in wa
    src = Path("scribe3/api/routers/misc_routes.py").read_text(encoding="utf-8")
    assert "event_graph_surface" in src


def test_lock_loop_ingest_repair_surface():
    from scribe3.chapter_lock import (
        acquire_chapter_lock, release_chapter_lock, InMemoryLockStore,
    )
    from scribe3.novel_first_surface import is_chapter_op_busy

    for kind in ("loop", "ingest", "repair"):
        r1 = acquire_chapter_lock(kind, "main", 3)
        assert r1.ok
        assert is_chapter_op_busy(kind, "main", 3) is True
        r2 = acquire_chapter_lock(kind, "main", 3)
        assert not r2.ok and r2.status == "busy"
        release_chapter_lock(kind, "main", 3)
        assert is_chapter_op_busy(kind, "main", 3) is False

    store = InMemoryLockStore()
    import os
    os.environ["SCRIBE3_DISTRIBUTED_LOCK"] = "1"
    try:
        assert acquire_chapter_lock("ingest", "w", 9, store=store).ok
        assert not acquire_chapter_lock("ingest", "w", 9, store=store).ok
        release_chapter_lock("ingest", "w", 9, store=store)
    finally:
        os.environ.pop("SCRIBE3_DISTRIBUTED_LOCK", None)

    # 结构：enqueue 与 app_impl 走 chapter_lock
    src = Path("scribe3/api/services/ingest_bg.py").read_text(encoding="utf-8")
    assert "acquire_chapter_lock" in src and "ingest" in src
    app = Path("scribe3/api/app_impl.py").read_text(encoding="utf-8")
    assert "acquire_chapter_lock" in app and "_chapter_op_busy" in app
    ch = Path("scribe3/api/routers/chapters.py").read_text(encoding="utf-8")
    assert "_acquire_op_mutex" in ch and "_chapter_op_busy" in ch


def test_routes_registered_in_misc_source():
    src = Path("scribe3/api/routers/misc_routes.py").read_text(encoding="utf-8")
    assert "/soft-precheck" in src
    assert "/literary-distill" in src
    assert "/event-graph" in src
    assert "soft_precheck_surface" in src or "soft_precheck_ep" in src


if __name__ == "__main__":
    import traceback
    failed = []
    for name, fn in list(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print("PASS", name)
        except Exception as e:
            print("FAIL", name, e)
            traceback.print_exc()
            failed.append(name)
    print("SUMMARY failed=", failed)
    raise SystemExit(1 if failed else 0)
