"""铜炉第四轮收尾：日志、分层、素材 hybrid、ingest 重试。不起 Surreal。"""
from __future__ import annotations

import inspect
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_m1_outline_snapshot_logs_warning():
    from scribe3.stage_generate import _thicken_stage_body
    src = inspect.getsource(_thicken_stage_body)
    assert "outline snapshot failed" in src
    assert "except Exception as e" in src


def test_m3_store_has_no_api_import():
    store_dir = ROOT / "scribe3/store"
    bad = []
    for p in store_dir.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        if "from scribe3.api" in text or "import scribe3.api" in text:
            bad.append(str(p.relative_to(ROOT)))
    assert bad == []
    src = (ROOT / "scribe3/store/connection.py").read_text(encoding="utf-8")
    assert "scribe3.diagnostics.budget_report" in src


def test_p2_hybrid_fuses_vector_neighbors():
    from scribe3.store.materials import rank_materials_hybrid
    items = [
        {"id": "a", "title": "刀剑谱", "body": "刀与剑的用法"},
        {"id": "b", "title": "兵器录", "body": "各类兵器"},
        {"id": "c", "title": "茶经", "body": "喝茶"},
    ]
    vec = {"a": 0.82, "b": 0.71, "c": 0.05}
    ranked = rank_materials_hybrid("剑", items, vec_scores=vec)
    ids = [m["id"] for m in ranked]
    assert ids[0] == "a"
    assert "b" in ids[:2]


def test_p2_ingest_retry_caps_at_three():
    from scribe3.ingest_integrity import checkpoint_ingest, retry_failed_ingests

    class St:
        def __init__(self):
            self._ingest_checkpoints = {}

        def _execute_write(self, *a, **k):
            return None

        def _query(self, *a, **k):
            return []

    st = St()
    checkpoint_ingest(st, 9, ok=False, needs_replay=True, retry_count=3, delta={"learned": []})
    out = retry_failed_ingests(st, max_retries=3)
    assert out["skipped"]
    assert out["skipped"][0]["seq"] == 9


def test_precheck_hint_and_extract_queue():
    from scribe3.journey_precheck import journey_precheck_block
    import os
    os.environ["SCRIBE3_JOURNEY_PRECHECK"] = "1"

    class Empty:
        def chapter_count(self):
            return 0

        def get_intent(self):
            return {}

        def list_motifs(self):
            return []

    try:
        block = journey_precheck_block(Empty())
        assert block and block.get("hint") == "请先完成旅程设定"
    finally:
        os.environ["SCRIBE3_JOURNEY_PRECHECK"] = "0"
    from scribe3.extract_retry import queue_extract_retry, pending_extracts, retry_pending_extracts
    queue_extract_retry("炉火", reason="boom")
    assert pending_extracts()
    retry_pending_extracts(complete_fn=None)
    src = inspect.getsource(__import__("scribe3.stage_generate", fromlist=["_thicken_stage_body"])._thicken_stage_body)
    assert "separators" in src
    assert "_log.warning" in src


def test_frontend_round4_wires():
    api = (ROOT / "scribe3/web/src/api.js").read_text(encoding="utf-8")
    assert "once: true" in api
    assert "idleMs" in api
    assert "onRetry" in api
    dock = (ROOT / "scribe3/web/src/studioDocks.jsx").read_text(encoding="utf-8")
    assert "dismissBusy" in dock
    assert "disabled={dismissBusy === it.id}" in dock
    chat = (ROOT / "scribe3/web/src/WriteChat.jsx").read_text(encoding="utf-8")
    assert "重新连接中" in chat
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "write_path_sync_ok" in ci
    assert "store_layer_ok" in ci
