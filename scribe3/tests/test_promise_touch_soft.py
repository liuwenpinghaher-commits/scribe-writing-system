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
