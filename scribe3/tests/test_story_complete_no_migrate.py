"""U1：宣称只认落库合同；suggest 不得把 scrape 写成 contract.ok。"""
from __future__ import annotations

from scribe3.narrative_contract import (
    adopt_scene_suggest,
    check_scene_lock,
    contract_content_fp,
    suggest_scene_contract,
    validate_narrative_contract,
)
from scribe3.story_complete import _load_contract, build_story_ready


class _ChStore:
    def __init__(self, chapters: dict):
        self._ch = chapters

    def get_chapter(self, seq):
        return self._ch.get(int(seq), {})

    def get_reader_ack(self, work, seq, kind="reader"):
        return None


def test_nested_drive_no_contract_claim_not_ok():
    drive = {
        "inciting_force": {"summary": "昨夜脚印未散想再查侧门"},
        "opposition": {"who_or_what": "冷锅婆", "wants": "拦门讨香债"},
        "scene_turn": "因「昨夜脚印未散想再查侧门」局势被迫转向，代价面：香债上门",
        "deadline_or_cost": {"if_fail": "父名挂上夜审"},
    }
    st = _ChStore({5: {"narrative_drive": drive, "beats": [{"text": "冷锅婆拦门讨香债"}]}})
    c = _load_contract(st, 5)
    assert c["validation"]["ok"] is False
    assert "missing_contract" in (c["validation"]["errors"] or [])
    sr = build_story_ready("冷锅婆拦门讨香债。灰狸扯袖口。", st=st, work="w", seq=5)
    assert sr["contract"]["ok"] is False
    sug = sr.get("suggest") or {}
    adopted_ok = False
    # suggest 诊断不得写入 contract.ok
    assert sr["contract"]["ok"] is False
    if sug.get("draft"):
        adopted = adopt_scene_suggest(sug["draft"])
        assert adopted["validation"]["ok"] is not True or sr["contract"]["ok"] is False


def test_suggest_nested_drive_candidates_not_str_dict():
    ch = {
        "narrative_drive": {
            "inciting_force": {"summary": "昨夜脚印未散想再查侧门"},
            "opposition": {"who_or_what": "冷锅婆", "wants": "拦门讨香债"},
            "scene_turn": "因「昨夜脚印未散想再查侧门」局势被迫转向，代价面：香债上门",
        },
        "beats": [{"text": "冷锅婆拦门讨香债"}],
    }
    sug = suggest_scene_contract(ch)
    assert sug["persist"] is False
    texts = [x["text"] for x in sug["candidates"]["desire"]]
    assert any("脚印" in t for t in texts)
    obst = " ".join(x["text"] for x in sug["candidates"]["obstacle"])
    assert "{'who" not in obst
    tmpl = [x for x in sug["candidates"]["turn"] if x.get("source") == "here.drive.scene_turn"]
    assert tmpl and tmpl[0].get("template") is True
    assert sug["draft"]["turn"] != tmpl[0]["text"]
    assert not sug["adopted_would_be"]["validation"]["ok"]


def test_template_only_turn_not_in_draft():
    ch = {
        "narrative_drive": {
            "scene_turn": "因「昨夜脚印」局势被迫转向，代价面：香债上门",
        },
    }
    sug = suggest_scene_contract(ch)
    assert sug["draft"]["turn"] == ""
    assert sug["needs_author"] is True
    assert not sug["adopted_would_be"]["validation"]["ok"]


def test_empty_chapter_needs_author():
    sug = suggest_scene_contract({})
    assert sug["needs_author"] is True
    assert not any(sug["draft"].get(k) for k in ("desire", "obstacle", "turn", "cost"))
    assert sug["briefing"]["prev"]["contract"]["turn"] == ""
    assert sug["persist"] is False


def test_repeat_prev_turn_lock_warning():
    draft = {
        "desire": "灰七要去侧门查昨夜脚印与匙齿",
        "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
        "turn": "热灰抵半债并把假片扔给灰狸",
        "cost": "暂禁侧门且父名挂上夜审阴影",
        "traces": ["空锅里一撮热灰"],
    }
    prev = {"turn": "热灰抵半债并把假片扔给灰狸"}
    lock = check_scene_lock(draft, prev_contract=prev)
    codes = [w["code"] for w in lock["warnings"]]
    assert "repeat_prev_turn" in codes


def test_adopt_does_not_carry_persist():
    adopted = adopt_scene_suggest({
        "desire": "灰七要去侧门查昨夜脚印与匙齿",
        "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
        "turn": "热灰抵半债并把假片扔给灰狸",
        "cost": "暂禁侧门且父名挂上夜审阴影",
        "traces": ["空锅里一撮热灰"],
        "persist": True,
        "sources": {"x": 1},
    })
    assert adopted["source"] == "orch"
    assert adopted["bindings"]["evidence_must_show"] == ["空锅里一撮热灰"]
    assert "persist" not in adopted
    assert "sources" not in adopted
    assert adopted["validation"]["ok"] is True


def test_contract_fp_ignores_pressure_stairs():
    a = validate_narrative_contract({
        "desire": "灰七要去侧门查昨夜脚印与匙齿",
        "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
        "turn": "热灰抵半债并把假片扔给灰狸",
        "cost": "暂禁侧门且父名挂上夜审阴影",
        "bindings": {"evidence_must_show": ["空锅里一撮热灰"]},
    })
    b = dict(a)
    # pressure 不进 fp
    fp1 = contract_content_fp(a)
    fp2 = contract_content_fp(b)
    assert fp1 == fp2
    c = dict(a)
    c["bindings"] = {"evidence_must_show": ["空锅里一撮热灰", "另留一痕"]}
    assert contract_content_fp(c) != fp1


def test_suggest_ok_not_copied_into_contract_ok():
    st = _ChStore({1: {
        "narrative_drive": {
            "inciting_force": {"summary": "昨夜脚印未散想再查侧门"},
            "opposition": {"wants": "拦门讨香债"},
        },
    }})
    sr = build_story_ready("冷锅婆拦门。", st=st, work="w", seq=1)
    assert sr["contract"]["ok"] is False
    # even if draft/adopted look ok-ish, contract.ok stays false
    adopted = (sr.get("suggest") or {})
    assert sr["contract"]["ok"] is not True
    _ = adopted
