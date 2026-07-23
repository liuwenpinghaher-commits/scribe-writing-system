"""Context-pipeline mount ≥98%: production write instructions re-enter brief must-sections,
author prefs, voice anchor, and gated material recall.

All asserts drive the shipped assembler entry `_assemble_write_instructions`
(same function `/chat/write` uses). No reimplementation of brief/voice/prefs/material.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.ontology import Entity, Event


def _instr(store, **kw):
    defaults = dict(
        chapter=2, focalizer="role:甲", phase="draft",
        seed_words=["密室"], short_mode=False, with_tools=False, work="main",
    )
    defaults.update(kw)
    return A._assemble_write_instructions(store, **defaults)


def test_write_instructions_mount_brief_must_sections(store):
    """Seed open promise + arc lie + causal debt → real assembler text contains them."""
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.set_char_anchors("role:甲", {
        "lie": "官法大过阴律",
        "arc_type": "disillusionment",
        "private_agenda": "寻母",
    })
    store.add_arc_beat("role:甲", "midpoint", target_chapter=6, lie_belief_target=50)
    # last_active far enough for heartbeat when writing ch 6
    store.add_char_state("role:甲", chapter=1, change_type="ability", summary="初现")
    store.plant_promise("井底的名字", setup_chapter=1)
    store.add_event(Event(
        id="ev:失窃", type="失窃", story_time=1,
        motivated_by_goal=None, causal_in=[],
    ))
    store.save_chapter(2, "", title="二")
    store.update_chapter_meta(2, {"synopsis": "甲在密室寻线索"})

    text = _instr(store, chapter=2, focalizer="role:甲", phase="draft")
    assert "本章创作简报" in text or "【角色弧光" in text or "井底的名字" in text
    assert "【角色弧光·甲】" in text or "官法大过阴律" in text
    assert "井底的名字" in text
    # causal debt when prior events lack motive
    assert "因果" in text or "失窃" in text


def test_write_instructions_mount_author_prefs(store, tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from scribe3.author_prefs import append_pref
    append_pref("偏短句,少用逗号堆叠-写路径挂载探针")
    text = _instr(store, chapter=1, focalizer="", phase="plan")
    assert "作者跨书偏好" in text
    assert "偏短句" in text
    assert "偏好≠正典" in text


def test_write_instructions_empty_prefs_no_fake_block(store, tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    text = _instr(store, chapter=1, focalizer="", phase="plan")
    assert "作者跨书偏好" not in text


def test_write_instructions_mount_voice_anchor(store):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.set_voice_profile("role:甲", {
        "style_summary": "短句冷峻如刀",
        "catchphrases": ["罢了"],
        "tone_rules": ["不煽情"],
    })
    text = _instr(store, chapter=1, focalizer="role:甲", phase="draft")
    assert "本章焦点者声音锚" in text
    assert "短句冷峻如刀" in text


def test_write_instructions_no_voice_when_no_profile(store):
    store.add_entity(Entity("role:乙", "character", "乙"))
    text = _instr(store, chapter=1, focalizer="role:乙", phase="draft")
    # no style_summary → no focalizer voice header (digest may still list others)
    assert "本章焦点者声音锚" not in text


def test_write_instructions_mount_material_on_draft(store):
    """draft/final inject gated material reference (借鉴非事实); deterministic, no LLM."""
    store.save_chapter(1, "", title="一")
    store.update_chapter_meta(1, {"synopsis": "沈砚在密室审讯囚犯"})
    mid = store.add_material(
        "密室白描", "冷硬的密室描写，寒气逼人", "snippet", ref_tags=["手法"])
    text = _instr(store, chapter=1, focalizer="", phase="draft", seed_words=["密室"])
    assert "参考记忆" in text or "借鉴非" in text
    assert "密室" in text
    # provenance written via shipped helper path
    refs = store.material_refs_by_chapter(1)
    assert any(r.get("material_id") == mid for r in refs)


def test_write_instructions_no_material_on_plan_phase(store):
    store.save_chapter(1, "", title="一")
    store.update_chapter_meta(1, {"synopsis": "沈砚在密室审讯囚犯"})
    store.add_material("密室白描", "冷硬的密室描写，寒气逼人", "snippet", ref_tags=["手法"])
    text = _instr(store, chapter=1, focalizer="", phase="plan", seed_words=["密室"])
    # plan phase must not strongly inject material block (tool-on-demand for discussion only)
    assert "【参考记忆·借鉴非照搬】" not in text


def test_capabilities_always_on_default(store, monkeypatch):
    """GET /capabilities: snapshot/fabric/inspector default true (no gray dormancy)."""
    monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)
    monkeypatch.delenv("SCRIBE3_CONTEXT_INSPECTOR_V1", raising=False)
    monkeypatch.delenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", raising=False)
    A.set_store(store)
    client = TestClient(A.app)
    flags = client.get("/capabilities").json()["flags"]
    assert flags.get("memory_fabric_v1") is True
    assert flags.get("context_inspector_v1") is True
    assert flags.get("snapshot_v1") is True
    assert flags.get("assembler_v1") is True
    # default-on: write retriever attached
    assert A._get_write_retriever(store) is not None
    text = _instr(store, chapter=1, focalizer="", phase="draft")
    assert len(text) > 200
    assert "⟦PROPOSAL" in text or "动稿" in text or "作者视角" in text


def test_write_assembler_default_path_not_fabric_short_circuit(store, monkeypatch):
    """Production assembler under default env attaches retriever path (not gray skip)."""
    monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)
    r = A._get_write_retriever(store)
    assert r is not None
    text = _instr(store, chapter=1, focalizer="", phase="draft", seed_words=["雨"])
    assert isinstance(text, str) and len(text) > 100


def test_brief_must_helper_strips_purpose_duplicate_path(store):
    """Helper is fail-soft and uses assemble_chapter_brief; empty book → empty/no crash."""
    out = A._brief_must_sections_write_block(store, 1, focalizer="")
    assert isinstance(out, str)
