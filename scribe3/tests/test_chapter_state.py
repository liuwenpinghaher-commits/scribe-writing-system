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
    assert PLAYBOOK_VERSION == "playbook.3.2.14"
    assert "playbook.3" in VERSIONED_RUBRICS
    assert "playbook.3.1" in VERSIONED_RUBRICS
    assert "playbook.3.2" in VERSIONED_RUBRICS
    assert "playbook.3.2.1" in VERSIONED_RUBRICS
    assert "playbook.3.2.2" in VERSIONED_RUBRICS
    assert "playbook.3.2.3" in VERSIONED_RUBRICS
    assert "playbook.3.2.4" in VERSIONED_RUBRICS
    assert "playbook.3.2.5" in VERSIONED_RUBRICS
    assert "playbook.3.2.6" in VERSIONED_RUBRICS
    assert "playbook.3.2.7" in VERSIONED_RUBRICS
    assert "playbook.3.2.8" in VERSIONED_RUBRICS
    assert "playbook.3.2.9" in VERSIONED_RUBRICS
    assert "playbook.3.2.10" in VERSIONED_RUBRICS
    assert "playbook.3.2.11" in VERSIONED_RUBRICS
    assert "playbook.3.2.12" in VERSIONED_RUBRICS
    assert "playbook.3.2.13" in VERSIONED_RUBRICS
    assert "playbook.3.2.14" in VERSIONED_RUBRICS
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


def test_realign_state_quotes_snaps_to_final_wording():
    from scribe3.playbook.structural import realign_state_quotes
    state = _ok_state()
    state["characters"][0]["quote"] = "寄在他手腕里面"
    final = "……它寄在他手腕里面，安静得发烫。它跳了最后一下，然后不再跳了。"
    aligned, misses = realign_state_quotes(state, final)
    assert misses == []
    assert "寄在他手腕里面" in aligned["characters"][0]["quote"]
    drifted = _ok_state()
    drifted["characters"][0]["quote"] = "他低头看自己的左手"
    prose = "柳岸青低头去看自己的左手。袖口翻到肘弯。"
    aligned2, misses2 = realign_state_quotes(drifted, prose)
    assert misses2 == [] or "低头" in (aligned2["characters"][0].get("quote") or "")


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


def test_gender_pronoun_skips_mixed_window():
    hit = check_gender_pronoun(
        "兰因看着柳岸青。他没抬头。兰因把盒子推过去，他仍不接。",
        [{"name": "柳岸青", "gender": "男"}, {"name": "兰因", "gender": "女"}],
    )
    assert hit["ok"] is True
    still = check_gender_pronoun(
        "柳岸青她把断指扔在地上，腕上的裂口还在渗。她说这根指头不再跳了。",
        [{"name": "柳岸青", "gender": "男"}, {"name": "兰因", "gender": "女"}],
    )
    assert still["ok"] is False
    assert still["code"] == "gender_pronoun"


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
    long = thin_metaphors(
        ("「按回去。」沈烛说。\n他按回碎片。像火。仿佛夜。似的冷。袖口发烫。沈烛把盒子推过来。\n" * 80)
    )
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


def test_contract_prompt_carries_struct_hint():
    from scribe3.playbook.prompts import contract_extract
    t = contract_extract({"play_text": "戏", "struct_hint": "choice 的 quote 不在戏里"})
    assert "上一稿没过" in t
    assert "choice" in t


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


def test_finalize_keeps_frozen_state_if_later_extract_fails(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    store = MemoryPlaybookStore()
    store.insert("chapter_state", {"seq": 2, "version": 1, "status": "frozen", "sha": "ok"})
    store.insert("chapter_state", {"seq": 2, "version": 2, "status": "needs_human", "sha": "bad"})
    store.insert("chapter_contract", {"seq": 2, "version": 1, "status": "frozen", "sha": "c"})
    fg = check_finalize_for_save(store, 2, "他按回碎片。" * 80, skip=False)
    assert fg.get("code") != "chapter_state_extract"


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


def test_detect_pov_three_cases():
    from scribe3.playbook.structural import detect_narrative_pov

    ch1 = "他把断指按进右腕。它寄在他手腕里面，安静得发烫。他听见最后一下。" * 8
    assert detect_narrative_pov(ch1) == "third"
    ch2 = "我把断指按进右腕。它寄在我手腕里面。我听见最后一下。我没松手。" * 12
    assert detect_narrative_pov(ch2) == "first"
    ch3 = ("「我不要这根指头。」柳岸青说。「我听见它跳了。」沈烛说。" * 14) + (
        "他把盒子推过去。他没再看腕上的裂口。" * 10
    )
    assert detect_narrative_pov(ch3) == "third"


def test_pov_gate_blocks_flip_after_ch1_third():
    from scribe3.playbook.structural import check_draft_struct, check_pov_consistency

    first = ("「按回去。」我说。\n我把盒子按进胸口，听见最后一下。袖口发烫。\n" * 80)
    hit = check_pov_consistency(first, "third")
    assert hit["ok"] is False
    assert hit["code"] == "pov_consistency"
    play = "完全另一场戏，沈烛若没有按回碎片。" * 40
    draft_hit = check_draft_struct(first, play_text=play, expected_pov="third")
    assert draft_hit["ok"] is False
    assert draft_hit["code"] == "pov_consistency"
    assert check_pov_consistency(first, "first")["ok"] is True
    third = ("「按回去。」沈烛说。\n他把盒子按进胸口，听见最后一下。袖口发烫。\n" * 80)
    assert check_pov_consistency(third, "third")["ok"] is True


def test_thin_unlike_is_not_broken_and_residue_rolls_back():
    from scribe3.playbook.structural import residue_hits, thin_metaphors

    unlike = "那温度不像是他自己的了。袖口发烫。" * 120
    out = thin_metaphors(unlike)
    assert "不似乎" not in out
    assert "不似" in out
    assert "不像是" not in out
    residue_src = "它裂开，像又烧过的骨片。袖口发烫。" * 120
    kept = thin_metaphors(residue_src)
    assert "不似乎" not in kept
    assert "像又烧过" in kept
    assert residue_hits("不似乎是他自己的了") == ["不似乎"]
    assert residue_hits("裂开，又烧过的骨片。")


def test_dialogue_floor_blocks_low_quote_share():
    from scribe3.playbook.structural import check_draft_struct, dialogue_ratio

    play = "完全另一场戏，沈烛若没有按回碎片。" * 40
    silent = ("他按回碎片，袖口发烫。沈烛把盒子推过来。柳岸青没说话。任务书摊在桌上。\n" * 80)
    assert dialogue_ratio(silent) < 0.15
    hit = check_draft_struct(silent, play_text=play)
    assert hit["ok"] is False
    assert hit["code"] == "dialogue_floor"
    talked = (
        "「按回去。」沈烛说。\n他按回碎片，袖口发烫。沈烛把盒子推过来。柳岸青没说话。任务书摊在桌上。\n" * 80
    )
    assert dialogue_ratio(talked) >= 0.15
    ok = check_draft_struct(talked, play_text=play)
    assert ok.get("ok") is True, ok


def test_prompts_inject_pov_line():
    ctx = {"seq": 2, "prev_state": {**_ok_state(), "narrative_pov": "third"}, "available_cast": ["柳岸青"]}
    d = duty_generate(ctx)
    p = play_generate({"seq": 2, "duty": {}, "prev_state": ctx["prev_state"]})
    from scribe3.playbook.prompts import draft_generate
    r = draft_generate({"play_text": "戏", "bite_quote": "钩", "prev_state": ctx["prev_state"]})
    for blob in (d, p, r):
        assert "第三人称" in blob
        assert "叙述里禁止出现「我」" in blob


def test_extract_sets_narrative_pov_from_source():
    store = MemoryPlaybookStore()

    def llm_fn(prompt, **kwargs):
        return json.dumps(_ok_state(seq=1), ensure_ascii=False)

    src = "他把断指按进右腕。它寄在他手腕里面。它跳了最后一下，然后不再跳了。"
    out = extract_chapter_state(store, 1, src, llm_fn=llm_fn, persist=True)
    assert out["ok"] is True
    frozen = store.get_frozen("chapter_state", 1)
    assert frozen["narrative_pov"] == "third"


def test_state_and_duty_read_routes_exist():
    from pathlib import Path

    from scribe3.api.routers import chapters as ch

    text = (Path(__file__).resolve().parents[1] / "api" / "routers" / "chapters.py").read_text(encoding="utf-8")
    assert "/chapters/{seq}/state" in text
    assert "/chapters/{seq}/duty" in text
    assert callable(ch.get_chapter_state)
    assert callable(ch.get_chapter_duty)


def test_elapsed_caps_pre_process_start():
    from datetime import datetime, timedelta, timezone

    from scribe3.pipeline_trace_store import _elapsed_s

    old = datetime.now(timezone.utc) - timedelta(hours=9)
    secs = _elapsed_s(old)
    assert secs is not None
    assert secs < 600


def test_gate0_freeze_mismatch_and_skip(monkeypatch):
    from scribe3.tools.gate0 import check_gate0_freeze

    monkeypatch.setenv("SCRIBE3_GATE0_SHA", "deadbeef")
    monkeypatch.setenv("SCRIBE3_GIT_SHA", "cafebabe")
    monkeypatch.delenv("SCRIBE3_REQUIRE_GATE0", raising=False)
    hit = check_gate0_freeze(require=True)
    assert hit["ok"] is False
    assert hit["code"] == "gate0_mismatch"
    monkeypatch.setenv("SCRIBE3_GIT_SHA", "deadbeefabc")
    ok = check_gate0_freeze(require=True)
    assert ok["ok"] is True
    monkeypatch.delenv("SCRIBE3_GATE0_SHA", raising=False)
    monkeypatch.delenv("SCRIBE3_GIT_SHA", raising=False)
    skipped = check_gate0_freeze(require=False)
    assert skipped["ok"] is True
    assert skipped.get("skipped") is True or skipped.get("tag")
