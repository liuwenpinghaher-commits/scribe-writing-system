"""Task 9 · 幂等捕获管线 + 经验记忆 + 活化缺口回填测试。

四层:
1) 计划原文两条失败测试(幂等捕获 / 正典事实不误存为经验)。
2) 活化翻转(灵魂):capture 回填 (entity,attribute)/linked_ids 后,Task 8 已就绪的
   正典压制与 focus 加权【对真机记忆生效】——unconflictable_count / unlinked_count 归零。
3) outbox 状态机:失败留痕(failed/attempts/error)+ runtime-status 可见。
4) working summary 蒸馏 + 与 lesson 系统严格分家。

铁律:绝不真调 embedding 服务,一律 monkeypatch scribe3.embed.embed(与 test_memory_retrieval 同款)。
"""
from __future__ import annotations

import math

import pytest

from scribe3.memory_capture import MemoryCapture, MemoryEvent, turn_event
from scribe3.memory_models import RetrievalQuery
from scribe3.memory_retrieval import MemoryRetriever
from scribe3.ontology import Entity, Fact


def _patch_embed(monkeypatch):
    """确定性假 embedding(按字符散列进 512 维),绝不加载真模型/服务。"""
    def fake(texts):
        out = []
        for t in texts:
            v = [0.0] * 512
            for ch in (t or ""):
                if ch.strip():
                    v[ord(ch) % 512] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out
    monkeypatch.setattr("scribe3.embed.embed", fake)


@pytest.fixture()
def capture(store, monkeypatch):
    _patch_embed(monkeypatch)
    return MemoryCapture(store)


# ---------- 计划原文两条核心失败测试 ----------

def test_turn_capture_is_idempotent(store, capture):
    event = turn_event(event_id="turn:42", text="我们决定删掉第二幕倒叙")
    capture.capture_event(event)
    capture.capture_event(event)
    assert store.count_memory_by_source("chat_turn", "turn:42") == 1


def test_canonical_fact_is_routed_to_domain_ingest_not_memory_item(store, capture):
    capture.capture_event(turn_event(text="甲的真实身份是王子", classification="canonical_claim"))
    assert store.list_memories(kind="episodic") == []
    claims = store.list_pending_authority_claims()
    assert claims and claims[0]["text"] == "甲的真实身份是王子"


# ---------- 灵魂:活化缺口回填 → Task 8 机制对真机记忆生效 ----------

def test_provenance_backfill_activates_canonical_suppression(store, capture):
    """捕获一条带 (entity,attribute) 的 episodic + 一条冲突 canonical(facts_at)。
    检索时该 episodic 被正典压制进 rejected(reason=conflicts_with_canonical),
    unconflictable_count 归零——证明 Task 8 的静默缺口被 Task 9 回填打通。"""
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:loc", "role:甲", "location", "城东", valid_from=1))
    # 与 canonical(甲/location/城东)直接矛盾的经验记忆,capture 回填 (entity,attribute)
    capture.capture_event(turn_event(
        text="甲还在城西盘桓未走", classification="episodic", work="w",
        entity="role:甲", attribute="location"))

    result = MemoryRetriever(store).retrieve_full(RetrievalQuery(
        work="w", snapshot={"work": "w", "chapter": 5, "focus": {"id": "role:甲"}},
        query="甲 城西", k=10))

    assert any(r.reason == "conflicts_with_canonical" for r in result.rejected), \
        "回填 (entity,attribute) 后,矛盾 episodic 必须被正典压制"
    assert not any(c.source_kind == "episodic" for c in result.selected), \
        "被压制的 episodic 不得再选入"
    assert result.unconflictable_count == 0, "活化缺口归零:不再有压制不了的 episodic"


def test_linked_ids_backfill_activates_focus_bonus(store, capture):
    """capture 回填 linked_ids 后,focus 加权对真机经验记忆生效,unlinked_count 归零。"""
    capture.capture_event(turn_event(
        text="甲在集市与旧友叙话", classification="episodic", work="w",
        linked_ids=["role:甲"]))
    result = MemoryRetriever(store).retrieve_full(RetrievalQuery(
        work="w", snapshot={"work": "w", "chapter": 5, "focus": {"id": "role:甲"}},
        query="集市 旧友", k=10))
    assert result.unlinked_count == 0, "回填 linked_ids 后不再有缺 linked_ids 的经验候选"
    exp = [c for c in result.selected if c.source_kind == "episodic"]
    assert exp and all(c.linked_ids for c in exp), "经验候选应带回填的 linked_ids"


# ---------- 限知红线:canonical 绝不进 memory_item;uncertainty 低信心 ----------

def test_canonical_claim_never_enters_memory_item(store, capture):
    """启发式识别正典揭示(真实身份)→ pending_authority_claim,memory_item 恒空。"""
    capture.capture_event(turn_event(text="其实那书生的真实身份是逃亡的太子", work="w"))
    assert store.list_memories(work="w") == [], "正典揭示绝不写进 memory_item"
    assert store.list_pending_authority_claims(work="w"), "应进正典待审队列"


def test_uncertainty_capped_confidence(store, capture):
    """“我猜/可能”→ uncertainty,confidence<=0.5(不作事实注入)。"""
    capture.capture_event(turn_event(text="我猜甲可能已经知道真相", work="w"))
    mems = store.list_memories(work="w", kind="uncertainty")
    assert mems, "应识别为 uncertainty"
    assert all(m["confidence"] <= 0.5 for m in mems), "uncertainty 信心必须 <=0.5"


def test_author_writing_preference_is_captured_as_procedural_constraint(store, capture):
    """作者明确的未来写法不是一条普通往事，必须进入可执行的工艺通道。

    这保证跨会话写作时，它会被编译为本次生成必须落实的约束，而非混在“近期事件”里
    供模型自行决定是否采用。
    """
    capture.capture_event(turn_event(
        text="作为作者，请记住这条后续写作偏好：潮票Alpha场景先写退潮借力，再让人物承担风险。",
        work="w",
    ))
    procedural = store.list_memories(work="w", kind="procedural")
    assert len(procedural) == 1
    assert "潮票Alpha" in procedural[0]["text"]


# ---------- outbox 状态机:失败留痕 + runtime-status 可见 ----------

def test_worker_failure_leaves_outbox_trace_and_does_not_raise(store, capture, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("embed down")
    monkeypatch.setattr(store, "add_memory_item", boom, raising=False)

    capture.capture_event(turn_event(event_id="turn:boom", text="我们决定删掉倒叙", work="w"))

    row = store.get_memory_event("turn:boom")
    assert row is not None and row["status"] == "failed"
    assert row["attempts"] >= 1
    assert "embed down" in (row.get("error") or "")
    assert store.count_failed_memory_events() >= 1, "失败事件应对 runtime-status 可见"


def test_enqueue_is_idempotent_at_outbox(store, capture):
    ev = turn_event(event_id="turn:99", text="现在正在修第8章结尾", work="w")
    assert store.enqueue_memory_event(ev.event_id, ev.work, ev.event_type, ev.payload,
                                      thread_id=ev.thread_id) is True
    assert store.enqueue_memory_event(ev.event_id, ev.work, ev.event_type, ev.payload,
                                      thread_id=ev.thread_id) is False, "同 event_id 二次入队应幂等"


# ---------- working summary 蒸馏 ----------

def test_consolidate_builds_working_summary(store, capture):
    tid = "ethread:w:consolidate"
    capture.capture_event(turn_event(text="我们现在正在修第8章结尾",
                                     classification="working", work="w", thread_id=tid))
    capture.capture_event(turn_event(text="这次已决定把第二幕倒叙删掉",
                                     classification="episodic", work="w", thread_id=tid))
    capture.capture_event(turn_event(text="我猜甲可能已经知道",
                                     classification="uncertainty", work="w", thread_id=tid))

    out = capture.consolidate_thread(tid, work="w")
    assert out["through_turn"] == 3

    ws = store.get_working_summary("w", tid)
    assert ws is not None
    assert any("倒叙" in d for d in ws["decisions"]), "决策应进 working summary"
    assert any("结尾" in t or "第8章" in t for t in ws["open_tasks"]), "在办目标应进 open_tasks"
    assert any("知道" in a for a in ws["assumptions"]), "不确定假设应进 assumptions"


def test_consolidate_is_idempotent(store, capture):
    tid = "ethread:w:idem"
    capture.capture_event(turn_event(event_id="turn:c1", text="现在正在铺垫第3章",
                                     classification="working", work="w", thread_id=tid))
    capture.consolidate_thread(tid, work="w")
    capture.consolidate_thread(tid, work="w")
    # working_summary thread 唯一,重复 consolidate 不产生第二条
    ws = store.get_working_summary("w", tid)
    assert ws is not None
    assert store.count_memory_by_source("chat_turn", "turn:c1") == 1


def test_flush_before_compress_delegates_to_consolidate(store, capture):
    tid = "ethread:w:flush"
    capture.capture_event(turn_event(text="已决定把开篇改成雨夜",
                                     classification="episodic", work="w", thread_id=tid))
    capture.flush_before_compress(tid, work="w")
    ws = store.get_working_summary("w", tid)
    assert ws is not None and any("雨夜" in d for d in ws["decisions"])


# ---------- 与 lesson 系统严格分家(Step 6)----------

def test_lesson_and_capture_stay_separate(store, capture):
    """add_lesson 落 lesson 表;capture 落 memory_item;两者互不吞并。"""
    store.add_lesson(chapter=8, kind="pitfall", text="刑讯先立寒气再落刀,冷硬白描不抒情")
    capture.capture_event(turn_event(text="以后少用全知解说", classification="procedural", work="w"))

    assert len(store.list_lessons(chapter=8)) == 1, "lesson 应留在 lesson 表"
    mems = store.list_memories(work="w")
    assert any("全知解说" in m["text"] for m in mems), "procedural 偏好应进 memory_item"
    assert not any("刑讯" in m["text"] for m in mems), "lesson 内容绝不得被吞进 memory_item"
    assert store.count_memory_by_source("lesson", "lesson:8") == 0, "capture 不搬运 lesson"


def test_memory_event_helper_shapes():
    ev = turn_event(text="随便一句", work="w")
    assert isinstance(ev, MemoryEvent)
    assert ev.event_type == "turn" and ev.event_id
    assert ev.payload["text"] == "随便一句"


# ---------- P0 限知宪法红线:身份/血缘/生死/秘密揭示强制进待审 ----------

def _register(store, *pairs):
    for cid, name in pairs:
        kind = "place" if cid.startswith("place:") else "character"
        store.add_entity(Entity(cid, kind, name))


def test_p0_canonical_reveals_routed_to_pending_not_memory_item(store, capture):
    """审查实证的 8 条身份/血缘/生死/背叛/情感揭示:命中登记实体 + 高风险稳定断言谓词
    → 强制 canonical_claim 待审,零进 memory_item(防揭示章前知情倒灌)。"""
    _register(store, ("role:甲", "甲"), ("role:乙", "乙"),
              ("role:丙", "丙"), ("role:皇帝", "皇帝"))
    reveals = [
        "其实凶手是甲", "凶手是甲", "甲的父亲是皇帝", "这个孩子是皇帝的私生子",
        "甲背叛了乙", "甲杀了乙", "乙其实早就死了", "甲爱着乙",
    ]
    for i, txt in enumerate(reveals):
        capture.capture_event(turn_event(event_id=f"turn:rev{i}", text=txt, work="w"))

    assert store.list_memories(work="w") == [], "身份/生死/血缘揭示绝不进 memory_item"
    claims = {c["text"] for c in store.list_pending_authority_claims(work="w")}
    for txt in reveals:
        assert txt in claims, f"限知红线漏放(未拦进待审): {txt}"


def test_p0_normal_experience_not_over_captured(store, capture):
    """普通经验(位置移动/打听消息)不含风险谓词 → 仍进 episodic,不被待审淹没。"""
    _register(store, ("role:甲", "甲"), ("place:城西", "城西"))
    capture.capture_event(turn_event(event_id="turn:exp", text="甲今天去城西打听消息", work="w"))
    assert store.list_pending_authority_claims(work="w") == [], "普通经验不得误拦进待审"
    mems = store.list_memories(work="w", kind="episodic")
    assert mems and any("城西" in m["text"] for m in mems), "普通经验应进 episodic"


def test_p0_hedged_canonical_is_uncertainty_not_pending(store, capture):
    """揣测('我猜甲是凶手')是不确定,不作事实注入也不当正典待审——对冲优先。"""
    _register(store, ("role:甲", "甲"))
    capture.capture_event(turn_event(event_id="turn:hedge", text="我猜甲就是凶手", work="w"))
    assert store.list_pending_authority_claims(work="w") == [], "揣测不进正典待审"
    mems = store.list_memories(work="w", kind="uncertainty")
    assert mems and all(m["confidence"] <= 0.5 for m in mems)


# ---------- P1 幂等:崩溃窗口后重放/重 drain 不产生重复记忆 ----------

def test_p1_replay_after_crash_window_no_duplicate(store, capture, monkeypatch):
    """add_memory_item 成功但 mark_complete 崩(事件置 failed)→ consolidate 认领 failed
    重 drain。add_memory_item 效果幂等(按 source 键预查)→ 不产生第二条 memory_item。"""
    tid = "ethread:w:crash"
    real_complete = store.mark_event_complete
    calls = {"n": 0}

    def flaky_complete(event_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("mark_complete crashed")   # 崩溃窗口:add 已成功,complete 未落
        return real_complete(event_id)

    monkeypatch.setattr(store, "mark_event_complete", flaky_complete, raising=False)

    capture.capture_event(turn_event(event_id="turn:crash", text="已决定把结尾改成留白",
                                     work="w", thread_id=tid))
    assert store.get_memory_event("turn:crash")["status"] == "failed"
    assert store.count_memory_by_source("chat_turn", "turn:crash") == 1

    capture.consolidate_thread(tid, work="w")   # 认领 failed 重 drain
    assert store.get_memory_event("turn:crash")["status"] == "complete"
    assert store.count_memory_by_source("chat_turn", "turn:crash") == 1, \
        "崩溃窗口后重 drain 不得产生重复记忆"


# ---------- 必修2:硬崩溃(SIGKILL/OOM)留 processing 孤儿 → reaper 回收,经验记忆不静默丢失 ----------

def test_p1_hard_crash_processing_orphan_reclaimed_by_consolidate(store, capture):
    """硬崩溃:进程在 begin_processing→mark_complete 窗口被 SIGKILL(直接残留 'processing',
    不经 Python 异常,故不落 failed)→ 事件永久卡 processing;claim_pending_events 只认领
    pending/failed(结构性排除 processing)、无 reaper → 该轮经验记忆静默永久丢失。
    修后:consolidate 起手 reaper 复位 failed → 重 drain 找回,经验记忆最终入库。"""
    tid = "ethread:w:hardcrash"
    store.enqueue_memory_event("turn:hard", "w", "turn",
                               {"text": "已决定把开场改成雪夜"}, thread_id=tid)
    store.begin_processing_event("turn:hard")     # 硬崩溃:留 processing,不 mark

    # 修前症状:卡 processing、claim 认领不到、记忆未入库(静默丢失)
    assert store.get_memory_event("turn:hard")["status"] == "processing"
    assert store.claim_pending_events(work="w", thread_id=tid, event_type="turn") == []
    assert store.count_memory_by_source("chat_turn", "turn:hard") == 0

    # consolidate 端到端回收:step0 reaper 复位 failed + step1 claim 重 drain
    capture.consolidate_thread(tid, work="w")
    assert store.get_memory_event("turn:hard")["status"] == "complete"
    assert store.count_memory_by_source("chat_turn", "turn:hard") == 1, \
        "硬崩溃 processing 孤儿必须被回收,经验记忆不得静默丢失"


def test_p1_reaper_makes_processing_orphan_visible_as_failed(store):
    """reaper 使 processing 孤儿【告警可见】:卡 processing 时 count_failed_memory_events 看不见
    (只数 failed),复位 failed 后可见。这是"静默丢失"变"可见可回收"的关键。"""
    tid = "ethread:w:orphanvis"
    store.enqueue_memory_event("turn:orphan", "w", "turn", {"text": "改了个设定"}, thread_id=tid)
    store.begin_processing_event("turn:orphan")
    assert store.count_failed_memory_events(work="w") == 0     # 卡 processing 不可见

    reclaimed = store.reclaim_stale_processing_events(work="w", thread_id=tid, event_type="turn")
    assert any(r["event_id"] == "turn:orphan" for r in reclaimed)
    assert store.get_memory_event("turn:orphan")["status"] == "failed"
    assert store.count_failed_memory_events(work="w") >= 1     # 复位后告警可见


def test_reaper_time_threshold_spares_fresh_in_flight(store):
    """纵深防御:older_than_seconds 大时,刚置的 processing(可能是在途/跨进程)不被误伤。"""
    tid = "ethread:w:fresh"
    store.enqueue_memory_event("turn:fresh", "w", "turn", {"text": "在途"}, thread_id=tid)
    store.begin_processing_event("turn:fresh")
    reclaimed = store.reclaim_stale_processing_events(
        work="w", thread_id=tid, event_type="turn", older_than_seconds=3600)
    assert reclaimed == []
    assert store.get_memory_event("turn:fresh")["status"] == "processing"


# ---------- 必修3:canonical_claim 路由崩溃窗口重放幂等(不产生重复待审) ----------

def test_p1_canonical_claim_crash_window_is_idempotent(store, capture, monkeypatch):
    """canonical 分支的崩溃窗口重放不得产生重复待审。add_pending_authority_claim 成功但
    mark_complete 崩(事件 failed)→ consolidate 以同 source_id=event_id 重 drain 回 canonical
    → 预查去重命中,pending_authority_claim 仍 1 条(此前裸 CREATE 会得两行同 text)。"""
    tid = "ethread:w:canon-crash"
    real_complete = store.mark_event_complete
    calls = {"n": 0}

    def flaky_complete(event_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("mark_complete crashed")   # 崩溃窗口:待审已建,complete 未落
        return real_complete(event_id)

    monkeypatch.setattr(store, "mark_event_complete", flaky_complete, raising=False)

    capture.capture_event(turn_event(
        event_id="turn:canon", text="甲的真实身份是前朝遗孤",
        classification="canonical_claim", work="w", thread_id=tid))
    assert store.get_memory_event("turn:canon")["status"] == "failed"
    assert len(store.list_pending_authority_claims(work="w")) == 1

    capture.consolidate_thread(tid, work="w")    # 重 drain 同 source_id
    assert store.get_memory_event("turn:canon")["status"] == "complete"
    assert len(store.list_pending_authority_claims(work="w")) == 1, \
        "canonical 崩溃窗口重放不得产生重复待审"


def test_p1_add_memory_item_is_effect_idempotent(store, monkeypatch):
    """add_memory_item 按 (work, source_type, source_id) 效果幂等:重复调用返回同一 id。"""
    _patch_embed(monkeypatch)
    a = store.add_memory_item(work="w", kind="episodic", text="甲在城西",
                              source_type="chat_turn", source_id="turn:dup")
    b = store.add_memory_item(work="w", kind="episodic", text="甲在城西(重放)",
                              source_type="chat_turn", source_id="turn:dup")
    assert a == b
    assert store.count_memory_by_source("chat_turn", "turn:dup") == 1


# ---------- P1 生产签名哨兵:linked_ids/known_from 生产已产出;attribute 缺口如实 ----------

def test_p1_production_signature_wires_linked_ids_and_known_from(store, capture):
    """走生产签名(turn_event 不手喂 entity/attribute,只给 known_from=章):
      · linked_ids 由领域反查生产产出 → focus 加权生效、unlinked_count 归零;
      · known_from 由章生产产出 → 限知门生效;
      · 自由文本 attribute 抽取【待后续】→ 仍 unconflictable(如实哨兵,接入后翻绿)。"""
    _register(store, ("role:甲", "甲"), ("place:城西", "城西"))
    capture.capture_event(turn_event(
        text="甲今天去城西打听消息", work="w", thread_id="ethread:w:prod", known_from=5))

    mems = store.list_memories(work="w", kind="episodic")
    assert mems, "普通经验应进 episodic"
    m = mems[0]
    assert "role:甲" in (m.get("linked_ids") or []), "linked_ids 应由领域反查生产产出"
    assert m.get("known_from") == 5, "known_from 应由 chapter 生产产出"

    r = MemoryRetriever(store).retrieve_full(RetrievalQuery(
        work="w", snapshot={"work": "w", "chapter": 9, "focus": {"id": "role:甲"}},
        query="甲 城西 打听", k=10))
    exp = [c for c in r.selected if c.source_kind == "episodic"]
    assert exp and all(c.linked_ids for c in exp), "生产经验候选应带 linked_ids(focus 加权生效)"
    assert r.unlinked_count == 0, "linked_ids 接线后 unlinked_count 归零"
    assert r.unconflictable_count >= 1, \
        "自由文本 attribute 抽取待后续:仍有压制不了的 episodic(如实哨兵)"
