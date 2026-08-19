"""余烬：正文尾巴 → end_hook；空钩不灌。禁止 Surreal。"""
from __future__ import annotations

from scribe3.narrative_drive import (
    extract_end_hook_from_prose,
    merge_end_hook,
    resolve_prev_end_hook,
)
from scribe3.experience.continue_rite import continue_block_text


def test_extract_prefers_last_sentences():
    prose = (
        "## 第三章\n\n前面很长的铺陈。"
        "灰狸翻了个身，含含糊糊地说了句梦话，像是侧门。"
        "那角纸硌在腰带底下。"
        "那行时辰他记下了，短横，平竖，亥正三刻。"
        "他坐着，听见风从烟囱里倒灌进来。"
    )
    hook = extract_end_hook_from_prose(prose)
    assert "亥正三刻" in hook
    assert "##" not in hook
    assert extract_end_hook_from_prose("") == ""


def test_merge_respects_lock():
    locked = {"locked": True, "end_hook": "作者自己写的钩"}
    out = merge_end_hook(locked, "新抽的尾巴")
    assert out["end_hook"] == "作者自己写的钩"
    open_ = merge_end_hook({"end_hook": "旧"}, "新抽的尾巴亥正三刻")
    assert "亥正三刻" in open_["end_hook"]


def test_resolve_falls_back_to_prose():
    ch = {"prose": "他记下亥正三刻。风从烟囱倒灌进来。", "narrative_drive": {}}
    assert "亥正三刻" in resolve_prev_end_hook(ch)
    ch2 = {"prose": "不该用这段", "narrative_drive": {"end_hook": "官方钩纸角"}}
    assert resolve_prev_end_hook(ch2) == "官方钩纸角"


def test_save_chapter_persists_end_hook():
    from pathlib import Path
    text = Path(__file__).resolve().parents[1].joinpath("store/chapters.py").read_text(
        encoding="utf-8"
    )
    assert "extract_end_hook_from_prose" in text
    assert "merge_end_hook" in text
    assert "update_chapter_meta" in text
    assert "end_hook" in text


def test_resolve_latest_draft_falls_back_to_chapter_field():
    from scribe3.draft_read import resolve_latest_draft
    assert resolve_latest_draft(None, {"seq": 1, "draft": ""}) == {}
    out = resolve_latest_draft(None, {"seq": 2, "draft": "排演全文在章字段。"})
    assert out["prose"].startswith("排演全文")
    assert out["source"] == "chapter.draft"
    ver = resolve_latest_draft({"prose": "版本表草稿", "stage": "draft"}, {"draft": "章字段"})
    assert ver["prose"] == "版本表草稿"
    frozen = resolve_latest_draft(
        None, {}, frozen_draft={"seq": 3, "text": "冻结排演场面。", "sha": "abc", "status": "frozen"},
    )
    assert frozen["prose"].startswith("冻结排演")
    assert frozen["source"] == "chapter_draft"


def test_continue_block_shows_prev_ember():
    txt = continue_block_text({
        "seq": 4, "focalizer": "", "prose_hash": "",
        "prev_end_hook": "那行时辰他记下了，亥正三刻。",
        "open_promises": [],
    })
    assert "上章余烬" in txt
    assert "亥正三刻" in txt


def test_continue_snapshot_uses_request_focalizer():
    from scribe3.experience.continue_rite import build_continue_snapshot

    class St:
        def get_chapter(self, seq):
            return {"seq": seq, "focalizer": "", "prose": ""}

        def get_character(self, oid):
            if "qin" in str(oid) or "huiqi" in str(oid):
                return {"name": "覃灰七"}
            return {}

    snap = build_continue_snapshot(St(), 4, focalizer="role:qin_huiqi")
    assert snap["focalizer"] == "覃灰七"
    txt = continue_block_text(snap)
    assert "覃灰七" in txt
    class Bare:
        def get_chapter(self, seq):
            return {"seq": seq, "prose": ""}
    snap2 = build_continue_snapshot(Bare(), 4, focalizer="role:qin_huiqi")
    assert snap2["focalizer"] == "覃灰七"
