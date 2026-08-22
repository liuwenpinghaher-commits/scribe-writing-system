"""PR-1 narrative-mainline pure tests — beat_shape / contract / story claim."""
from __future__ import annotations

import os

try:
    import pytest
except ImportError:  # allow runner without pytest installed
    pytest = None  # type: ignore

from scribe3.narrative_contract import (
    beat_shape,
    conflict_beats_ok,
    validate_narrative_contract,
    format_contract_block,
    migrate_contract_from_drive,
)
from scribe3.review.fp import prose_fp
from scribe3.story_complete import assert_story_claim, build_story_ready, clamp_claim_flags


# §3.4 design table #1–#13
BEAT_CASES = [
    ("冷锅婆拦门讨香债", True, None),
    ("灰狸扯袖口要跟去", True, None),  # 扯/跟 in LEX, not 去 alone
    ("半袋热灰倒进空锅抵账", True, None),
    ("湿脚印", False, "prop_like"),
    ("侧门灰", False, "prop_like"),
    ("匙齿缺口", False, "prop_like"),
    ("他走了", False, ("action_hint_only", "too_short")),  # short + 了；无冲突词
    ("铜匙静静摆在桌面上", False, ("no_conflict_clue",)),
    ("她被迫在债契上按了手印", True, None),
    ("对峙", False, ("too_short",)),  # 在 LEX 但过短
    ("他把铜匙放在桌上了", False, ("action_hint_only",)),  # R2
    ("她走过去看了看侧门", False, ("action_hint_only",)),  # R2
    ("她慢慢走过去拿钥匙", False, ("action_hint_only",)),  # R2
]


def _beat_shape_table_impl(text, expect_ok, reason):
    ok, rs = beat_shape(text)
    assert ok is expect_ok, (text, ok, rs)
    if reason:
        if isinstance(reason, tuple):
            assert any(r in rs for r in reason), (text, rs, reason)
        else:
            assert reason in rs, (text, rs)


if pytest is not None:
    @pytest.mark.parametrize("text,expect_ok,reason", BEAT_CASES)
    def test_beat_shape_table(text, expect_ok, reason):
        _beat_shape_table_impl(text, expect_ok, reason)
else:
    def test_beat_shape_table():
        for text, expect_ok, reason in BEAT_CASES:
            _beat_shape_table_impl(text, expect_ok, reason)


def test_ch5_conflict_beats_ok():
    beats = [
        {"text": "冷锅婆拦门讨香债"},
        {"text": "灰狸扯袖口要跟去"},
        {"text": "半袋热灰倒进空锅抵账"},
    ]
    r = conflict_beats_ok(beats)
    assert r["ok"] is True
    assert r["valid"] == 3


def test_ch4_prop_beats_fail_shape():
    beats = [{"text": "湿脚印"}, {"text": "侧门灰"}, {"text": "匙齿缺口"}]
    r = conflict_beats_ok(beats)
    assert r["ok"] is False
    assert r["valid"] == 0
    assert len(r["prop_like"]) >= 3


def test_validate_contract_min_fields():
    bad = validate_narrative_contract(
        {"desire": "短", "obstacle": "短", "turn": "短", "cost": "短"}
    )
    assert bad["validation"]["ok"] is False
    good = validate_narrative_contract(
        {
            "desire": "灰七要去侧门查昨夜脚印与匙齿",
            "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
            "turn": "热灰抵半债并把假片扔给灰狸",
            "cost": "暂禁侧门且父名挂上夜审阴影",
        }
    )
    assert good["validation"]["ok"] is True


def test_format_contract_block_capped():
    c = {
        "desire": "灰七要去侧门查昨夜脚印与匙齿痕迹",
        "obstacle": "冷锅婆香债拦门加上灰狸缠斗要铜",
        "turn": "热灰抵半债并把假片扔给灰狸打发",
        "cost": "暂禁侧门且父名挂上夜审阴影催债",
    }
    block = format_contract_block(c, max_chars=180)
    assert "叙事合同" in block
    assert len(block) <= 180


def test_migrate_from_drive():
    # cost must meet CONTRACT_MIN_FIELD_CHARS=8 (「答应暂不碰侧门」仅 7 → field_short)
    c = migrate_contract_from_drive(
        {
            "inciting": "昨夜脚印未散想再查侧门",
            "opposition": "冷锅婆空锅拦门讨债",
            "turn": "半袋热灰倒进锅里抵账",
            "cost": "答应暂不碰侧门半步",
        }
    )
    assert c["source"] == "assembled"
    assert c["validation"]["ok"] is True, c["validation"]


def test_clamp_cover_when_story_off(monkeypatch):
    monkeypatch.setenv("SCRIBE3_STORY_COMPLETE", "0")
    monkeypatch.setenv("SCRIBE3_SCENE_COVER_IN_CLAIM", "0")
    f = clamp_claim_flags()
    assert f["STORY_COMPLETE"] is False
    assert f["SCENE_COVER_IN_CLAIM"] is True
    assert any("clamp" in n for n in f["notes"])


def test_assert_story_claim_missing_contract(monkeypatch):
    monkeypatch.setenv("SCRIBE3_STORY_COMPLETE", "1")
    monkeypatch.setenv("SCRIBE3_ANTI_META_BLOCK_CLAIM", "1")
    monkeypatch.setenv("SCRIBE3_ANTI_META", "1")
    monkeypatch.setenv("SCRIBE3_SCENE_COVER_IN_CLAIM", "0")

    prose = "冷锅婆拦门讨香债。灰狸扯袖口要跟去。半袋热灰倒进空锅抵账。炉灰烫手铜腥冲鼻。"

    class St:
        def get_chapter(self, seq):
            return {"beats": [{"text": "冷锅婆拦门讨香债"}]}

        def get_reader_ack(self, work, seq, kind="reader"):
            return None

    out = assert_story_claim(prose, st=St(), work="w", seq=5, require_ack=True)
    assert out["allowed"] is False
    assert out["code"] == "narrative_contract_required"


def test_assert_story_claim_ok_path(monkeypatch):
    monkeypatch.setenv("SCRIBE3_STORY_COMPLETE", "1")
    monkeypatch.setenv("SCRIBE3_ANTI_META_BLOCK_CLAIM", "1")
    monkeypatch.setenv("SCRIBE3_ANTI_META", "1")
    monkeypatch.setenv("SCRIBE3_SCENE_COVER_IN_CLAIM", "0")

    prose = (
        "冷锅婆拦门讨香债，锅沿顶住他小腹。"
        "灰狸扯袖口要跟去，针脚快绷开。"
        "半袋热灰倒进空锅抵账，铜腥混着焦糊味。"
        "灰七掌心烫出红印，答应暂不碰侧门。"
    )
    contract = {
        "desire": "灰七要去侧门查昨夜脚印与匙齿",
        "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
        "turn": "热灰抵半债并把假片扔给灰狸",
        "cost": "暂禁侧门且父名挂上夜审阴影",
        "conflict_beats": [
            {"text": "冷锅婆拦门讨香债"},
            {"text": "灰狸扯袖口要跟去"},
            {"text": "半袋热灰倒进空锅抵账"},
        ],
    }
    fp = prose_fp(prose)

    class St:
        def get_chapter(self, seq):
            return {
                "beats": contract["conflict_beats"],
                "narrative_contract": contract,
            }

        def get_reader_ack(self, work, seq, kind="reader"):
            if kind == "story":
                from scribe3.narrative_contract import contract_content_fp
                return {
                    "prose_fp": fp,
                    "contract_fp": contract_content_fp(contract),
                    "work": work,
                    "seq": seq,
                    "note": "本章戏成立：香债拦门后热灰抵账，代价是暂不碰侧门。",
                    "kind": "story",
                }
            return None

    out = assert_story_claim(
        prose, st=St(), work="book_qe_live5", seq=5, require_ack=True, contract=contract
    )
    assert out["allowed"] is True, out
    assert out["code"] == "ok"
    assert out["story_ready"]["claims"]["may_claim_story"] is True


def test_assert_story_claim_prop_beats_rejected(monkeypatch):
    monkeypatch.setenv("SCRIBE3_STORY_COMPLETE", "1")
    monkeypatch.setenv("SCRIBE3_ANTI_META_BLOCK_CLAIM", "1")
    monkeypatch.setenv("SCRIBE3_ANTI_META", "1")
    monkeypatch.setenv("SCRIBE3_SCENE_COVER_IN_CLAIM", "0")

    prose = "雾里有湿脚印。侧门灰还在。匙齿缺口贴着心跳。他先不推。"
    contract = {
        "desire": "灰七要查清昨夜脚印来源与侧门",
        "obstacle": "没有对手当面拦他只有静物",
        "turn": "他比对缺口却仍不敢推门离开",
        "cost": "什么都没推进只带回烟头余温",
        "conflict_beats": [
            {"text": "湿脚印"},
            {"text": "侧门灰"},
            {"text": "匙齿缺口"},
        ],
    }
    fp = prose_fp(prose)

    class St:
        def get_chapter(self, seq):
            return {"beats": contract["conflict_beats"], "narrative_contract": contract}

        def get_reader_ack(self, work, seq, kind="reader"):
            if kind == "story":
                return {
                    "prose_fp": fp,
                    "note": "这章其实没什么冲突只有静物巡检。",
                    "kind": "story",
                }
            return None

    out = assert_story_claim(
        prose, st=St(), work="w", seq=4, require_ack=True, contract=contract
    )
    assert out["allowed"] is False
    assert out["code"] == "conflict_beats_required"
