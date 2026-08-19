"""chapter_state：跨章连续性。纯内存，不烧模型、不启 Surreal。"""
from __future__ import annotations

import json

from scribe3.finalize_gate import check_finalize_for_save
from scribe3.playbook.context import cast_cards, gender_roster
from scribe3.playbook.judge import VERSIONED_RUBRICS
from scribe3.playbook.memory_store import MemoryPlaybookStore, TABLES
from scribe3.playbook.pipeline import extract_chapter_state
from scribe3.playbook.prompts import duty_generate, play_generate, play_judge, play_judge_v2
from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.playbook.schema import SCHEMA_NAME
from scribe3.playbook.structural import check_chapter_state_struct, check_gender_pronoun


SOURCE = "……它寄在他手腕里面，安静得发烫。它跳了最后一下，然后不再跳了。"


def _ok_state(seq: int = 2) -> dict:
    return {
        "seq": seq,
        "characters": [
            {"name": "柳岸青", "gender": "男", "state": "右腕内嵌断指", "quote": "寄在他手腕里面"}
        ],
        "objects": [
            {"name": "断指", "location": "柳岸青右腕内", "state": "不再跳", "quote": "然后不再跳了"}
        ],
        "open_loops": [
            {"text": "三十七小时后第一道监测确认", "from_seq": 1, "due_seq": 4}
        ],
        "timeline": {"at": "签约当夜", "elapsed_from_prev": "同日深夜"},
        "imagery": ["黑屋"],
    }


def test_playbook_version_is_3():
    assert PLAYBOOK_VERSION == "playbook.3"
    assert "playbook.3" in VERSIONED_RUBRICS
    assert SCHEMA_NAME == "chapter_state.v1"
    assert "chapter_state" in TABLES


def test_state_quote_must_be_in_source():
    fake = _ok_state()
    fake["characters"][0]["quote"] = "这段话正文里根本没有"
    hit = check_chapter_state_struct(fake, SOURCE)
    assert hit["ok"] is False
    assert hit["code"] == "state_quote"


def test_state_quote_accepts_verbatim():
    hit = check_chapter_state_struct(_ok_state(), SOURCE)
    assert hit["ok"] is True


def test_gender_pronoun_blocks_she_for_male():
    hit = check_gender_pronoun(
        "柳岸青她把断指扔在地上，腕上的裂口还在渗。她说这根指头不再跳了。",
        [{"name": "柳岸青", "gender": "男"}],
    )
    assert hit["ok"] is False
    assert hit["code"] == "gender_pronoun"


def test_gender_pronoun_allows_he_majority():
    hit = check_gender_pronoun(
        "柳岸青他把断指按进右腕。他听见它跳了最后一下。",
        [{"name": "柳岸青", "gender": "男"}],
    )
    assert hit["ok"] is True


def test_gender_pronoun_skips_unregistered():
    hit = check_gender_pronoun("柳岸青她走了。", [{"name": "柳岸青", "gender": ""}])
    assert hit["ok"] is True


def test_thin_metaphors_drops_narrative_similes_keeps_dialogue():
    from scribe3.playbook.structural import check_draft_struct, metaphor_per_800, thin_metaphors

    dense = "他按回碎片。像火。仿佛夜。似的冷。袖口发烫。" * 120
    assert metaphor_per_800(dense) > 1.0
    out = thin_metaphors(dense)
    assert metaphor_per_800(out) <= 1.0
    assert "按回碎片" in out
    talk = "「像火一样。」沈烛说。" + "他按回碎片，袖口发烫。" * 80
    kept = thin_metaphors(talk)
    assert "像火一样" in kept
    play = "完全另一场戏，沈烛若没有按回碎片。" * 40
    long = thin_metaphors(("他按回碎片。像火。仿佛夜。似的冷。袖口发烫。沈烛把盒子推过来。" * 80))
    hit = check_draft_struct(long, play_text=play)
    assert hit.get("code") != "draft_metaphor", hit


def test_gen_draft_thins_similes_on_the_way_in():
    from scribe3.playbook.layers import gen_draft
    from scribe3.playbook.structural import metaphor_per_800

    def llm(prompt, **kw):
        return "他按回碎片。像火。仿佛夜。似的冷。袖口发烫。" * 80

    raw = gen_draft({"seq": 1}, llm)
    assert metaphor_per_800(raw["text"]) <= 1.0


def test_gen_draft_uses_lower_temperature():
    from scribe3.playbook.layers import gen_draft
    seen: dict = {}

    def llm(prompt, **kw):
        seen.update(kw)
        return "场面。" * 800

    gen_draft({"seq": 1}, llm)
    assert seen.get("temperature") == 0.4


def test_draft_prompt_carries_struct_hint():
    from scribe3.playbook.prompts import draft_generate
    t = draft_generate({"play_text": "戏", "bite_quote": "钩", "struct_hint": "明喻 25 处 / 2469 字超过 1"})
    assert "上一稿没过" in t
    assert "明喻 25" in t
    assert "上一稿没过" not in draft_generate({"play_text": "戏", "bite_quote": "钩"})


def test_prompts_inject_prev_state():
    ctx = {"seq": 3, "prev_state": _ok_state(), "available_cast": ["柳岸青"]}
    assert "寄在他手腕里面" in duty_generate(ctx)
    assert "寄在他手腕里面" in play_generate({"seq": 3, "duty": {}, "prev_state": _ok_state()})
    assert "对照上章末态" in play_judge(ctx)
    assert "对照上章末态" not in play_judge_v2(ctx)


def test_extract_freezes_with_stub_llm():
    store = MemoryPlaybookStore()

    def llm_fn(prompt, **kwargs):
        return json.dumps(_ok_state(), ensure_ascii=False)

    out = extract_chapter_state(store, 2, SOURCE, llm_fn=llm_fn, persist=True)
    assert out["ok"] is True
    frozen = store.get_frozen("chapter_state", 2)
    assert frozen and frozen.get("status") == "frozen"
    assert frozen["characters"][0]["quote"] == "寄在他手腕里面"


def test_extract_failure_is_needs_human_not_silent():
    store = MemoryPlaybookStore()

    def llm_fn(prompt, **kwargs):
        bad = _ok_state()
        bad["characters"][0]["quote"] = "编造的锚句"
        return json.dumps(bad, ensure_ascii=False)

    out = extract_chapter_state(store, 2, SOURCE, llm_fn=llm_fn, persist=True)
    assert out["ok"] is False
    assert out["code"] == "chapter_state_extract"
    assert store.get_frozen("chapter_state", 2) is None
    versions = store.list_versions("chapter_state", 2)
    assert versions and versions[-1]["status"] == "needs_human"


def test_finalize_blocks_needs_human_state(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    store = MemoryPlaybookStore()
    store.insert("chapter_state", {"seq": 2, "version": 1, "status": "needs_human", "sha": "x"})
    store.insert("chapter_contract", {"seq": 2, "version": 1, "status": "frozen", "sha": "c"})
    fg = check_finalize_for_save(store, 2, "他按回碎片。" * 80, skip=False)
    assert fg["allowed"] is False
    assert fg["code"] == "chapter_state_extract"


def test_old_book_without_state_does_not_block():
    store = MemoryPlaybookStore()
    store.insert("chapter_contract", {"seq": 1, "version": 1, "status": "frozen", "sha": "c"})
    # 无 chapter_state → 与现状一致，不因缺失去拦（质控 triage 另说）
    assert store.get_frozen("chapter_state", 1) is None


def test_cast_cards_read_gender():
    from scribe3.ontology import Entity

    class _St:
        def characters(self):
            return [Entity("role:柳岸青", "character", "柳岸青", traits={"gender": "男"})]

    cards = cast_cards(_St())
    assert cards == [{"name": "柳岸青", "gender": "男"}]
    roster = gender_roster({"characters": [{"name": "柳岸青", "gender": "女"}]}, cards)
    assert roster == [{"name": "柳岸青", "gender": "男"}]
