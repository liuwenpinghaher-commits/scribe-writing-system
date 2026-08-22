"""讨论路径限知/时间一致性 + 可观测(立即阶段)。

驱动 shipped:
- brief.assemble_injection 按章 facts_at(seq)
- chat_stream / agentic 调用 _editor_system(chapter=seq)
- context_snapshot 产品默认开
- discuss 组装指标进入 metrics_snapshot
"""
from __future__ import annotations

import inspect

import pytest

from scribe3 import context_cache as cc
from scribe3.brief import assemble_injection
from scribe3.context_service import context_snapshot_flag_enabled, FLAG_ENV
from scribe3.ontology import Fact


def test_context_snapshot_product_default_on(monkeypatch, tmp_path):
    """产品默认开:无 env 覆盖且空 settings DB 时 flag 为 True。"""
    monkeypatch.delenv(FLAG_ENV, raising=False)
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "settings.sqlite3"))
    from scribe3 import settings as S
    # 强制走 registry 默认
    assert S.get_setting(FLAG_ENV) is True
    assert context_snapshot_flag_enabled() is True


def test_assemble_injection_uses_chapter_time_gate():
    """有 seq 时不得用 99999 灌入未来 valid_from 命题(内存 World,无 Surreal)。"""
    from scribe3.ontology import World

    w = World()
    w.add_fact(Fact("fact:a", "entity:a", "status", "已现身", valid_from=1, valid_to=None, secret=False))
    w.add_fact(Fact("fact:b", "entity:b", "secret_reveal", "终局钥匙", valid_from=20, valid_to=None, secret=False))
    early = assemble_injection(w, 3)
    late = assemble_injection(w, 25)
    early_attrs = {(f.entity_id, f.attribute) for f in early["facts"]}
    late_attrs = {(f.entity_id, f.attribute) for f in late["facts"]}
    assert ("entity:a", "status") in early_attrs
    assert ("entity:b", "secret_reveal") not in early_attrs, "第3章不得见 valid_from=20 的命题"
    assert ("entity:b", "secret_reveal") in late_attrs


def test_chat_stream_passes_chapter_to_editor_system():
    """生产讨论入口是 assemble_discussion_system，不是 _editor_system。"""
    import scribe3.api.routers.misc_routes as misc
    src = inspect.getsource(misc.chat_stream)
    assert "assemble_discussion_system" in src
    assert "user_msg=msg" in src or "user_msg = msg" in src.replace(" ", "")
    assert "chapter=seq" in src or "chapter = seq" in src.replace(" ", "")


def test_chat_agentic_also_passes_chapter():
    import scribe3.api.routers.misc_routes as misc
    src = inspect.getsource(misc.chat_agentic_stream)
    assert "chapter=seq" in src


def test_discuss_assembly_metrics_recorded():
    cc.reset_metrics_for_test()
    cc.record_discuss_assembly(
        12.5, 800, chapter=3, work="book_demo", thread_id="ethread:book_demo:abc",
        path="chat_stream",
    )
    m = cc.metrics_snapshot()
    assert m["discuss_assembly_samples"] == 1
    assert m["discuss_assembly_p50"] is not None
    assert m["discuss_chars_p95"] is not None
    assert isinstance(m.get("discuss_recent"), list)
    assert m["discuss_recent"][-1]["work"] == "book_demo"
    assert m["discuss_recent"][-1]["chapter"] == 3
    # 无 prompt 泄漏
    blob = str(m)
    assert "secret" not in blob.lower() or "secret_reveal" not in blob
    assert "请写入" not in blob
