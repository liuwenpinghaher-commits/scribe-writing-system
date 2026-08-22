"""2026-08-23 铜炉最优化 Stage 1：SSE / 正典同步 / 级联清理 / leak_markers。"""
from __future__ import annotations

import inspect
from pathlib import Path

from scribe3.canon_apply_store import apply_item_to_store
from scribe3.canon_apply_sync import after_canon_apply
from scribe3.codex_secret_bridge import sync_faction_secrets
from scribe3.leak_markers import auto_generate_leak_markers
from scribe3.store.connection import ConnectionMixin
from scribe3.store.facts_knowledge import FactsKnowledgeMixin
from scribe3.store.chapters import ChaptersMixin


ROOT = Path(__file__).resolve().parents[2]


def test_leak_markers_nonempty_from_target_field():
    marks = auto_generate_leak_markers("faction:衔尾蛇", "origin", "不可名状之处藏着炉心")
    assert marks
    assert any("衔尾蛇" in m or m == "衔尾蛇" for m in marks)
    assert "origin" in marks
    assert any("炉心" in m or "不可名状" in m for m in marks)


def test_secret_bridge_passes_leak_markers():
    seen = {}

    class St:
        def find_bridge_proposition_local(self, *a, **k):
            return None

        def upsert_bridge_proposition(self, **kw):
            seen.update(kw)
            return "loc1"

        def semantic_index(self, *a, **k):
            return None

        db_name = "w"

    row = {
        "origin": "不可名状之处",
        "origin_secret": True,
    }
    out = sync_faction_secrets(St(), "衔尾蛇", row)
    assert out.get("created", 0) >= 1 or seen
    assert seen.get("leak_markers")
    assert all(seen["leak_markers"])


def test_after_canon_apply_calls_digest_and_secrets():
    calls = []

    class St:
        db_name = "w"

        def get_faction(self, name):
            return {"name": name, "origin": "秘", "origin_secret": True}

        def semantic_index(self, eid, text):
            calls.append(("index", eid, text))

        def upsert_bridge_proposition(self, **kw):
            calls.append(("upsert", kw))
            return "x"

        def find_bridge_proposition_local(self, *a, **k):
            return None

        def delete_bridge_proposition(self, *a, **k):
            return None

    import scribe3.canon_apply_sync as S

    def fake_digest(store, kind, eid, row):
        calls.append(("digest", kind, eid))
        return {"created": 1}

    orig = S.sync_entity_digests if hasattr(S, "sync_entity_digests") else None
    import scribe3.codex_digest as D
    old = D.sync_entity_digests
    D.sync_entity_digests = fake_digest
    try:
        stats = after_canon_apply(St(), "faction", "faction:衔尾蛇", {"name": "衔尾蛇", "origin": "秘", "origin_secret": True})
    finally:
        D.sync_entity_digests = old
    assert any(c[0] == "digest" for c in calls)
    assert stats.get("digest") or any(c[0] == "digest" for c in calls)


def test_apply_item_wires_sync():
    src = inspect.getsource(apply_item_to_store)
    assert "_sync_after_apply" in src


def test_cleanup_covers_proposition_material_canon():
    src = inspect.getsource(ConnectionMixin._cleanup_record_refs)
    assert "DELETE proposition" in src
    assert "about_entities" in src
    assert "canon_candidate" in src
    df = inspect.getsource(FactsKnowledgeMixin.delete_faction)
    assert "_cleanup_record_refs" in df
    perm = inspect.getsource(ChaptersMixin.delete_chapter_permanent)
    assert "canon_candidate" in perm
    arch = inspect.getsource(ChaptersMixin.archive_chapter)
    assert "dismissed" in arch or "canon_candidate" in arch


def test_frontend_live_bus_and_hint_handler():
    insight = (ROOT / "scribe3/web/src/views/InsightView.jsx").read_text(encoding="utf-8")
    assert "s3-live" in insight
    tl = (ROOT / "scribe3/web/src/views/TimelineView.jsx").read_text(encoding="utf-8")
    assert "s3-live" in tl
    codex = (ROOT / "scribe3/web/src/layout/CodexDirectory.jsx").read_text(encoding="utf-8")
    assert "s3-live" in codex
    gw = (ROOT / "scribe3/web/src/settings/GatewaySection.jsx").read_text(encoding="utf-8")
    assert "retryUntilOnline" in gw
    ui = (ROOT / "scribe3/web/src/lib/uiDirective.js").read_text(encoding="utf-8")
    assert "s3-chapter-phase-hint" in ui
