"""经验压力层 E0–E5 TDD · 驱动真实 shipped 函数。"""
from __future__ import annotations

import pytest

from scribe3.experience import exp_state
from scribe3.experience.letter import (
    build_revision_letter,
    letter_has_total_score,
    update_letter_item_status,
)
from scribe3.experience.modes import normalize_revision_mode, revision_mode_priority
from scribe3.experience.scene_grid import (
    diagnose_scene_grid,
    evaluate_strict_scene_gate,
    normalize_scene_grid,
)
from scribe3.experience.choice_seed import (
    build_choice_audit,
    promote_seed_payload,
    suggest_seeds,
)
from scribe3.experience.continue_rite import (
    build_continue_snapshot,
    continue_block_text,
    reread_allowed,
)
from scribe3.experience.feedback_cut import parse_feedback_markdown, suggest_cut_candidates


@pytest.fixture(autouse=True)
def _clean_exp_state():
    exp_state.clear_all()
    yield
    exp_state.clear_all()


class MiniStore:
    """最小 store 面,驱动 letter/snapshot 真实聚合。"""

    def __init__(self):
        self.intent = {
            "reader_feeling": "沉重而暖",
            "emotional_arc": "从压抑到挣开",
            "red_lines": "不美化酷刑",
        }
        self.chapters = [
            {"seq": 1, "synopsis": "压力级:2\nchapter_role:推进", "beats": [],
             "scene_truth": "", "prose": "他把伞收了。" * 5, "focalizer": "role:沈砚",
             "title": "一"},
            {"seq": 2, "synopsis": "压力级:2\nchapter_role:推进", "beats": [],
             "scene_truth": "", "prose": "雨还在下。" * 5, "focalizer": "role:沈砚",
             "title": "二"},
            {"seq": 3, "synopsis": "压力级:2\nchapter_role:推进", "beats": [],
             "scene_truth": "", "prose": "灰契又在袖中。" * 5, "focalizer": "role:沈砚",
             "title": "三"},
            {"seq": 4, "synopsis": "压力级:5", "beats": [], "prose": "高潮。" * 10,
             "focalizer": "role:沈砚", "title": "四"},
        ]
        self.promises = [
            {"text": "灰契背面真名", "setup_chapter": 1, "status": "open",
             "window": {"state": "overdue"}},
            {"text": "白姑的旧债", "setup_chapter": 2, "status": "open",
             "window": {"state": "open"}},
        ]

    def get_intent(self):
        return dict(self.intent)

    def chapters_lite(self):
        return [dict(c) for c in self.chapters]

    def list_chapters(self):
        return self.chapters_lite()

    def get_chapter(self, seq):
        for c in self.chapters:
            if int(c["seq"]) == int(seq):
                return dict(c)
        return {}

    def promises_with_lifecycle(self, max_chapter=None):
        return list(self.promises)

    def open_promises(self):
        return list(self.promises)

    def list_characters(self):
        return [{"id": "role:沈砚", "name": "沈砚"}]


# ===== E0 modes + constitution =====

def test_revision_mode_normalize_and_priority():
    assert normalize_revision_mode("STRUCTURE") == "structure"
    assert normalize_revision_mode("nope") == "full"
    assert revision_mode_priority("scene")[0] == "scene_kinetics"
    assert "opening_promise" in revision_mode_priority("structure")


def test_letter_has_no_total_score_field():
    st = MiniStore()
    letter = build_revision_letter(st, work="test")
    assert not letter_has_total_score(letter)
    assert "total_score" not in letter
    assert "composite_score" not in letter
    # 伪造总分必须被检测
    bad = dict(letter, total_score=99)
    assert letter_has_total_score(bad)


# ===== E1 letter =====

def test_build_revision_letter_multi_kinds():
    st = MiniStore()
    letter = build_revision_letter(st, work="test", mode="full")
    kinds = {i["kind"] for i in letter["items"]}
    # 至少四类
    need = {"opening_promise", "middle_sag", "character_arc", "unpaid_promise"}
    assert need <= kinds, f"缺 kinds: {need - kinds}, 有 {kinds}"
    assert letter["item_count"] >= 4
    assert letter.get("note")


def test_letter_item_waived_keeps_audit():
    st = MiniStore()
    letter = build_revision_letter(st, work="t")
    iid = letter["items"][0]["id"]
    updated = update_letter_item_status(
        letter, iid, status="waived", author_note="本卷刻意不还")
    item = next(i for i in updated["items"] if i["id"] == iid)
    assert item["status"] == "waived"
    assert item["author_note"]
    assert item["history"]
    # 项仍在列表
    assert any(i["id"] == iid for i in updated["items"])


def test_letter_overlay_via_state():
    st = MiniStore()
    letter = build_revision_letter(st, work="w1")
    iid = letter["items"][0]["id"]
    exp_state.set_letter_item("w1", iid, status="acknowledged", author_note="seen")
    letter2 = build_revision_letter(
        st, work="w1", status_overlay=exp_state.get_letter_overlay("w1"))
    item = next(i for i in letter2["items"] if i["id"] == iid)
    assert item["status"] == "acknowledged"


# ===== E2 scene grid =====

def test_diagnose_disaster_without_reaction():
    g = normalize_scene_grid({
        "goal": "夺回灰契", "conflict": "守卫", "disaster": "被反杀",
        "reaction": "", "dilemma": "", "decision": "", "source": "author",
    })
    issues = diagnose_scene_grid(g, seq=3)
    codes = {i["code"] for i in issues}
    assert "disaster_without_reaction" in codes


def test_diagnose_clean_grid():
    g = normalize_scene_grid({
        "goal": "问清", "conflict": "对方沉默", "disaster": "只得到半句",
        "reaction": "心沉", "dilemma": "逼问还是退", "decision": "先退",
        "source": "author",
    })
    issues = diagnose_scene_grid(g)
    assert not any(i["code"] == "disaster_without_reaction" for i in issues)


def test_strict_scene_gate_default_off_allows_empty():
    d = evaluate_strict_scene_gate(None, strict=False, prose="实质正文" * 40)
    assert d["allowed"] is True


def test_strict_scene_gate_on_blocks_empty_substantial():
    d = evaluate_strict_scene_gate(
        None, strict=True, prose="实质正文内容很多字数要够才拦" * 10)
    assert d["allowed"] is False
    assert d["code"] == "strict_scene_empty"


def test_strict_scene_gate_on_allows_filled():
    g = {
        "goal": "a", "conflict": "b", "disaster": "c",
        "reaction": "d", "dilemma": "e", "decision": "f", "source": "author",
    }
    d = evaluate_strict_scene_gate(g, strict=True, prose="实质正文" * 40)
    assert d["allowed"] is True


# ===== E3 choice + seed =====

def test_choice_audit_template_no_score():
    audit = build_choice_audit(
        quote="他放下了刀。",
        character_id="role:沈砚",
        anchors={"name": "沈砚", "fear": "失明", "surface_goal": "护住灰契",
                 "lie": "我能独活"},
        recent_synopsis="前章他几乎动手",
    )
    assert "欲望" in audit["question"] or "恐惧" in audit["question"]
    assert audit["likeness_score"] is None
    assert audit["evidence"]
    assert any(e["field"] == "choice_quote" for e in audit["evidence"])


def test_seed_suggest_and_promote_not_auto_plant():
    prose = "灰契在袖中。他摸了摸灰契。旁人不知灰契。他问:「真名何在？」"
    seeds = suggest_seeds(prose, seq=2)
    assert seeds
    # 至少有重复标记
    assert any(s["kind"] == "repeated_marker" for s in seeds)
    seed = seeds[0]
    payload = promote_seed_payload(seed)
    assert payload["requires_approval"] is True
    assert payload["text"]
    # promote 不写 store——此处无 plant 副作用
    assert "seed_id" in payload


# ===== E4 continue =====

def test_continue_snapshot_from_store_fields():
    st = MiniStore()
    snap = build_continue_snapshot(st, 3, work="test")
    assert snap["source"] == "store_fields"
    assert snap["seq"] == 3
    assert snap["focalizer"] == "role:沈砚"
    assert snap["prose_hash"]
    assert snap["open_promises"] or snap["overdue_promises"]
    block = continue_block_text(snap)
    assert "续写状态快照" in block
    assert "灰契" in block or "承诺" in block


def test_reread_hard_mode_blocks_generate():
    assert reread_allowed(require_reread=False, acked=False)["allowed"]
    g = reread_allowed(require_reread=True, acked=False, is_generate=True)
    assert g["allowed"] is False
    assert reread_allowed(require_reread=True, acked=True)["allowed"]
    assert reread_allowed(require_reread=True, acked=False, is_generate=False)["allowed"]


def test_continue_inject_into_write_assemble_path(monkeypatch):
    """ack 后 continue_block 进入真实组装 helper 路径。"""
    from scribe3.api.services import write_assemble as WA
    st = MiniStore()
    exp_state.ack_reread("main", 3)
    exp_state.set_require_reread("main", False)
    snap = build_continue_snapshot(st, 3, work="main")
    text = continue_block_text(snap)
    assert "续写状态快照" in text
    # 生产路径:check_generate_reread_gate 在 require 关时放行
    g = WA.check_generate_reread_gate("main", 3)
    assert g["allowed"] is True
    exp_state.set_require_reread("main", True)
    exp_state.clear_reread_ack("main", 3)
    g2 = WA.check_generate_reread_gate("main", 3)
    assert g2["allowed"] is False
    exp_state.ack_reread("main", 3)
    assert WA.check_generate_reread_gate("main", 3)["allowed"] is True


# ===== E5 feedback + cut =====

def test_parse_feedback_markdown_three_notes():
    sample = """
## 第1章
- 开头慢,想跳过
## 第3章
我不懂沈砚为何收手
第5章: 结尾假得像在赶稿
"""
    items = parse_feedback_markdown(sample)
    assert len(items) >= 3
    seqs = {i.get("seq") for i in items}
    assert 1 in seqs and 3 in seqs and 5 in seqs


def test_cut_suggestions_no_auto_delete():
    prose = "他走了。他走了。他走了。这正是因为命运如此安排。"
    cands = suggest_cut_candidates(prose)
    assert cands
    assert all(c.get("auto_delete") is False for c in cands)


# ===== API handlers (real bind) =====

def test_api_revision_letter_and_waive(monkeypatch):
    import scribe3.app as A
    st = MiniStore()
    A.set_store(st, work="test")
    # monkeypatch _store_for on rebound handlers
    monkeypatch.setattr(A, "_store_for", lambda work="main": st, raising=False)
    exp_state.clear_work("test")
    letter = A.get_revision_letter(work="test")
    assert letter["item_count"] >= 4
    assert "total_score" not in letter
    kinds = {i["kind"] for i in letter["items"]}
    assert "opening_promise" in kinds
    assert "unpaid_promise" in kinds
    iid = letter["items"][0]["id"]
    from scribe3.api.routers.experience import LetterItemUpdate
    r = A.patch_revision_letter_item(
        iid, LetterItemUpdate(status="waived", author_note="ok"), work="test")
    assert r["ok"]
    item = next(i for i in r["letter"]["items"] if i["id"] == iid)
    assert item["status"] == "waived"


def test_api_strict_scene_and_seed_promote(monkeypatch):
    import scribe3.app as A
    st = MiniStore()
    monkeypatch.setattr(A, "_store_for", lambda work="main": st, raising=False)
    A.set_store(st, work="test")
    from scribe3.api.routers.experience import (
        StrictSceneReq, SeedSuggestReq, SeedPromoteReq, SceneGridReq,
    )
    A.set_strict_scene_ep(StrictSceneReq(enabled=True), work="test")
    assert exp_state.get_strict_scene("test") is True
    # empty grid + substantial prose → gate refuse
    from scribe3.experience.scene_grid import evaluate_strict_scene_gate
    long_prose = "实质正文必须足够长才会触发严格戏格空六格拦截。" * 6
    d = evaluate_strict_scene_gate(
        exp_state.get_scene_grid("test", 1),
        strict=True,
        prose=long_prose,
    )
    assert d["allowed"] is False
    # fill grid
    A.put_scene_grid_ep(1, SceneGridReq(
        goal="g", conflict="c", disaster="d",
        reaction="r", dilemma="m", decision="e", source="author",
    ), work="test")
    d2 = evaluate_strict_scene_gate(
        exp_state.get_scene_grid("test", 1), strict=True,
        prose=long_prose)
    assert d2["allowed"] is True
    # seeds
    r = A.seed_suggest_ep(SeedSuggestReq(seq=1, prose="灰契在袖。他摸灰契。旁人不知灰契。"), work="test")
    assert r["count"] >= 1
    sid = r["seeds"][0]["id"]
    pr = A.seed_promote_ep(SeedPromoteReq(seed_id=sid), work="test")
    assert pr["planted"] is False
    assert pr["requires_approval"] is True


def test_api_feedback_import(monkeypatch):
    import scribe3.app as A
    st = MiniStore()
    monkeypatch.setattr(A, "_store_for", lambda work="main": st, raising=False)
    from scribe3.api.routers.experience import FeedbackImportReq
    text = "## 第1章\n- a\n## 第2章\n- b\n第3章: c\n"
    r = A.feedback_import_ep(FeedbackImportReq(text=text), work="test")
    assert r["imported"] >= 3
    letter = A.get_revision_letter(work="test")
    assert any(i["kind"] == "external_read" for i in letter["items"])
