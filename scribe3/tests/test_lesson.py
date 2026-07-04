"""北极星方案任务8 · 章后复盘蒸馏 + lesson 反哺 TDD(蓝图 §4-② 第2-3级,沉淀环)。

品味复利:一章 ingest 后对本章主编对话只提取三类(决策理由/用户纠偏/坑),
产出结构化 lesson(原子条目+适用条件,AutoGuide 条件→规则式)挂章;
lesson 独立表+专属 HNSW 索引(D:Q4 裁决分表分索引);召回 k=3+相似度下限
(Power of Noise:相关但不适用比无关更毒,宁缺勿滥);反哺下一章 brief
"上章复盘要点"段;importance 计数(ExpeL:初始2/重复+1/归零退役)≥4 进
craft_rule 候选(升格必走既有 s3_craft_rule_add 待批——宪法:永不自动生效);
严禁复述世界状态(蒸馏 prompt 负例+kind 白名单);invalid_at 失效标记不物理删。
"""
import pytest

import scribe3.app as A
from scribe3.brief import assemble_chapter_brief
from scribe3.lesson import (build_distill_prompt, distill_chapter,
                            parse_distill)

from .test_app import _client

_DISTILL_OK = ('[{"kind":"correction","text":"用户把直说情绪改为物象暗示:寒意只写抖而不写怕",'
               '"condition":"写恐惧/紧张场景时"},'
               '{"kind":"decision","text":"反转揭示压到章尾最后一场,前文只留两处物象铺垫",'
               '"condition":"含反转的章"}]')


# ===== 蒸馏 prompt 与解析 =====

def test_build_distill_prompt_three_kinds_and_negative():
    msgs = [{"role": "user", "text": "开头别写雨了", "turn": "t1"},
            {"role": "assistant", "text": "好,改成灶上冷粥。", "turn": "t1"}]
    p = build_distill_prompt(msgs)
    assert "decision" in p and "correction" in p and "pitfall" in p
    assert "世界状态" in p and "返回空数组" in p, "负例 few-shot:剧情事实/人物状态→空(Mem0 先例)"
    assert "开头别写雨了" in p


def test_parse_distill_failsoft_and_kind_whitelist():
    assert parse_distill("垃圾不是json") == []
    out = parse_distill('[{"kind":"decision","text":"x"},{"kind":"世界状态","text":"戊丢了信物"}]')
    assert len(out) == 1 and out[0]["kind"] == "decision", "未知 kind 丢弃(世界状态越界防线之二)"


# ===== 蒸馏落库 + 软去重 =====

def test_distill_chapter_persists_lessons_with_embedding(store):
    store.add_chat_message(chapter=3, stage="", role="user", text="寒意别直说", turn="t1")
    store.add_chat_message(chapter=3, stage="", role="assistant", text="收到,只写抖。", turn="t1")
    r = distill_chapter(store, 3, lambda p, **kw: _DISTILL_OK)
    assert r["added"] == 2
    rows = store.list_lessons(chapter=3)
    assert len(rows) == 2
    assert all(r["importance"] == 2 for r in rows), "ExpeL 初始重要性 2"


def test_distill_soft_dedup_bumps_importance(store):
    store.add_chat_message(chapter=4, stage="", role="user", text="同一课", turn="t1")
    distill_chapter(store, 4, lambda p, **kw: _DISTILL_OK)
    r2 = distill_chapter(store, 4, lambda p, **kw: _DISTILL_OK)
    assert r2["merged"] == 2 and r2["added"] == 0, "近重蒸馏合并不新增(软去重)"
    rows = store.list_lessons()
    assert len(rows) == 2
    assert all(r["importance"] == 3 for r in rows), "合并→importance+1(跨章重复偏好积累)"


def test_distill_no_messages_noop(store):
    r = distill_chapter(store, 9, lambda p, **kw: _DISTILL_OK)
    assert r == {"added": 0, "merged": 0, "skipped": "no_messages"}


# ===== 召回(k+相似度下限,宁缺勿滥) =====

def test_recall_lessons_semantic_with_floor(store):
    store.add_lesson(3, "correction", "写恐惧场景只写身体反应不写心理词", condition="恐惧场景")
    store.add_lesson(3, "decision", "反转揭示压到章尾", condition="反转章")
    hits = store.recall_lessons("这一章有个吓人的夜戏,人物很害怕", k=3)
    assert hits and "恐惧" in hits[0]["text"]
    assert store.recall_lessons("完全无关的现代都市股票行情分析", k=3, min_sim=0.8) == [], \
        "低于相似度下限宁缺勿滥(Power of Noise)"


def test_recall_bumps_uses_counter(store):
    store.add_lesson(2, "pitfall", "更次不可倒退,四更之后只能五更", condition="夜戏")
    before = store.list_lessons()[0]["uses"]
    store.recall_lessons("夜里打更的戏", k=1)
    assert store.list_lessons()[0]["uses"] == before + 1, "质量闭环:注入次数落库"


# ===== brief 反哺 =====

def test_brief_injects_last_chapter_lessons(store):
    store.save_chapter(1, "第一章。", title="一")
    store.save_chapter(2, "第二章。", title="二")
    store.add_lesson(1, "correction", "开头压身体实感,不写天气抒情", condition="开章")
    out = assemble_chapter_brief(store, 2)
    assert "【上章复盘要点】" in out["text"]
    assert "开头压身体实感" in out["text"]


def test_brief_no_lessons_section_when_empty(store):
    store.save_chapter(2, "第二章。", title="二")
    out = assemble_chapter_brief(store, 2)
    assert "复盘要点" not in out["text"]


# ===== 升格候选(只列队列,升格走既有 craft_rule 待批) =====

def test_promotable_lessons_threshold(store):
    store.add_lesson(1, "correction", "情绪永远走物象", condition="")
    for _ in range(2):   # importance 2 → 4
        store.bump_lesson_importance(store.list_lessons()[0]["id"])
    c = _client(store)
    data = c.get("/lessons/promotable").json()
    assert len(data) == 1 and data[0]["importance"] >= 4
    assert "craft_rule" in data[0]["note"] and "待批" in data[0]["note"], \
        "升格永不自动生效:仅候选清单,动作走 s3_craft_rule_add 待批(宪法)"


# ===== 失效标记(不物理删) =====

def test_invalidate_lesson_excluded_from_recall(store):
    store.add_lesson(1, "decision", "夜戏收尾用实物动作压住", condition="")
    lid = store.list_lessons()[0]["id"]
    store.invalidate_lesson(lid)
    assert store.recall_lessons("夜戏怎么收尾", k=3) == []
    assert store.list_lessons(include_invalid=True), "失效标记保留溯源,不物理删(Zep 先例)"


# ===== ingest 挂接(事件驱动,不走 cron) =====

def test_ingest_endpoint_triggers_distill(store, monkeypatch):
    import scribe3.ingest as I
    monkeypatch.setattr(I, "ingest_chapter", lambda st, seq, llm: {})
    store.save_chapter(5, "第五章正文。", title="五")
    store.add_chat_message(chapter=5, stage="", role="user", text="这里别解释", turn="t1")
    c = _client(store)
    A.set_complete_fn(lambda p, **kw: _DISTILL_OK)
    r = c.post("/ingest?seq=5")
    assert r.status_code == 200
    assert store.list_lessons(chapter=5), "ingest 成功路径必须触发蒸馏(事件驱动)"


def test_ingest_distill_failure_does_not_break_ingest(store, monkeypatch):
    import scribe3.ingest as I
    monkeypatch.setattr(I, "ingest_chapter", lambda st, seq, llm: {})
    store.save_chapter(6, "第六章正文。", title="六")
    store.add_chat_message(chapter=6, stage="", role="user", text="x", turn="t1")
    c = _client(store)
    A.set_complete_fn(lambda p, **kw: (_ for _ in ()).throw(RuntimeError("llm down")))
    r = c.post("/ingest?seq=6")
    assert r.status_code == 200, "蒸馏挂了绝不拖垮 ingest(fail-soft)"
    assert store.list_lessons(chapter=6) == []
