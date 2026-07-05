"""遗留处置批次二 TDD:校准回路与效率(处置方案 2-A/2-B/2-C/2-D + 真机发现)。

- 2-A 池A2:needs_human 章(三稿全拦)是检测器假阳性富矿,盲评包扩三稿并排观察。
- 2-B 短文本置信度:<500 可见字且 heavy 仅密度类证据 → 降 advisory+标注(P2 真机
  曾见 400 字三候选全灭;密度类分母小单发即爆表)。阈值 500 为自定口径,批次三标定。
- 2-C 增量蒸馏:marker 后新增对话才喂 LLM(教训天然增量,软去重兜重复)。
- 2-D 窄查询:书级面板一次拉草料字段,不拉 prose/embedding。
- violations 值域过滤:真机发现生产 LLM 混塞自由文本(D-024),须与五类标签求交。
"""
import json

import pytest

import scribe3.app as A
from scribe3.critique import parse_discipline
from scribe3.lesson import distill_chapter
from scribe3.loop import triage

from .test_app import _client


# ===== 2-B 短文本置信度(triage 纯函数) =====

def _post_heavy(visible_chars, gates_hit, non_density_heavy=False):
    """构造 ai_grade heavy 的 post-check 响应骨架。"""
    ind = {k: {"value": 9.9, "tier": "heavy"} for k in
           ("banned_density", "psych_ratio", "dialogue_tag_density", "repeat_density")}
    ind["parallel_run"] = {"value": 5 if non_density_heavy else 1,
                           "tier": "heavy" if non_density_heavy else "light"}
    ind["rhythm_uniform"] = {"value": "ok", "tier": "light"}
    return {"leaks": [], "issues": [], "degraded_stages": [], "leaks_degraded": False,
            "punct_suggestions": [], "visible_chars": visible_chars,
            "ai_grade": {"grade": "heavy", "gates_hit": gates_hit, "indicators": ind}}


def test_short_text_density_only_heavy_downgrades_to_advisory():
    """<500 可见字 + heavy 证据全是密度类(Gate A/C/E,无非密度指标 heavy)→
    降 advisory 并标注置信度警示(不误杀短章草稿)。"""
    t = triage(_post_heavy(400, gates_hit=["A", "C"]))
    assert t["verdict"] == "advisory", "短文本密度爆表≠真 AI 味重"
    assert not t["blocking"]
    assert any(i.get("type") == "short_text_low_confidence" for i in t["advisory_items"]), \
        "必须显式标注降档原因(自定口径 500 字)"


def test_short_text_with_non_density_evidence_stays_blocking():
    """短文本但 heavy 含非密度证据(Gate D 节奏/结构)→ 照常 blocking。"""
    t = triage(_post_heavy(400, gates_hit=["A", "D"]))
    assert t["verdict"] == "blocking"
    assert any(b["detector"] == "aggregate_ai_grade" for b in t["blocking"])


def test_long_text_density_heavy_stays_blocking():
    """≥500 可见字的密度 heavy 是真信号 → 照常 blocking(降档只救短文本)。"""
    t = triage(_post_heavy(1200, gates_hit=["A", "C"]))
    assert t["verdict"] == "blocking"


def test_short_text_indicator_path_non_density_heavy_stays_blocking():
    """短文本、无 Gate 命中、但 parallel_run(计数类)指标自身 heavy → 照常 blocking。"""
    t = triage(_post_heavy(300, gates_hit=[], non_density_heavy=True))
    assert t["verdict"] == "blocking"


def test_post_check_response_carries_visible_chars(store):
    """app 层:post-check 响应带 visible_chars(triage 降档判据的数据源)。"""
    c = _client(store)
    r = c.post("/post-check?seq=1", json={"prose": "他把伞收了,雨还没停。"}).json()
    assert isinstance(r.get("visible_chars"), int) and 0 < r["visible_chars"] < 20


# ===== violations 值域过滤(真机发现,D-024) =====

def test_parse_discipline_filters_free_text_violations():
    raw = json.dumps({"ok": False, "violations": [
        "god_view", "未处理开放项:「纸人去了哪里」", "double_climax", "随口点评"],
        "cut_after": ""}, ensure_ascii=False)
    d = parse_discipline(raw)
    assert d["violations"] == ["god_view", "double_climax"], "只留五类标签,保序"
    assert d["extra"] == ["未处理开放项:「纸人去了哪里」", "随口点评"], "自由文本进 extra 不丢"


# ===== 2-C 增量蒸馏 =====

_DISTILL_ONE = json.dumps([{"kind": "decision", "text": "条件A→做法B",
                            "condition": "", "evidence_turns": ["t9"]}], ensure_ascii=False)


def test_distill_incremental_feeds_only_new_messages(store):
    """有 marker 且消息只增 → 蒸馏 prompt 只含新增对话(长会话不再全量重喂)。"""
    store.add_chat_message(chapter=6, stage="", role="user", text="旧话题甲", turn="t1")
    store.add_chat_message(chapter=6, stage="", role="user", text="旧话题乙", turn="t2")
    distill_chapter(store, 6, lambda p, **kw: _DISTILL_ONE)
    store.add_chat_message(chapter=6, stage="", role="user", text="新纠偏丙", turn="t3")
    seen = {}
    def spy(p, **kw):
        seen["prompt"] = p
        return _DISTILL_ONE
    r = distill_chapter(store, 6, spy)
    assert r.get("skipped") is None
    assert "新纠偏丙" in seen["prompt"], "新增消息必须在"
    assert "旧话题甲" not in seen["prompt"] and "旧话题乙" not in seen["prompt"], \
        "已蒸馏过的旧消息不再重喂(增量语义)"


def test_distill_message_shrink_falls_back_to_full(store):
    """消息数回退(被删改)→ marker 切片失效,退回全量喂(宁可多蒸不静默丢)。"""
    store.add_chat_message(chapter=7, stage="", role="user", text="第一句", turn="t1")
    store.add_chat_message(chapter=7, stage="", role="user", text="第二句", turn="t2")
    store.add_chat_message(chapter=7, stage="", role="user", text="第三句", turn="t3")
    distill_chapter(store, 7, lambda p, **kw: _DISTILL_ONE)
    # 伪造 marker 大于现存消息数(模拟消息被清理后又加新的)
    store.set_distill_marker(7, 99, "tX")
    seen = {}
    def spy(p, **kw):
        seen["prompt"] = p
        return _DISTILL_ONE
    r = distill_chapter(store, 7, spy)
    assert r.get("skipped") is None
    assert "第一句" in seen["prompt"] and "第三句" in seen["prompt"], "回退全量"


# ===== 2-D 窄查询 =====

def test_chapters_lite_excludes_prose_and_embedding(store):
    store.save_chapter(1, "很长的正文…" * 50, title="一")
    store.save_chapter(2, "另一章正文。", title="二")
    rows = store.chapters_lite()
    assert [r["seq"] for r in rows] == [1, 2]
    for r in rows:
        assert "prose" not in r and "embedding" not in r, "窄查询不拉重字段"
        assert "synopsis" in r and "beats" in r and "scene_truth" in r and "deltas" in r


# ===== 2-A 盲评池A2(needs_human 三稿观察) =====

@pytest.fixture()
def journal_dir(tmp_path, monkeypatch):
    d = tmp_path / "journals"
    monkeypatch.setenv("SCRIBE3_LOOP_JOURNAL_DIR", str(d))
    return d


def _needs_human_journal(journal_dir, work, seq):
    p = journal_dir / work
    p.mkdir(parents=True, exist_ok=True)
    stages = []
    for a in (0, 1, 2):
        stages += [f"ch{seq}_a{a}_generate", f"ch{seq}_a{a}_post_check",
                   f"ch{seq}_a{a}_verdict_blocking"]
    stages.append(f"ch{seq}_needs_human")
    jp = p / f"loop_ch{seq}_987654321.json"
    jp.write_text(json.dumps({"in_progress": None, "stages_completed": stages}),
                  encoding="utf-8")
    # loop 端点 1-C#2 的旁文件(blocking 原因分布数据源)
    result = {"verdict": "needs_human", "rounds": [
        {"verdict": "blocking", "blocking": [{"detector": "find_leaks"}]},
        {"verdict": "blocking", "blocking": [{"detector": "aggregate_ai_grade"}]},
        {"verdict": "blocking", "blocking": [{"detector": "aggregate_ai_grade"}]}]}
    (p / (jp.name + ".result.json")).write_text(
        json.dumps(result, ensure_ascii=False), encoding="utf-8")


def test_blind_pack_pool_a2_three_drafts(store, journal_dir):
    """needs_human 章进池A2:三稿并排+「真的都不行吗」问题+key 记 blocking 分布;
    不混入池A(它没有『重写后过审』的对照语义),正文未落库也不出空 prose 样本。"""
    store.save_chapter(1, "正常章正文。", title="一")
    store.save_chapter(2, "另一正常章。", title="二")
    for a in (0, 1, 2):
        store.add_chapter_version(1, f"被拦第{a}稿正文。", label=f"loop第{a}稿·blocking",
                                  kind="checkpoint", stage="draft")
    _needs_human_journal(journal_dir, "main", 1)
    c = _client(store)
    pack = c.get("/audit/blind-pack", params={"sample_n": 1, "seed": 3}).json()
    a2_ids = [bid for bid, k in pack["key"].items() if k["pool"] == "A2"]
    assert len(a2_ids) == 1 and pack["key"][a2_ids[0]]["chapter"] == 1
    assert not [bid for bid, k in pack["key"].items() if k["pool"] == "A"], \
        "needs_human 章不得同时算池A"
    s = next(x for x in pack["samples"] if x["blind_id"] == a2_ids[0])
    assert "triple" in s and len(s["triple"]) == 3
    texts = [t["prose"] for t in s["triple"]]
    assert texts == [f"被拦第{a}稿正文。" for a in (0, 1, 2)], "按轮次序(演进即证据)"
    assert "都不行吗" in s.get("triple_question", "")
    assert "prose" not in s, "needs_human 正文未落库,样本不带空 prose"
    dist = pack["key"][a2_ids[0]].get("blocking_dist")
    assert dist == {"find_leaks": 1, "aggregate_ai_grade": 2}, "拦截原因分布(来自 .result.json)"


def test_blind_pack_pool_a2_takes_latest_run_only(store, journal_dir):
    """真机发现(loop-qa ch5 存 3 轮 loop 共 7 稿):A2 只取最新一组(needs_human 那次),
    组边界=新→旧扫描遇到重复 attempt 号。"""
    store.save_chapter(1, "正文。", title="一")
    for a in (0, 1):   # 旧一轮(先入库=更旧)
        store.add_chapter_version(1, f"旧轮第{a}稿。", label=f"loop第{a}稿·raw",
                                  kind="checkpoint", stage="draft")
    for a in (0, 1, 2):   # 最新一轮
        store.add_chapter_version(1, f"新轮第{a}稿。", label=f"loop第{a}稿·blocking",
                                  kind="checkpoint", stage="draft")
    _needs_human_journal(journal_dir, "main", 1)
    pack = _client(store).get("/audit/blind-pack", params={"sample_n": 0, "seed": 1}).json()
    a2 = next(bid for bid, k in pack["key"].items() if k["pool"] == "A2")
    s = next(x for x in pack["samples"] if x["blind_id"] == a2)
    assert [t["prose"] for t in s["triple"]] == ["新轮第0稿。", "新轮第1稿。", "新轮第2稿。"]
