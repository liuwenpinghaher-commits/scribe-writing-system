"""S7③ · LLM 语义判官(纪律闸)—— 确定性检测的盲区补丁(双高潮/声音崩/解说倾泻/知识泄露)。

complete_fn 可注入 → 解析+截断逻辑确定性可测,不连网。真机判官走 Hermes。
"""
from scribe3.critique import discipline_truncate, parse_discipline


def test_parse_clean():
    v = parse_discipline('{"ok": true, "violations": [], "cut_after": ""}')
    assert v["ok"] and v["violations"] == []


def test_parse_violation_with_noise():
    v = parse_discipline('好的 {"ok": false, "violations": ["double_climax"], "cut_after": "他松了口气。"} 完')
    assert not v["ok"] and "double_climax" in v["violations"] and v["cut_after"] == "他松了口气。"


def test_parse_malformed_fail_open():
    assert parse_discipline("完全不是JSON")["ok"], "解析失败不阻断(fail-open)"


def test_truncate_cuts_at_relapse():
    text = "前半正经的志怪内容。" * 20 + "他松了口气。" + "然后又是一场开挂大战。" * 4
    judge = lambda _p: '{"ok": false, "violations":["double_climax"], "cut_after":"他松了口气。"}'
    r = discipline_truncate(text, "", judge)
    assert r["changed"] and r["text"].endswith("他松了口气。")


def test_truncate_too_early_keeps():
    text = "他松了口气。" + "后面还有一大堆内容。" * 50
    judge = lambda _p: '{"ok": false, "violations":["voice_collapse"], "cut_after":"他松了口气。"}'
    r = discipline_truncate(text, "", judge)
    assert not r["changed"], "复发太早(截后<40%)→只标记不砍"
