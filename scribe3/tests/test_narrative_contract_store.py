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
    assert "focalizer" in CHAPTER_META_ALLOWED


def test_coerce_and_dump_roundtrip():
    dumped = dump_chapter_json_meta(CONTRACT)
    assert isinstance(dumped, str)
    back = coerce_chapter_json_dict(dumped)
    assert back["turn"] == CONTRACT["turn"]
    assert coerce_chapter_json_dict(None) == {}
    assert coerce_chapter_json_dict("not-json") == {}
    assert dump_chapter_json_meta(None) is None


def test_extract_contract_from_ch4_style_outline():
    from scribe3.narrative_contract import (
        extract_contract_from_iceberg,
        merge_iceberg_contract,
    )
    ch = {
        "synopsis": (
            "1. 日子\n集快散了。\n\n2. 必须发生\n"
            "冷锅婆把陈灰按进灰七掌心，他攥住不甩。\n\n"
            "3. 因 → 果\n她怕侧门再被人试缝；他怕炉未冷漏真名。"
            "他用清香债挡话，挡不干净。\n\n"
            "4. 不能说\n不许念亡父真名。\n\n"
            "5. 章末未决\n场散了，炉册夜审要点名，炉凉不凉还挂着。\n"
        ),
        "beats": [{
            "text": (
                "**进场：** 他要去旧库侧门核对擦痕。\n**事件：** 空锅拦路按灰。\n"
                "**翻转：** 他清债挡话，她不让路。\n"
                "**出场：** 掌心里那撮凉灰。\n**水下：** 炉其实未冷。\n"
            ),
        }],
    }
    got = extract_contract_from_iceberg(ch)
    desire = got.get("desire") or ""
    obstacle = got.get("obstacle") or ""
    assert "像翻一只碗" not in desire
    assert "清香债" in desire or "挡话" in desire or "侧门" in desire
    assert obstacle
    assert obstacle[:32] not in desire
    assert "不让" in (got.get("turn") or "") or "挡" in (got.get("turn") or "")
    assert "夜审" in (got.get("cost") or "") or "凉" in (got.get("cost") or "") or "掌心" in (got.get("cost") or "")
    assert "“" not in (got.get("cost") or "") and "”" not in (got.get("cost") or "")
    merged = merge_iceberg_contract(ch, {})
    nc = merged["narrative_contract"]
    assert nc["desire"]
    locked = merge_iceberg_contract(
        {**ch, "narrative_contract": {"locked": True, "desire": "作者已写"}},
        {},
    )
    assert "narrative_contract" not in locked


def test_repair_replaces_scene_dump_iceberg_contract():
    from scribe3.narrative_contract import repair_iceberg_contract

    ch = {
        "synopsis": (
            "1. 日子\n集快散了。\n\n2. 必须发生\n"
            "冷锅婆把空锅翻转向他，像翻一只碗。锅是空的，只有锅底卧着一小撮陈灰。\n\n"
            "3. 因 → 果\n他用清香债挡话，挡不干净。她怕侧门再被人试缝。\n\n"
            "5. 章末未决\n炉册夜审要点名，炉凉不凉还挂着。\n"
        ),
        "beats": [{
            "text": (
                "**进场：** 散集。\n**事件：** 空锅拦路按灰。\n"
                "**翻转：** 他清债挡话，她不让路。\n"
                "**出场：** 掌心里那撮凉灰。\n"
            ),
        }],
        "narrative_contract": {
            "source": "iceberg",
            "desire": "冷锅婆把空锅翻转向他，像翻一只碗。锅是空的，只有锅底卧着一小撮陈灰，不知搁了多少天。她伸出两根指头，从锅底捻起那撮灰，不等灰七后退，已经按进他掌心里。",
            "obstacle": "她伸出两根指头，从锅底捻起那撮灰，不等灰七后退，已经按进他掌心里",
            "turn": "是两头越逼越紧的怕。",
            "cost": "灰七把三集香债的钱数出来",
        },
    }
    nxt, changed = repair_iceberg_contract(ch)
    assert changed is True
    assert "像翻一只碗" not in (nxt.get("desire") or "")
    assert (nxt.get("obstacle") or "")[:32] not in (nxt.get("desire") or "")
    locked_ch = {**ch, "narrative_contract": {**ch["narrative_contract"], "locked": True, "source": "author"}}
    same, changed2 = repair_iceberg_contract(locked_ch)
    assert changed2 is False
    assert same.get("locked") is True


def test_slot_prompt_leak_is_dirty_and_skipped():
    from scribe3.narrative_contract import (
        extract_contract_from_iceberg,
        iceberg_contract_dirty,
        repair_iceberg_contract,
    )
    dirty = {
        "source": "iceberg",
        "desire": "",
        "obstacle": "不拜，不祷告，就是直挺挺跪下去",
        "turn": "名里那个字烧进眼仁",
        "cost": "下一章的动作与把柄",
    }
    assert iceberg_contract_dirty(dirty, {}) is True
    leak_outline = {
        "synopsis": (
            "1. 日子\n巷口等开门。\n\n2. 必须发生\n"
            "他要在炉冷之前把那粒焦黑还回去。灰狸把假铜片递过来。\n\n"
            "3. 因 → 果\n他没接那片铜。婆子拦着说账勾了门没开。\n\n"
            "5. 章末未决\n门内咳了一声，名字没出口。\n"
        ),
        "beats": [{
            "text": (
                "**进场：** 他要对照撕角半侧与门枢埋灰。\n"
                "**事件：** 灰狸跟来，婆子空锅堵在巷口。\n"
                "**翻转：** 灰被翻过，底下压着一粒焦黑。\n"
                "**出场：** 门内弹了匙齿，天亮前不能张嘴。\n"
                "**水下：** 为什么非发生不可\n"
            ),
        }],
        "narrative_contract": dirty,
    }
    got = extract_contract_from_iceberg(leak_outline)
    assert "下一章" not in (got.get("cost") or "")
    assert "为什么非发生不可" not in json.dumps(got, ensure_ascii=False)
    assert got.get("desire")
    nxt, changed = repair_iceberg_contract(leak_outline)
    assert changed is True
    assert nxt.get("desire")
    assert "下一章的动作与把柄" not in (nxt.get("cost") or "")


def test_extract_strips_half_quotes_from_cost():
    from scribe3.narrative_contract import extract_contract_from_iceberg
    ch = {
        "synopsis": "5. 章末未决\n名还在册上还没勾。\n",
        "beats": [{
            "text": (
                "**进场：** 他要去旧库侧门核对擦痕。\n"
                "**事件：** 空锅拦路按灰。\n"
                "**出场：** “那角纸，你收好。\n"
            ),
        }],
    }
    got = extract_contract_from_iceberg(ch)
    assert "“" not in (got.get("cost") or "")
    assert "角纸" in (got.get("cost") or "") or "册" in (got.get("cost") or "")


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
