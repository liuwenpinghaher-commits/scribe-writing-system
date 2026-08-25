"""playbook.3.2：叙述装腔拦、节奏记账、定稿法官两问。不烧模型。"""
from __future__ import annotations

from scribe3.playbook.diagnose import craft_diagnostic, sentence_rhythm, style_judge_fields
from scribe3.playbook.judge import VERSIONED_RUBRICS
from scribe3.playbook.prompts import draft_generate, final_generate, final_judge, play_generate
from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.playbook.structural import check_draft_struct, check_final_last_mile, check_syntax_tics, list_syntax_tics


def _draft(extra: str) -> str:
    pad = "「按回去。」他说。\n他按住盒子，袖口发烫。沈烛把任务书推过来。\n"
    return extra + pad * 80


PLAY = "完全另一场戏，没有盒子也没有袖口。" * 40


def test_version_is_32():
    assert PLAYBOOK_VERSION == "playbook.3.2.14"
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
    assert "playbook.3.1" in VERSIONED_RUBRICS


def test_two_narration_flips_block():
    text = "这不是明火，是碳粉。袖口发烫。那不是灯火是磷光。他站着。"
    hit = check_syntax_tics(text)
    assert hit["ok"] is False
    assert hit["code"] == "syntax_tics"
    assert "装腔" in hit["message"]
    assert "拆掉" not in hit["message"]
    draft = check_draft_struct(_draft(text), play_text=PLAY)
    assert draft.get("code") != "syntax_tics"
    assert draft.get("ok") is True
    final = check_final_last_mile(("他按回碎片，袖口发烫。" * 120) + text)
    assert final["ok"] is False
    assert final["code"] == "syntax_tics"


def test_dialogue_flips_do_not_count():
    text = "「这不是明火，是碳粉。」他说。\n「那不是灯火是磷光。」柳岸青说。\n他按住盒子。"
    assert check_syntax_tics(text)["ok"] is True
    assert list_syntax_tics(text) == []


def test_one_flip_is_advisory_not_block():
    text = "这不是明火，是碳粉。袖口发烫。他按住盒子。"
    assert check_syntax_tics(text)["ok"] is True
    hits = list_syntax_tics(text)
    assert len(hits) == 1
    fields = style_judge_fields(text)
    assert "不是明火" in fields["syntax_tics_block"]


def test_toxic_two_hits_block():
    text = "声音不大，却把夜压住了。眼中闪过一丝冷意。他推门。"
    hit = check_syntax_tics(text)
    assert hit["ok"] is False
    assert hit["code"] == "syntax_tics"


def test_sentence_rhythm_three_numbers():
    # 四连短句 + 一句长句
    text = "他走了。门响。灯灭了。夜还在。然后他在走廊里把盒子按回胸口，听见最后一下跳完。"
    r = sentence_rhythm(text)
    assert r["sentences"] >= 5
    assert 0 <= r["short_ratio"] <= 1
    assert 0 <= r["long_ratio"] <= 1
    assert r["short_bursts"] >= 1
    report = craft_diagnostic(text)
    assert report["blocking"] is False
    assert report["sentence_rhythm"]["short_bursts"] >= 1


def test_draft_hint_combines_len_and_copy():
    from scribe3.playbook.pipeline import COMBINED_LEN_COPY, draft_struct_hint
    h = draft_struct_hint(["draft_len"], last_message="排演字数 1800 低于 2000")
    assert "1800" in h
    h2 = draft_struct_hint(["draft_len", "draft_copy_play"], last_message="糙稿与戏重复率 21%")
    assert COMBINED_LEN_COPY == h2 or COMBINED_LEN_COPY in h2
    assert "还没演完" in h2
    assert "不能靠搬戏凑" in h2
    assert "写够两千字" not in h2
    h3 = draft_struct_hint(
        ["draft_len", "draft_copy_play"],
        last_message="x",
        tic_phrases=["不是慢慢冷，是抽", "不是往外走，是折回来"],
    )
    assert "还没演完" in h3
    assert "装腔" in h3
    assert "不是慢慢冷" in h3


def test_live_headline_shows_fail_reasons_while_running():
    from scribe3.pipeline_trace_store import live_headline
    h = live_headline({
        "status": "in_progress",
        "cursor_step_key": "playbook.struct",
        "notes": ["fail_reasons:draft_len", "fail_reasons:draft_len,draft_copy_play"],
    })
    assert "字数不够" in h
    assert "抄了戏" in h


def test_chapter_has_prose_missing_key_is_unknown():
    from scribe3.playbook.pipeline import _chapter_has_prose

    class Lite:
        def chapters_lite(self):
            return [{"seq": 1}]

    assert _chapter_has_prose(Lite(), 1, {}) is False
    assert _chapter_has_prose(Lite(), 1, {"has_prose": True}) is True

    class LiteTrue:
        def chapters_lite(self):
            return [{"seq": 1, "has_prose": True}]

    assert _chapter_has_prose(LiteTrue(), 1, {}) is True


def test_playbook_does_not_mount_voice_anchor():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "playbook/context.py").read_text(encoding="utf-8")
    assert "voice_anchor_block" not in src
    f = final_generate({})
    assert "【声纹】（无）" in f


def test_play_is_design_not_prose():
    p = play_generate({"seq": 1, "duty": {}})
    assert "800-2000" not in p
    assert "400-900" in p
    assert "留给糙稿" in p
    assert "设计图" in p


def test_prompts_drop_quota_verbs_and_keep_eight_questions():
    d = draft_generate({"play_text": "戏", "bite_quote": "钩"})
    assert "可听可触" not in d
    assert "摸到或听到" in d
    f = final_generate({})
    assert "补上画面的质感与声音" not in f
    assert "宁可糙着" in f
    j = final_judge({})
    assert "念出声" in j
    assert "在使劲" in j
    assert "把开头念出声" in j
    numbered = [ln for ln in j.splitlines() if ln[:2] in {f"{i}." for i in range(1, 12)}]
    assert any(ln.startswith("8.") for ln in numbered)
    assert not any(ln.startswith("9.") for ln in numbered)
    assert "syntax_tics_block" in j or "机器先检出的装腔原句" in j
