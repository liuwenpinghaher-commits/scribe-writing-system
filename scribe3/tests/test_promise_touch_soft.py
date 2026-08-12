"""F7 open promise soft — 纯函数，无 Surreal。"""
from scribe3.promise_touch_soft import (
    open_promise_touch_advisories,
    prose_touches_promise,
)


def test_touch_when_keyword_in_prose():
    assert prose_touches_promise("铜匙齿边缺口硌着皮肉", "铜匙齿边缺口要回收") is True


def test_no_touch_when_unrelated():
    assert prose_touches_promise("天亮了，巷口空了。", "铜匙齿边缺口要回收") is False


def test_advisories_for_untouched_open():
    prose = "晨光落在灰狸背上。"
    promises = [
        {"id": "p1", "status": "open", "text": "铜匙齿边缺口要回收"},
        {"id": "p2", "status": "closed", "text": "已回收的线"},
    ]
    adv = open_promise_touch_advisories(prose, promises)
    assert len(adv) == 1
    assert adv[0]["blocking"] is False
    assert adv[0]["severity"] == "advisory"
    assert "铜匙" in adv[0]["message"]


def test_skip_mark_clears():
    adv = open_promise_touch_advisories(
        "无关键词",
        [{"status": "open", "text": "铜匙齿边缺口要回收"}],
        chapter_skip_mark=True,
    )
    assert adv == []


def test_touched_no_advisory():
    prose = "他摸了摸衣襟里的真匙，齿边缺口仍在。"
    adv = open_promise_touch_advisories(
        prose,
        [{"status": "open", "text": "铜匙齿边缺口要回收"}],
    )
    assert adv == []


def test_meta_span_does_not_count_as_touch():
    from scribe3.promise_touch_soft import prose_touches_promise_scene
    # 关键词只在验收清单句里
    prose = "伏笔触碰：齿边、铜匙、炉灰。信息差维持到章末。"
    ok, reason = prose_touches_promise_scene(prose, "铜匙齿边缺口要回收")
    assert ok is False
    # 场面真写
    ok2, reason2 = prose_touches_promise_scene(
        "他摸了摸衣襟里的真匙，齿边缺口硌着皮肉。",
        "铜匙齿边缺口要回收",
    )
    assert ok2 is True
    assert reason2 == "scene"


CH2_TAIL = """
信息差维持到章末：缺口露一线，用途不写明。伏笔触碰：齿边、铜匙、炉灰、温着、铜腥，一一落在读者可感的句子里，却不收口。
读者知道那是旧库钥匙；他知道；灰狸不知道——这道差，就是今夜的全部胜负。
伏笔仍 open：铜匙齿边缺口要回收——本章只 touch，不 close。
余烬主题在炉灰、温着、铜腥里轻轻回响。
"""


def test_ch2_tail_not_scene_touch():
    """齿边验收腔全文：清单词不得算场面 touch（criterion3）。"""
    from scribe3.promise_touch_soft import prose_touches_promise_scene
    ok, reason = prose_touches_promise_scene(CH2_TAIL, "铜匙齿边缺口要回收")
    assert ok is False, (ok, reason)


def test_ch2_tail_scene_cover_not_ok():
    """验收腔 + beats 关键词不得 scene_cover 假绿。"""
    from scribe3.reader_ready import scene_cover
    from scribe3.anti_meta_narration import scan_anti_meta
    hits = scan_anti_meta(CH2_TAIL).get("hits") or []
    sc = scene_cover(
        CH2_TAIL,
        [{"text": "齿边"}, {"text": "铜匙"}, {"text": "炉灰"}],
        hits,
    )
    assert sc.get("ok") is not True, sc
    assert (sc.get("valid") or 0) == 0 or sc.get("beat_ratio", 1) < 2 / 3
