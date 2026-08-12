"""话语层 Week-1（方案 E）：驱动 shipped 纯函数 / soft 聚合 / dedup / loop 分桶。"""
from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_tip_ssot_lookups():
    from scribe3.discourse_craft_ssot import tip_for, tip_text, product_label, TIPS

    assert "telling" in TIPS
    assert tip_text("telling")
    assert product_label("god_view") == "越界全知"
    assert tip_for("hook_on_page")["tip"]


def test_aggregate_breath_rhythm_only_uniform_not_ok():
    """诚实路径：高 CV / verdict=ok 的句长变化正文不得出 rhythm tip，也不得仅因 rhythm 假 tight。

    驱动 shipped ``aggregate_breath`` → 内部 ``find_rhythm_uniformity``，不重实现。
    """
    from scribe3.critique import find_rhythm_uniformity
    from scribe3.discourse_detectors import aggregate_breath

    # 长短交错：应判 ok 而非 uniform（需足够句数）
    varied = "".join(
        [
            "他走了。",
            "门外的雨越下越大，巷子深处有人提着灯笼，脚步声一下一下敲在青石板上。",
            "灯灭了。",
            "她忽然想起三年前的那封信，于是停住，又往前走，又停住。",
            "风停。",
            "铜炉里的灰还热着，像有人刚走不久，却又什么都没留下。",
            "谁？",
            "没有人回答，只有雨声把夜色一层层洗薄。",
            "他抬手推门。",
            "门开了，里面空无一人，桌上却摆着那枚她丢失多年的铜钱。",
            "停。",
            "她的呼吸乱了半拍，随即又平复下来，仿佛什么都没发生过。",
            "远方有狗吠。",
            "狗吠停了之后，世界重新安静得过分，连雨丝都像被按了静音。",
            "她把铜钱握紧。",
            "然后松开，放回桌上，退后一步，再退后一步，直到门槛外的冷风灌进领口。",
            "走。",
            "她没有回头，雨打在伞上，像无数细小的催促。",
            "巷口有人影一闪。",
            "那人影却再也不出现，只留下她一个人站在灯下，听着自己的心跳。",
            "心跳慢下来。",
            "她终于明白：有些事不是来得太快，而是来得太安静。",
        ]
    )
    rhythm = find_rhythm_uniformity(varied)
    assert rhythm is not None, "need n_sentences enough for verdict"
    assert rhythm.get("verdict") == "ok", rhythm
    assert rhythm.get("n_sentences", 0) >= 20, rhythm

    # 无情绪贴标输入，避免 telling 干扰 tight
    breath = aggregate_breath(varied, emotion_hits=[], god_view_count=0)
    families = {t.get("family") for t in (breath.get("tips") or [])}
    assert "rhythm" not in families, breath
    assert breath.get("tight") is not True, breath

    # 显式传入 verdict=ok 元数据同样不报
    breath2 = aggregate_breath(
        "短。",
        emotion_hits=[],
        rhythm={"verdict": "ok", "cv": 0.5, "n_sentences": 25},
        god_view_count=0,
    )
    assert "rhythm" not in {t.get("family") for t in (breath2.get("tips") or [])}

    # uniform 才报
    breath3 = aggregate_breath(
        "短。",
        emotion_hits=[],
        rhythm={"verdict": "uniform", "cv": 0.05, "n_sentences": 30},
        god_view_count=0,
    )
    assert "rhythm" in {t.get("family") for t in (breath3.get("tips") or [])}


def test_hook_plan_and_hook_on_page():
    from scribe3.discourse_detectors import detect_hook_plan, detect_hook_on_page

    empty = detect_hook_plan({"beats": [], "synopsis": "短"})
    assert empty["emit"] is True
    assert empty["hook_text"] == ""

    planned = detect_hook_plan({
        "beats_meta": {"chapter_hook": "他推门时刀已出鞘"},
        "beats": [],
    })
    assert planned["emit"] is False
    assert "刀" in planned["hook_text"]

    prose = "前文铺垫。" + ("闲笔。" * 40) + "他推门时刀已出鞘，冷光一闪。"
    hop = detect_hook_on_page(prose, "他推门时刀已出鞘")
    assert hop["status"] == "ok"
    assert hop.get("hook_on_page_ok") is True
    assert hop["emit"] is False

    weak = detect_hook_on_page("全文只谈天气与茶。" * 30, "他推门时刀已出鞘")
    assert weak["status"] == "ok"
    assert weak.get("hook_on_page_ok") is False
    assert weak["emit"] is True


def test_info_delta_thresholds():
    from scribe3.discourse_detectors import detect_info_delta

    skip = detect_info_delta("短", ["近章梗概也有内容"])
    assert skip["status"] == "skip"

    focus = (
        "柳怀玉赴义庄验尸，发现铜钱异样，推断有人先到，并记下现场布局与疑点清单。"
        "义庄后室有异响，铜炉余温未散。"
    )
    near = ["柳怀玉接到报案，准备出门去见捕快。" * 3]
    # focus has new bigrams vs near
    r = detect_info_delta(focus, near)
    assert r["status"] == "ok", r
    assert "score" in r
    # very similar → low score emit
    same = "甲乙丙丁戊己庚辛壬癸" * 5  # 50 CJK chars
    r2 = detect_info_delta(same, [same])
    assert r2["status"] == "ok", r2
    assert r2["emit"] is True or (r2.get("score") is not None and r2["score"] < 0.08)
    # new events suppress
    r3 = detect_info_delta(
        same, [same],
        focus_event_ids={"e1"},
        near_event_ids=set(),
    )
    assert r3["emit"] is False
    assert r3.get("reason") == "new_events"


def test_run_soft_no_prose_and_ok():
    from scribe3.discourse_advisory import run_discourse_advisory

    no = run_discourse_advisory(
        None,
        {"seq": 1, "synopsis": "柳怀玉赴义庄验尸发现铜钱异样推断先有人到。", "beats": []},
        near_chapters=[{"synopsis": "昨日无事。"}],
        mode="soft",
    )
    assert no["status"] == "no_prose"
    assert no["severity"] in ("advisory", "warning")
    assert no.get("not_a_kpi") is True
    # may have hook_plan / info_delta findings
    for f in no.get("findings") or []:
        assert str(f.get("type") or "").startswith("discourse.")

    prose = "他感到愤怒。" + ("句子很长。" * 20) + "门外有人。"
    ok = run_discourse_advisory(
        prose,
        {
            "seq": 2,
            "synopsis": "柳怀玉赴义庄验尸发现铜钱异样推断先有人到。",
            "beats_meta": {"chapter_hook": "门外有人"},
        },
        near_chapters=[{"synopsis": "昨日无事只有喝茶。"}],
        mode="soft",
    )
    assert ok["status"] == "ok"
    assert "breath" in ok
    assert "serial" in ok
    assert isinstance(ok.get("findings"), list)


def test_post_check_annotate_no_discourse_issues_and_no_telling_growth():
    from scribe3.discourse_advisory import run_discourse_advisory

    et = [{"text": "感到愤怒", "level": "L1"}]
    issues = [
        {"type": "god_view", "message": "全知", "text": "他怎会知道"},
        {"type": "rhythm", "message": "匀", "text": "……"},
    ]
    post = {
        "emotion_telling": list(et),
        "issues": list(issues),
        "structure_style": {"ending_formula_hit": True, "ending_formula": {"line": "风起了"}},
    }
    n_et = len(post["emotion_telling"])
    n_god = sum(1 for i in post["issues"] if i.get("type") == "god_view")
    n_rhythm = sum(1 for i in post["issues"] if i.get("type") == "rhythm")

    adv = run_discourse_advisory(
        "他感到愤怒。" * 10 + "风起了。",
        {"synopsis": "代价：命。柳怀玉验尸。", "beats": []},
        mode="post_check_annotate",
        existing_post=post,
    )
    assert adv["status"] == "ok"
    # emotion_telling length unchanged
    assert len(post["emotion_telling"]) == n_et
    assert post["emotion_telling"][0].get("product_label")
    assert post["emotion_telling"][0].get("discourse_tip")
    # no new god_view/rhythm rows
    assert sum(1 for i in post["issues"] if i.get("type") == "god_view") == n_god
    assert sum(1 for i in post["issues"] if i.get("type") == "rhythm") == n_rhythm
    assert post["issues"][0].get("product_label") == "越界全知"
    # pure findings only discourse.*
    for f in adv.get("findings") or []:
        assert str(f.get("type") or "").startswith("discourse.")
    # no discourse.* leaked into issues
    assert not any(str(i.get("type") or "").startswith("discourse.") for i in post["issues"])


def test_loop_triage_discourse_to_story():
    from scribe3.loop import _triage_bucket_for, triage

    assert _triage_bucket_for({"type": "discourse.hook_plan"}, is_block=False) == "story"
    assert _triage_bucket_for({"type": "discourse.info_delta"}, is_block=False) == "story"

    post = {
        "issues": [],
        "leaks": [],
        "discourse_advisory": {
            "findings": [
                {
                    "type": "discourse.hook_plan",
                    "severity": "advisory",
                    "message": "缺钩",
                }
            ]
        },
    }
    out = triage(post)
    story_types = [x.get("type") for x in (out.get("buckets") or {}).get("story") or []]
    assert "discourse.hook_plan" in story_types
    # not blocking
    assert out.get("verdict") in ("pass", "advisory")
    assert not any(
        str(b.get("type") or "").startswith("discourse.")
        for b in (out.get("blocking") or [])
    )


def test_flags_registered():
    from scribe3.feature_flags import FLAG_REGISTRY, get_flag

    names = {f.name for f in FLAG_REGISTRY}
    for k in (
        "SCRIBE3_DISCOURSE_ADVISORY",
        "SCRIBE3_DISCOURSE_MESO",
        "SCRIBE3_DISCOURSE_SERIAL",
        "SCRIBE3_DISCOURSE_INFO_DELTA",
        "SCRIBE3_DISCOURSE_STAKES",
        "SCRIBE3_DISCOURSE_BLOCKING",
        "SCRIBE3_DISCOURSE_RASHOMON",
    ):
        assert k in names, k
    assert get_flag("SCRIBE3_DISCOURSE_BLOCKING") in ("0", "false", "off", "")


def test_blocking_flag_not_finalize_contract():
    """DISCOURSE_BLOCKING 不改变 is_blocking_issue。"""
    from scribe3.review.blocking import is_blocking_issue

    iss = {
        "type": "discourse.hook_plan",
        "severity": "blocking",
        "meta": {"severity": "blocking"},
    }
    # even with blocking-looking fields, discourse types should not hard-block
    # if is_blocking_issue doesn't special-case discourse, severity alone might block —
    # design says is_blocking_issue must NOT read DISCOURSE_BLOCKING; discourse should
    # never be in issues[]. Verify pure finding is not treated as S1/leak.
    assert is_blocking_issue(iss) is False or not str(iss.get("type")).startswith("discourse.")
    # safer: empty meta advisory
    assert is_blocking_issue({
        "type": "discourse.info_delta",
        "severity": "advisory",
    }) is False


def test_no_discourse_soft_in_l0_structure_diversity():
    """Week-1 禁止 discourse 进 L0 structure_diversity / registry discourse_soft。"""
    from scribe3.injection_registry import SEGMENT_REGISTRY
    from scribe3.context_budget import L0_NEVER_CUT, generation_physical_order_names

    names = {s.name for s in SEGMENT_REGISTRY}
    assert "discourse_soft" not in names  # Week-1 gate
    assert "discourse_soft" not in generation_physical_order_names()
    # structure_diversity remains L0
    assert "structure_diversity" in L0_NEVER_CUT or any(
        s.name == "structure_diversity" and s.tier == "L0" for s in SEGMENT_REGISTRY
    )


if __name__ == "__main__":
    test_tip_ssot_lookups()
    test_hook_plan_and_hook_on_page()
    test_info_delta_thresholds()
    test_run_soft_no_prose_and_ok()
    test_post_check_annotate_no_discourse_issues_and_no_telling_growth()
    test_loop_triage_discourse_to_story()
    test_flags_registered()
    test_blocking_flag_not_finalize_contract()
    test_no_discourse_soft_in_l0_structure_diversity()
    print("ALL_DISCOURSE_WEEK1_OK")
