"""收件箱纯函数 + 旧库 unclear 无 question 风险闭环。"""
from __future__ import annotations

import pytest

from scribe3.inbox import (
    DEFAULT_UNCLEAR_QUESTION,
    dedupe_degraded,
    hermes_approval_inbox_item,
    idea_inbox_item,
    idea_unclear_question,
    needs_question_backfill,
    selection_inbox_item,
    sort_items,
)


def test_idea_unclear_question_priority():
    assert idea_unclear_question({"question": "你指哪一章?"}) == "你指哪一章?"
    assert idea_unclear_question({"note": "落到第几章？"}) == "落到第几章？"
    q = idea_unclear_question({"text": "那段感觉不对，节奏也怪怪的"})
    assert "那段感觉不对" in q and "具体" in q
    assert idea_unclear_question({}) == DEFAULT_UNCLEAR_QUESTION
    assert idea_unclear_question(None) == DEFAULT_UNCLEAR_QUESTION


def test_needs_question_backfill_only_unclear_missing_q():
    assert needs_question_backfill({"status": "unclear", "question": None}) is True
    assert needs_question_backfill({"status": "unclear", "question": "  "}) is True
    assert needs_question_backfill({"status": "unclear", "question": "有问句?"}) is False
    assert needs_question_backfill({"status": "pending_approval", "question": None}) is False


def test_idea_inbox_item_unclear_without_question_flag():
    it = idea_inbox_item({
        "id": "abc",
        "text": "老范那段不对劲",
        "route_kind": "unclear",
        "status": "unclear",
        "question": None,
        "note": "",
    })
    assert it["kind"] == "idea_unclear"
    assert it["id"] == "idea:abc"
    assert "想法待澄清" in it["message"]
    assert "老范" in it["message"]
    assert it.get("question_backfilled") is True
    assert it["resolve"] == {"kind": "idea_resolve", "payload": "abc"}
    assert it["action"]["kind"] == "chat"


def test_idea_inbox_item_setting_pending():
    it = idea_inbox_item({
        "id": "s1",
        "text": "老范其实识字",
        "route_kind": "setting",
        "status": "pending_approval",
        "note": "要改设定",
    })
    assert it["kind"] == "idea_setting"
    assert "动设定" in it["message"]
    assert "question_backfilled" not in it


def test_sort_items_focus_and_priority():
    items = [
        {"id": "d", "kind": "daily_digest", "message": "d"},
        {"id": "p", "kind": "pilot_outline", "seq": 2, "message": "p2"},
        {"id": "n", "kind": "needs_human", "seq": 9, "message": "n"},
        {"id": "p1", "kind": "pilot_outline", "seq": 1, "message": "p1"},
    ]
    sort_items(items, focus_seq=2)
    # 焦点章 pilot_outline 先于非焦点 needs_human? 实际: focus_boost 优先, 再 KIND_PRIORITY
    assert items[0]["id"] == "p"  # seq=2 焦点
    kinds_order = [i["kind"] for i in items]
    assert kinds_order.index("pilot_outline") < kinds_order.index("daily_digest")


def test_selection_inbox_item_waiting_and_done():
    assert selection_inbox_item("l1", 3, {"verdict": "picked"}) is None
    waiting = selection_inbox_item("l1", 3, {"verdict": "awaiting_pick", "variants": [{}, {}]})
    assert waiting["kind"] == "selection_l1"
    assert waiting["action"]["kind"] == "open_select"
    assert waiting["seq"] == 3
    l2 = selection_inbox_item("l2", 4, {"verdict": "awaiting_human", "candidates": [{}, {}]})
    assert l2["kind"] == "selection_l2"
    assert selection_inbox_item("l2", 4, {"verdict": "finalized"}) is None
    fail = selection_inbox_item("l1", 2, {"verdict": "all_failed"})
    assert fail["kind"] == "selection_failed"


def test_hermes_approval_inbox_item():
    assert hermes_approval_inbox_item({}) is None
    it = hermes_approval_inbox_item({"run_id": "r1", "message": "写入角色"})
    assert it["kind"] == "hermes_approval"
    assert it["action"]["kind"] == "open_chief"
    assert "写入角色" in it["message"]


def test_dedupe_degraded_preserves_order():
    assert dedupe_degraded(["ideas", "pilot", "ideas", "lessons"]) == ["ideas", "pilot", "lessons"]
    assert dedupe_degraded(None) == []


def test_inbox_legacy_unclear_message_and_lazy_backfill(store):
    """旧库 unclear 无 question：收件箱文案可展示，并懒回填 question。"""
    from .test_app import _client

    store._execute_write(
        "CREATE idea SET text=$t, route_kind='unclear', note=$n, status='unclear', "
        "question=NONE, created_at=time::now()",
        {"t": "那段节奏很怪", "n": ""},
    )
    # 确认落库时 question 为空
    rows = store._query(
        "SELECT meta::id(id) AS id, question, status FROM idea WHERE status='unclear'")
    assert rows and not (rows[0].get("question") or "").strip()
    rid = rows[0]["id"]

    r = _client(store).get("/inbox").json()
    unclear = [i for i in r["items"] if i["kind"] == "idea_unclear"]
    assert unclear, "unclear idea 必须进收件箱"
    assert "澄清" in unclear[0]["message"] or "具体" in unclear[0]["message"]
    assert "节奏" in unclear[0]["message"]

    # 懒回填
    after = store._query(
        "SELECT question FROM type::record('idea',$id)", {"id": rid})
    assert after and (after[0].get("question") or "").strip(), "GET /inbox 须懒回填 question"
