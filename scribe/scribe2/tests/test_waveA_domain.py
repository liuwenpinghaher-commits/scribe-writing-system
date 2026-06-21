"""WaveA:核心写作数据形状——快照分支/字数/段落引用/状态/移动/反馈/作品库汇总。"""
import json

from scribe2.domain import Domain
from scribe2.store import Store


def _dom(db):
    d = Domain(Store(db)); d.s.init_schema()
    return d


def test_prose_branches_and_wordcount(db):
    d = _dom(db)
    w = d.create_work("书")
    cid = d.add_chapter(w, 1, "一")
    d.save_prose(w, cid, "渡叔立于船头,独眼望浊浪。")          # human-final
    d.create_branch(w, cid, "走向B", "另一种写法,他没上船。")   # 分支
    assert d.latest_prose(cid) == "渡叔立于船头,独眼望浊浪。"   # 只取 human-final
    labels = {b["label"] for b in d.list_branches(cid)}
    assert "human-final" in labels and "走向B" in labels
    # 字数落到章
    ch = d.get_chapter(w, 1)
    assert ch["word_count"] == 11 and len(ch["snapshots"]) == 2
    # 合并分支为定稿
    d.merge_branch(w, cid, "走向B")
    assert "他没上船" in d.latest_prose(cid)


def test_status_and_move(db):
    d = _dom(db)
    w = d.create_work("书")
    d.add_chapter(w, 1, "一"); d.add_chapter(w, 2, "二")
    d.set_chapter_status(w, 1, "done")
    assert d.get_chapter(w, 1)["status"] == "done"
    assert d.move_chapter(w, 1, "down")
    seqs = {c["title"]: c["seq"] for c in d.list_chapters(w)}
    assert seqs["一"] == 2 and seqs["二"] == 1


def test_segments_with_citations(db):
    d = _dom(db)
    w = d.create_work("书")
    d.add_character(w, "渡叔")
    d.add_setting(w, "九原渡", "古渡")
    cid = d.add_chapter(w, 1, "一")
    n = d.save_segments(w, cid, "渡叔立于九原渡的船头。\n\n浊浪拍岸,夜雾沉沉。")
    assert n == 2
    segs = d.list_segments(cid)
    refs0 = json.loads(segs[0]["citation_refs"])
    names = {r["name"] for r in refs0}
    assert "渡叔" in names and "九原渡" in names
    assert json.loads(segs[1]["citation_refs"]) == []


def test_feedback_and_work_summaries(db):
    d = _dom(db)
    w = d.create_work("书")
    cid = d.add_chapter(w, 1, "一")
    d.save_prose(w, cid, "一二三四五。")
    d.save_feedback(w, 1, "节奏太慢")
    summ = d.work_summaries("u1")
    s = next(x for x in summ if x["id"] == w)
    assert s["chapter_count"] == 1 and s["word_count"] == 5
    assert s["new_insight_count"] == 0 and s["pending_optionset_count"] == 0
