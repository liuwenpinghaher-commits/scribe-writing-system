"""铜炉第三轮：反向 import、prune 批量删、调度纯计算、precheck 豁免。不起 Surreal。"""
from __future__ import annotations

import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_s0_store_does_not_import_quality_router():
    src = inspect.getsource(__import__("scribe3.store.chapters", fromlist=["ChaptersMixin"]).ChaptersMixin.save_chapter)
    assert "scribe3.api.routers.quality" not in src
    assert "scribe3.quality.cache" in src
    from scribe3.quality.cache import invalidate_quality_cache
    invalidate_quality_cache("ut")


def test_s1_prune_single_delete():
    from scribe3.store.chapters import ChaptersMixin
    src = inspect.getsource(ChaptersMixin.prune_chapter_versions)
    assert "NOT IN $keep_ids" in src
    assert "DELETE type::record('chapter_version'" not in src

    class St(ChaptersMixin):
        def __init__(self):
            self.writes = []
            self.rows = [{"id": str(i), "kind": "checkpoint"} for i in range(30)]

        def list_chapter_versions(self, seq, *, limit=100, offset=0):
            return list(self.rows)

        def _execute_write(self, q, vars=None):
            self.writes.append((q, vars))

    st = St()
    out = st.prune_chapter_versions(1, keep_recent=20)
    assert out["dropped"] == 10
    assert len(st.writes) == 1


def test_s1_schedule_motifs_is_pure():
    from scribe3.motif_craft import apply_motif_advances, schedule_motifs

    class St:
        def __init__(self):
            self.n = 0

        def update_motif(self, mid, fields):
            self.n += 1

    st = St()
    out = schedule_motifs(
        [{"id": "灯", "phase": "seed"}],
        {"灯": [1, 2]},
        3,
        store=st,
    )
    assert st.n == 0
    assert out["advances"]
    assert apply_motif_advances(out["advances"], st) == 1
    assert st.n == 1


def test_s2_precheck_exempts_existing_chapters():
    from scribe3.journey_precheck import journey_precheck_block
    import os
    os.environ["SCRIBE3_JOURNEY_PRECHECK"] = "1"

    class Empty:
        def get_intent(self):
            return {}

        def list_motifs(self):
            return []

        def chapter_count(self):
            return 0

    class HasChapters(Empty):
        def chapter_count(self):
            return 3

    try:
        assert journey_precheck_block(Empty()) is not None
        assert journey_precheck_block(HasChapters()) is None
    finally:
        os.environ["SCRIBE3_JOURNEY_PRECHECK"] = "0"


def test_s2_duty_lookback_capped():
    src = inspect.getsource(__import__("scribe3.playbook.context", fromlist=["playbook_recent_duty_summary"]).playbook_recent_duty_summary)
    assert "min(max(1" in src and ", 10)" in src


def test_s2_lock_docs_mention_async():
    from scribe3.chapter_lock import acquire_chapter_lock, chapter_lock_held_here
    assert "async" in (acquire_chapter_lock.__doc__ or "").lower() or "asyncio" in inspect.getsource(acquire_chapter_lock)
    assert "await" in (chapter_lock_held_here.__doc__ or "")


def test_s4_man03_chapter_seq_and_man05_outline():
    from scribe3.store.chapters import ChaptersMixin
    assert "chapter_seq" in inspect.getsource(ChaptersMixin.delete_chapter_permanent)
    from scribe3.stage_generate import _thicken_stage_body
    assert "kind=\"outline\"" in inspect.getsource(_thicken_stage_body) or "kind='outline'" in inspect.getsource(_thicken_stage_body)


def test_s4_cdx06_embed_entity_and_ded21_alert():
    from scribe3.canon_apply_sync import after_canon_apply, embed_entity
    assert callable(embed_entity)
    assert "embed_entity" in inspect.getsource(after_canon_apply)
    from scribe3.canon_extract import extract_claims_from_prose
    assert "ingest_extract_fail" in inspect.getsource(extract_claims_from_prose)


def test_s4_ded18_state_fail_reason():
    src = inspect.getsource(__import__("scribe3.playbook.pipeline", fromlist=["_run_final"])._run_final)
    assert "draft_frozen" in src
    assert 'result["reason"]' in src


def test_s3_s5_frontend_wires():
    nd = (ROOT / "scribe3/web/src/views/atlas/NodeDetail.jsx").read_text(encoding="utf-8")
    assert "window.prompt" not in nd
    assert "InputDialog" in nd
    assert "withFeedback" in nd
    card = (ROOT / "scribe3/web/src/WriteProposalCard.jsx").read_text(encoding="utf-8")
    assert "withFeedback" in card
    jv = (ROOT / "scribe3/web/src/views/JourneyView.jsx").read_text(encoding="utf-8")
    assert "setTimeout(refreshExtras, 300)" in jv
    api = (ROOT / "scribe3/web/src/api.js").read_text(encoding="utf-8")
    assert "dismissInboxItem" in api
    assert "maxTries" in api
    dock = (ROOT / "scribe3/web/src/studioDocks.jsx").read_text(encoding="utf-8")
    assert "dismissInboxItem" in dock
    wf = (ROOT / "scribe3/web/src/lib/withFeedback.js").read_text(encoding="utf-8")
    assert "showToast" in wf
    imports = nd.count("withFeedback") + card.count("withFeedback") + wf.count("export async function withFeedback")
    assert imports >= 3
