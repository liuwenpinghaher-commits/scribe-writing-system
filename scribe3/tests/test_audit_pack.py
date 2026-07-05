"""北极星方案任务13 · 盲评包导出 TDD(秘密审计制度的抽样工具)。

制度文档:设计文档/2026-07-05-秘密审计制度.md。原则:结论只供人读永不进 loop
(宪法级);池A=被自动 regenerate 章(journal *_verdict_blocking)附第0稿随机
左右并排(审「重写是否磨掉好东西」);池B=seed 可复现随机抽样;样本盲号不含章号。
"""
import json

import pytest

from .test_app import _client


@pytest.fixture()
def journal_dir(tmp_path, monkeypatch):
    d = tmp_path / "journals"
    monkeypatch.setenv("SCRIBE3_LOOP_JOURNAL_DIR", str(d))
    return d


def _fake_journal(journal_dir, work, seq, blocking=True):
    p = journal_dir / work
    p.mkdir(parents=True, exist_ok=True)
    stages = [f"ch{seq}_a0_generate", f"ch{seq}_a0_post_check",
              f"ch{seq}_a0_verdict_{'blocking' if blocking else 'pass'}"]
    (p / f"loop_ch{seq}_123456789.json").write_text(
        json.dumps({"in_progress": None, "stages_completed": stages}), encoding="utf-8")


def test_blind_pack_pools_and_key(store, journal_dir):
    store.save_chapter(1, "第一章正文,被回炉过的。", title="一")
    store.save_chapter(2, "第二章正文。", title="二")
    store.save_chapter(3, "第三章正文。", title="三")
    store.add_chapter_version(1, "第0稿原始文本。", label="loop第0稿", kind="checkpoint",
                              stage="draft")
    _fake_journal(journal_dir, "main", 1, blocking=True)
    c = _client(store)
    pack = c.get("/audit/blind-pack", params={"per_volume": 1, "seed": 7}).json()
    assert pack["samples"] and pack["key"]
    # 池A 样本:含双稿并排与对照问题,不含明文章号
    a_ids = [bid for bid, k in pack["key"].items() if k["pool"] == "A"]
    assert len(a_ids) == 1 and pack["key"][a_ids[0]]["chapter"] == 1
    sample_a = next(s for s in pack["samples"] if s["blind_id"] == a_ids[0])
    assert "pair" in sample_a and len(sample_a["pair"]) == 2
    texts = {p["prose"] for p in sample_a["pair"]}
    assert "第0稿原始文本。" in texts and "第一章正文,被回炉过的。" in texts
    assert "chapter" not in sample_a, "样本本体不得漏章号(盲评)"
    # 池B:1 章随机
    b_ids = [bid for bid, k in pack["key"].items() if k["pool"] == "B"]
    assert len(b_ids) == 1
    # 四问在
    assert len(pack["samples"][0]["questions"]) == 4
    assert "永不接入" in pack["note"], "宪法级声明必须随包"


def test_blind_pack_seed_reproducible(store, journal_dir):
    store.save_chapter(1, "一。", title="一")
    store.save_chapter(2, "二。", title="二")
    c = _client(store)
    p1 = c.get("/audit/blind-pack", params={"per_volume": 2, "seed": 42}).json()
    p2 = c.get("/audit/blind-pack", params={"per_volume": 2, "seed": 42}).json()
    assert [s["blind_id"] for s in p1["samples"]] == [s["blind_id"] for s in p2["samples"]]
    assert p1["key"] == p2["key"], "同 seed 抽样可复现(审计流程可追溯)"
