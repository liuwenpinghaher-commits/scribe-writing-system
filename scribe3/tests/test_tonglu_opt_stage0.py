"""2026-08-23 铜炉最优化 Stage 0：打真实入口，不起 Surreal。"""
from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

from scribe3.chapter_lock import acquire_chapter_lock, release_chapter_lock
from scribe3.chapter_versions import select_versions_to_drop
from scribe3.codex_digest import digest_payloads, kind_field_groups
from scribe3.codex_generate import spec_ask
from scribe3.codex_schema import CodexField, all_storage_keys, filter_patch_fields, fields_for
from scribe3.playbook.duty_gate import refuse_empty_synopsis
from scribe3.playbook.pipeline import run_stage
from scribe3.promise_overdue_gate import (
    OVERDUE_HARD_THRESHOLD,
    check_overdue_hard,
    count_open_overdue,
    overdue_hard_block,
)
from scribe3.store.characters import CharactersMixin
from scribe3.store.codex_ext import CodexExtMixin
from scribe3.store.materials import MaterialsMixin
from scribe3.store.promises import PromisesMixin


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/plans/2026-08-23-tonglu-optimization-spec.md"
LEDGER = ROOT / "docs/plans/2026-08-23-tonglu-opt-ledger.md"
LEDGER_JSON = ROOT / "docs/plans/2026-08-23-tonglu-opt-ledger.json"
ID_RE = re.compile(r"\b((?:SYS|DSH|CDX|MAT|ATL|PRM|MOT|TML|JNY|DIR|MAN|DED|CRS|T13)-\d+)\b")
EXPECTED = (
    [f"SYS-{i:02d}" for i in range(1, 15)]
    + [f"DSH-{i:02d}" for i in range(1, 10)]
    + [f"CDX-{i:02d}" for i in range(1, 18)]
    + [f"MAT-{i:02d}" for i in range(1, 9)]
    + [f"ATL-{i:02d}" for i in range(1, 10)]
    + [f"PRM-{i:02d}" for i in range(1, 10)]
    + [f"MOT-{i:02d}" for i in range(1, 8)]
    + [f"TML-{i:02d}" for i in range(1, 9)]
    + [f"JNY-{i:02d}" for i in range(1, 9)]
    + [f"DIR-{i:02d}" for i in range(1, 19)]
    + [f"MAN-{i:02d}" for i in range(1, 12)]
    + [f"DED-{i:02d}" for i in range(1, 25)]
    + [f"CRS-{i:02d}" for i in range(1, 8)]
    + [f"T13-{i:02d}" for i in range(1, 9)]
)


def _ids(text: str) -> set[str]:
    return set(ID_RE.findall(text or ""))


def test_ledger_covers_every_spec_id():
    spec_ids = _ids(SPEC.read_text(encoding="utf-8"))
    led_ids = _ids(LEDGER.read_text(encoding="utf-8"))
    data = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    json_ids = {row["id"] for row in data}
    missing = set(EXPECTED) - spec_ids
    assert not missing, missing
    assert set(EXPECTED) <= led_ids
    assert json_ids == set(EXPECTED)
    assert spec_ids >= set(EXPECTED)


def test_t13_01_fake_stream_named_hermes():
    src = (ROOT / "scribe3/tests/test_pulse.py").read_text(encoding="utf-8")
    assert 'fake_stream.__name__ = "hermes_complete_stream"' in src


def test_atl_01_characters_sql_excludes_archived():
    src = inspect.getsource(CharactersMixin.characters)
    assert "archived" in src
    assert "archived != true" in src or "archived = false" in src.lower()


def test_cdx_02_item_digest_uses_real_fields():
    groups = kind_field_groups("item")
    keys = {k for _, ks in groups for k in ks}
    assert "function" not in keys
    assert "description" in keys
    assert "current_owner" in keys
    rows = digest_payloads("item", "item:铜炉", {
        "name": "铜炉",
        "description": "收债的炉",
        "current_owner": "沈拾灯",
        "function": "不应出现",
        "origin": "也不应作为字段名",
    })
    blob = " ".join(p.get("value") or "" for p in rows)
    assert "收债的炉" in blob
    assert "沈拾灯" in blob
    assert "function：" not in blob


def test_cdx_01_filter_keeps_schema_key_outside_legacy_tuple():
    legacy = {
        "category", "description", "current_owner", "symbolic_state",
        "special_properties", "first_chapter", "name",
    }
    extra = CodexField("new_plot_hook", "新钩", "text")
    import scribe3.codex_schema as cs
    old = cs.KINDS["item"]
    try:
        cs.KINDS["item"] = old + (extra,)
        out = filter_patch_fields("item", {"new_plot_hook": "x", "not_a_field": 1})
        assert out["new_plot_hook"] == "x"
        assert "not_a_field" not in out
        assert "new_plot_hook" not in legacy
    finally:
        cs.KINDS["item"] = old
    src = inspect.getsource(CodexExtMixin.patch_item)
    assert "_codex_filter_patch" in src or "filter_patch_fields" in src
    assert 'if k in ("category"' not in src


def test_cdx_03_spec_ask_includes_schema_keys():
    ask = spec_ask("item")
    for f in fields_for("item"):
        if f.deprecated:
            continue
        assert f.key in ask, f.key


def test_mat_04_delete_emits_invalidation(monkeypatch):
    seen: list = []
    import scribe3.store.materials as M

    monkeypatch.setattr(
        M, "_emit_cache_invalidation",
        lambda *a, **k: seen.append((a, k)),
    )

    class Fake(MaterialsMixin):
        db_name = "book_x"

        def _material_exists(self, _mid):
            return True

        def _delete_by(self, *_a, **_k):
            return None

    assert Fake().delete_material("m1") is True
    assert seen, "delete_material 必须发 cache invalidation"


def test_ded_01_02_second_lock_busy_in_other_context():
    r1 = acquire_chapter_lock("run", "book_lock", 3, store=None, ttl_seconds=30)
    assert r1.ok
    r2 = acquire_chapter_lock("run", "book_lock", 3, store=None, ttl_seconds=30)
    try:
        assert not r2.ok
        assert r2.status == "busy"
    finally:
        release_chapter_lock("run", "book_lock", 3, store=None)

    from scribe3.api.routers.write import chat_write, chat_write_post
    from scribe3.playbook.pipeline import run_stage as rs
    assert "acquire_chapter_lock" in inspect.getsource(chat_write) or "_lock_chapter_run" in inspect.getsource(chat_write)
    assert "_lock_chapter_run" in inspect.getsource(chat_write_post)
    assert "acquire_chapter_lock" in inspect.getsource(rs)


def test_ded_02_run_stage_busy_when_lock_held():
    class Fake:
        db_name = "book_lock2"

        def get_frozen(self, *_a, **_k):
            return None

        def get_chapter(self, *_a, **_k):
            return {"synopsis": "今夜必须打开箱子"}

    held = acquire_chapter_lock("run", "book_lock2", 4, store=None, ttl_seconds=30)
    assert held.ok
    try:
        out = run_stage(
            Fake(), 4, "duty",
            llm_fn=lambda *_a, **_k: "{}",
            ctx={"synopsis": "今夜必须打开箱子"},
            persist=False,
        )
        assert out.get("ok") is False
        assert out.get("code") == "chapter_busy"
    finally:
        release_chapter_lock("run", "book_lock2", 4, store=None)


def test_ded_06_empty_synopsis_refused():
    assert refuse_empty_synopsis({"synopsis": ""})["ok"] is False
    assert refuse_empty_synopsis({"synopsis": "   "})["code"] == "empty_synopsis"
    assert refuse_empty_synopsis({"synopsis": "今夜必须打开金縢"}) is None

    class Fake:
        db_name = "book_syn"

        def get_frozen(self, *_a, **_k):
            return None

        def get_chapter(self, *_a, **_k):
            return {"synopsis": ""}

    out = run_stage(
        Fake(), 1, "duty",
        llm_fn=lambda *_a, **_k: "{}",
        ctx={"synopsis": ""},
        persist=False,
    )
    assert out.get("ok") is False
    assert out.get("code") == "empty_synopsis"


def test_prm_01_overdue_threshold_blocks():
    assert overdue_hard_block(2) is None
    hit = overdue_hard_block(OVERDUE_HARD_THRESHOLD)
    assert hit and hit["allowed"] is False and hit["code"] == "promise_overdue"
    rows = [
        {"status": "open", "kind": "promise", "setup_chapter": 1, "payoff_max": 3},
        {"status": "open", "kind": "promise", "setup_chapter": 1, "payoff_max": 3},
        {"status": "open", "kind": "promise", "setup_chapter": 1, "payoff_max": 3},
    ]
    n = count_open_overdue(rows, max_chapter=10, slack=3)
    assert n == 3
    assert overdue_hard_block(n)["blocking"] is True

    class Fake:
        def open_promises(self):
            return rows

        def max_chapter(self):
            return 10

        def get_intent(self):
            return {}

    assert check_overdue_hard(Fake())["code"] == "promise_overdue"

    from scribe3.finalize_gate import check_finalize_for_save
    src = inspect.getsource(check_finalize_for_save)
    assert "check_overdue_hard" in src
    from scribe3.api.routers.write import _reject_overdue_hard
    assert "check_overdue_hard" in inspect.getsource(_reject_overdue_hard)


def test_prm_02_advance_cas_and_touch_dedup():
    src = inspect.getsource(PromisesMixin.advance_promise)
    assert "WHERE status='open'" in src or 'WHERE status="open"' in src
    touch = inspect.getsource(PromisesMixin.add_promise_touch)
    assert "ingest_seq" in touch
    assert "LIMIT 1" in touch
    mig = (ROOT / "scribe3/migrations/161_promise_touch_unique.surql").read_text(encoding="utf-8")
    assert "UNIQUE" in mig
    assert "promise_touch" in mig


def test_man_01_version_pagination_and_retention():
    src = inspect.getsource(__import__("scribe3.store.chapters", fromlist=["ChaptersMixin"]).ChaptersMixin.list_chapter_versions)
    assert "LIMIT" in src
    rows = [
        {"id": f"v{i}", "kind": "checkpoint"} for i in range(30)
    ]
    rows[25]["kind"] = "milestone"
    drop = select_versions_to_drop(rows, keep_recent=20)
    drop_ids = {r["id"] for r in drop}
    assert "v25" not in drop_ids
    assert len(drop) == 9  # 30-20-1 milestone
    from scribe3.store.chapters import ChaptersMixin
    assert "prune_chapter_versions" in inspect.getsource(ChaptersMixin.add_chapter_version)


def test_sys_01_02_admin_confirm_and_toast():
    admin = (ROOT / "scribe3/web/src/admin/AdminConsole.jsx").read_text(encoding="utf-8")
    assert "ConfirmDialog" in admin
    assert "showToast" in admin
    assert "转让书籍归属" in admin or "转让归属" in admin
    assert "重置密码" in admin
    assert "alert(" not in admin
    settings = (ROOT / "scribe3/web/src/settings/SettingField.jsx").read_text(encoding="utf-8")
    assert "showToast" in settings
    assert 'autoComplete="off"' in settings
