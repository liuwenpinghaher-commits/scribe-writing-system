"""P0-2：场面合同编解码 + 装载入口（零 Surreal）。"""
from __future__ import annotations

import json

from scribe3.chapter_meta_codec import (
    CHAPTER_JSON_META_KEYS,
    CHAPTER_META_ALLOWED,
    coerce_chapter_json_dict,
    dump_chapter_json_meta,
)
from scribe3.story_constraint_prompt import format_story_contract_head
from scribe3.api.services.write_assemble_context import load_chapter_story_inputs


CONTRACT = {
    "desire": "灰七要去侧门查昨夜脚印与匙齿",
    "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
    "turn": "热灰抵半债并把假片扔给灰狸",
    "cost": "暂禁侧门且父名挂上夜审阴影",
}


def test_json_meta_keys_include_narrative_contract():
    assert "narrative_contract" in CHAPTER_JSON_META_KEYS
    assert "narrative_contract" in CHAPTER_META_ALLOWED


def test_coerce_and_dump_roundtrip():
    dumped = dump_chapter_json_meta(CONTRACT)
    assert isinstance(dumped, str)
    back = coerce_chapter_json_dict(dumped)
    assert back["turn"] == CONTRACT["turn"]
    assert coerce_chapter_json_dict(None) == {}
    assert coerce_chapter_json_dict("not-json") == {}
    assert dump_chapter_json_meta(None) is None


def test_load_inputs_accepts_json_string_contract():
    class St:
        def get_chapter(self, seq):
            return {"narrative_contract": json.dumps(CONTRACT, ensure_ascii=False)}

    inputs = load_chapter_story_inputs(St(), 1)
    head = format_story_contract_head(inputs["contract"])
    assert "【本章必须发生的场面】" in head
    assert "热灰抵半债" in head


def test_select_sql_lists_narrative_contract():
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "store/chapters.py"
    text = src.read_text(encoding="utf-8")
    assert "narrative_drive,narrative_contract" in text.replace(" ", "")
    assert "CHAPTER_META_ALLOWED" in text
    assert "coerce_chapter_json_dict(r.get(\"narrative_contract\"))" in text
    assert "dump_chapter_json_meta" in text


def test_v1_pushes_head_and_reports_inject():
    from pathlib import Path
    v1 = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "format_story_contract_head(" in v1
    assert 'load_chapter_story_inputs(st, chapter)' in v1
    assert '_push(\n                "narrative_contract"' in v1 or '_push(\n                "narrative_contract",' in v1
    assert 'bud_rep["narrative_contract_injected"]' in v1
    assert "empty_narrative_contract" in v1
    assert "narrative_contract_skip" in v1
