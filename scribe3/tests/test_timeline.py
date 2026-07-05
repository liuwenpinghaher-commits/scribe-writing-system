"""遗留处置批次三 · 时间线检测器第一刀 TDD(ConStory 对照结论:Timeline 大类
6 子类此前仅 2 窄点,时间维是长篇错误重灾区;处置方案批次三追加项)。

三件套,全部 report-only(advisory 通道,永不进 blocking——宪法:停机判据只挂
确定性项,时间语义歧义多,第一刀宁窄勿滥):
① 章内季节冲突:叙述层出现两个不同季节族词(剥引号;回忆句豁免)
② 章内时辰倒流:时辰序后退≥2档 且中间无跨日衔接词
③ 同章同主体双地:event 结构查询(story_time 是章粒度,双地可能有移动衔接,
  只出 low hint 请人工确认)
"""
from scribe3.critique import find_intra_chapter_time_conflicts
from scribe3.ontology import Entity, Event

from .test_app import _client


# ===== ① 季节冲突 =====

def test_season_conflict_reported():
    text = "盛夏的日头把石板晒得发烫。他走了半条街。屋檐下积着隆冬未化的残雪。"
    hits = find_intra_chapter_time_conflicts(text)
    ks = [h["kind"] for h in hits]
    assert "season_conflict" in ks
    h = next(x for x in hits if x["kind"] == "season_conflict")
    assert h["range"] and isinstance(h["range"], list)


def test_season_in_dialogue_or_memory_exempt():
    # 台词里报冬天:合法(角色谈论别的时节)
    t1 = "盛夏的日头毒。他说:「隆冬那会儿,河面能走人。」"
    assert not [h for h in find_intra_chapter_time_conflicts(t1)
                if h["kind"] == "season_conflict"]
    # 回忆句豁免:想起/去年 等标记
    t2 = "盛夏的日头毒。他想起去年隆冬,河面冻得能走人。"
    assert not [h for h in find_intra_chapter_time_conflicts(t2)
                if h["kind"] == "season_conflict"]


def test_same_season_family_not_conflict():
    text = "初夏的雨下了三天。入夏以来他没睡过一个整觉。盛夏将至。"
    assert not [h for h in find_intra_chapter_time_conflicts(text)
                if h["kind"] == "season_conflict"]


# ===== ② 时辰倒流 =====

def test_time_regression_reported():
    text = "黄昏时分他到了义庄。守了一阵。正午的日头照得院里发白,他数着影子。"
    hits = [h for h in find_intra_chapter_time_conflicts(text)
            if h["kind"] == "time_regression"]
    assert hits, "黄昏→正午 无跨日衔接 = 倒流"


def test_time_regression_with_day_break_exempt():
    text = "黄昏时分他到了义庄。次日正午,日头照得院里发白。"
    assert not [h for h in find_intra_chapter_time_conflicts(text)
                if h["kind"] == "time_regression"]


def test_adjacent_time_steps_not_reported():
    # 相邻档(傍晚→入夜)与顺行不报;差 1 档的边界模糊不报(宁窄勿滥)
    text = "傍晚他出门。入夜才回。深夜里犬吠了两声。"
    assert not [h for h in find_intra_chapter_time_conflicts(text)
                if h["kind"] == "time_regression"]


def test_time_in_dialogue_exempt():
    text = "入夜他到了义庄。老范说:「正午那阵儿,来过一拨人。」"
    assert not [h for h in find_intra_chapter_time_conflicts(text)
                if h["kind"] == "time_regression"]


# ===== ③ 同章同主体双地(结构查询) =====

def test_event_colocation_hint(store):
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    store.add_entity(Entity("place:乱岗", "place", "乱葬岗"))
    store.add_entity(Entity("place:县城", "place", "县城"))
    store.add_event(Event("ev:守夜", "守夜", participants={"SUBJ": "role:焦三"},
                          location="place:乱岗", story_time=3))
    store.add_event(Event("ev:赶集", "赶集", participants={"SUBJ": "role:焦三"},
                          location="place:县城", story_time=3))
    hints = store.validate_event_colocation(3)
    assert len(hints) == 1
    h = hints[0]
    assert h["type"] == "event_colocation" and h["severity"] == "low"
    assert set(h["locations"]) == {"place:乱岗", "place:县城"}
    assert "人工确认" in h["note"], "章粒度双地≠必错,note 必须说明"


def test_event_colocation_different_subjects_ok(store):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_event(Event("ev:a", "a", participants={"SUBJ": "role:甲"},
                          location="place:东", story_time=4))
    store.add_event(Event("ev:b", "b", participants={"SUBJ": "role:乙"},
                          location="place:西", story_time=4))
    assert store.validate_event_colocation(4) == []


# ===== 接线:post-check 出 timeline issue,triage 永不 blocking =====

def test_post_check_timeline_issue_advisory_only(store):
    from scribe3.loop import triage
    c = _client(store)
    r = c.post("/post-check?seq=1", json={
        "prose": "盛夏的日头把石板晒得发烫。屋檐下积着隆冬未化的残雪。"}).json()
    tl = [i for i in r["issues"] if i["type"] == "timeline"]
    assert tl and tl[0]["meta"]["kind"] == "season_conflict"
    t = triage(r)
    assert all(b.get("kind") != "season_conflict" for b in t["blocking"]), \
        "时间线第一刀 report-only,永不 blocking(宪法:歧义语义不挂停机)"
