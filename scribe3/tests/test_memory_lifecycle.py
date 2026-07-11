"""Task 10 · 记忆的三时态、更正、作废与遗忘生命周期测试。

分两层:
1) 纯函数层(memory_lifecycle.visible / resolve_temporal_view)——三时态判定:
   故事真值(story_time)≠ 角色知道(knowledge_time),focalizer 是投影参数。
2) store-backed 层——supersede 留审计、invalidate/superseded 排除检索、forget 两阶段、
   forget 不碰正典领域数据、resolve_temporal_view 的 chapter×focalizer 投影矩阵。

铁律:绝不真调 embedding 服务,一律 monkeypatch scribe3.embed.embed(与 test_memory_retrieval 同款)。
"""
from __future__ import annotations

import math

from scribe3.memory_capture import MemoryCapture, turn_event
from scribe3.memory_lifecycle import resolve_temporal_view, visible
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


def item(**kw) -> dict:
    """构造一条最小记忆行(默认 active),供纯函数层可见性判定。"""
    return {"status": "active", **kw}


# ---------- 纯函数层:三时态语义(计划 Step 1 第一条)----------

def test_story_validity_and_character_knowledge_are_distinct():
    """故事真值 ≠ 角色知道:同一条记忆在故事第 4 章成立,但聚焦角色第 8 章才知道。"""
    memory = item(valid_from=4, valid_to=None, known_from=8, known_to=None)
    assert visible(memory, chapter=6, focalizer=None) is True       # 无视角=故事真值,valid_from<=6
    assert visible(memory, chapter=6, focalizer="role:a") is False  # role:a 在 ch6 还不知道(known_from=8)
    assert visible(memory, chapter=9, focalizer="role:a") is True   # ch9>=known_from=8


def test_story_time_gate_before_valid_from_hidden():
    """valid_from 之前,连全知视角都看不到(事实在故事里还没成立)。"""
    memory = item(valid_from=4, valid_to=None)
    assert visible(memory, chapter=3, focalizer=None) is False
    assert visible(memory, chapter=4, focalizer=None) is True


def test_story_time_upper_bound_is_half_open():
    """valid_to 为半开区间:valid_to=7 → 第 7 章起不再成立。"""
    memory = item(valid_from=2, valid_to=7)
    assert visible(memory, chapter=6, focalizer=None) is True
    assert visible(memory, chapter=7, focalizer=None) is False


def test_superseded_and_invalid_never_visible():
    """非 active(superseded/invalid)一律不可见,即便时态命中。"""
    assert visible(item(valid_from=1, status="superseded"), chapter=5, focalizer=None) is False
    assert visible(item(valid_from=1, status="invalid"), chapter=5, focalizer=None) is False


def test_discussion_mode_chapter_none_fail_open():
    """讨论模式 chapter=None → 不做时态过滤(fail-open),active 即可见。"""
    memory = item(valid_from=9, known_from=9)
    assert visible(memory, chapter=None, focalizer=None) is True
    assert visible(memory, chapter=None, focalizer="role:a") is True


def test_resolve_temporal_view_pure_filters_and_keeps_order():
    mems = [
        item(valid_from=1, known_from=8),   # 故事成立于1;role:a 第8章才知道
        item(valid_from=6),                 # 故事第6章才成立
        item(valid_from=1, status="invalid"),
    ]
    # ch5 全知:第一条可见、第二条未成立、第三条 invalid
    assert resolve_temporal_view(mems, 5, None) == [mems[0]]
    # ch5 限知 role:a:第一条也被 knowledge_time 挡下 → 空
    assert resolve_temporal_view(mems, 5, "role:a") == []


# ---------- store 层:更正留审计(计划 Step 1 第二条)----------

def test_correction_keeps_audit_history(store, monkeypatch):
    _patch_embed(monkeypatch)
    old = store.add_memory(text="甲喜欢青色", work="w")
    new = store.supersede_memory(old["id"], text="甲只是害怕红色", reason="author_correction")
    # 旧记录留库、状态转 superseded(审计不删)
    assert store.get_memory(old["id"])["status"] == "superseded"
    # 新记录 active,supersedes 指回旧记录(裸 id)
    assert store.get_memory(new["id"])["status"] == "active"
    assert store.get_memory(new["id"])["supersedes"] == old["id"]
    assert new["text"] == "甲只是害怕红色"


def test_supersede_inherits_temporal_and_can_override(store, monkeypatch):
    _patch_embed(monkeypatch)
    old = store.add_memory(text="甲住城东", work="w", kind="episodic",
                           valid_from=3, known_from=5)
    # 不传时态 → 承接旧值
    inherit = store.supersede_memory(old["id"], text="甲住城东老宅")
    assert inherit["valid_from"] == 3 and inherit["known_from"] == 5
    # 传时态 → 更正之(时间线纠错)
    corrected = store.supersede_memory(inherit["id"], text="甲其实一直住城南",
                                       valid_from=1, known_from=2)
    assert corrected["valid_from"] == 1 and corrected["known_from"] == 2


# ---------- store 层:invalid / superseded 排除检索 ----------

def _retrieve_ids(store, query, snapshot=None):
    res = MemoryRetriever(store).retrieve_full(RetrievalQuery(
        work="w", snapshot=snapshot or {"work": "w"}, query=query, k=10))
    return [c.source_id for c in res.selected]


def test_invalidate_excludes_from_retrieval(store, monkeypatch):
    _patch_embed(monkeypatch)
    m = store.add_memory(text="城西有座废庙很关键", work="w", kind="episodic")
    assert f"mem:{m['id']}" in _retrieve_ids(store, "废庙 城西")   # 基线可召回
    invalidated = store.invalidate_memory(m["id"])
    assert invalidated["status"] == "invalid"
    assert invalidated["invalid_at"]                              # system_time 记录失效时刻
    assert f"mem:{m['id']}" not in _retrieve_ids(store, "废庙 城西")  # 作废后不再召回


def test_superseded_old_excluded_new_retrievable(store, monkeypatch):
    _patch_embed(monkeypatch)
    old = store.add_memory(text="甲住在城东老宅", work="w", kind="episodic")
    new = store.supersede_memory(old["id"], text="甲住在城南别院")
    ids = _retrieve_ids(store, "甲 住在")
    assert f"mem:{old['id']}" not in ids   # 旧记录(superseded)不召回
    assert f"mem:{new['id']}" in ids       # 新记录(active)可召回


def test_graph_channel_excludes_superseded_neighbor(store, monkeypatch):
    """graph 通道也必须排除 superseded 邻居——不能绕过 status 门倒灌回检索。"""
    _patch_embed(monkeypatch)
    seed = store.add_memory(text="线索指向青色披风", work="w", kind="episodic")
    neigh = store.add_memory(text="青色披风属于甲", work="w", kind="episodic")
    store.add_memory_relation(seed["id"], neigh["id"], "same_topic")
    assert neigh["id"] in store.memory_graph("w", [seed["id"]], k=10)   # 基线
    store.supersede_memory(neigh["id"], text="青色披风其实属于乙")
    assert neigh["id"] not in store.memory_graph("w", [seed["id"]], k=10)


# ---------- store 层:forget 两阶段 ----------

def test_forget_is_two_phase(store, monkeypatch):
    _patch_embed(monkeypatch)
    a = store.add_memory(text="临时目标:修第八章结尾", work="w", kind="working")
    b = store.add_memory(text="第八章结尾要收束伏笔", work="w", kind="episodic")
    store.add_memory_relation(a["id"], b["id"], "same_topic")

    # 阶段一:影响清单,什么都不删
    impact = store.forget_impact(a["id"])
    assert impact["exists"] is True
    assert impact["relation_count"] >= 1
    assert store.get_memory(a["id"]) is not None

    # 未确认的 forget = 不删(deleted=False)
    res0 = store.forget_memory(a["id"])
    assert res0["deleted"] is False
    assert store.get_memory(a["id"]) is not None

    # 阶段二:确认后真删本记忆 + 其联想边
    res = store.forget_memory(a["id"], confirmed=True)
    assert res["deleted"] is True
    assert store.get_memory(a["id"]) is None
    assert store.forget_impact(a["id"])["relation_count"] == 0
    # 关联到的另一条记忆 b 不受牵连(只删触及 a 的边)
    assert store.get_memory(b["id"]) is not None


def test_forget_through_capture_clears_payload_and_prevents_revival(store, monkeypatch):
    """I-1 彻底性:经真实捕获管线的记忆,forget 后必须清掉来源事件 payload 原文,
    且 re-consolidate 不能把它从残留 payload 自动重炼/re-drain 复活。
    (现有 test_forget_* 直调 add_memory 不经捕获管线,盖不住此缺口——本条经 MemoryCapture。)"""
    _patch_embed(monkeypatch)
    cap = MemoryCapture(store)
    text = "我们这次决定把废庙那段删掉"
    cap.capture_event(turn_event(text=text, event_id="turn:forget1", work="w", thread_id="th"))
    mid = store.list_memories(kind="episodic", work="w")[0]["id"]
    # 复现审计②:consolidate 把原文炼进 working_summary.decisions
    ws0 = cap.consolidate_thread("th", work="w")
    assert text in ws0["decisions"]

    # 影响清单如实披露来源事件 + working_summary(契约不再说谎)
    impact = store.forget_impact(mid)
    assert impact["origin_event_id"] == "turn:forget1"
    assert impact["working_summary_thread"] == "th"
    assert "working_summary" in impact["note"]

    res = store.forget_memory(mid, confirmed=True)
    assert res["deleted"] is True
    assert res["origin_event_deleted"] is True
    assert res["working_summary_invalidated"] is True

    # ① 来源事件 payload 原文已清
    assert store.get_memory_event("turn:forget1") is None
    # ③ re-consolidate 不复活:事件已删,无残留可重炼/re-drain
    ws1 = cap.consolidate_thread("th", work="w")
    assert text not in ws1["decisions"]
    assert store.count_memory_by_source("chat_turn", "turn:forget1") == 0
    assert store.get_memory(mid) is None


def test_supersede_is_idempotent_on_retry(store, monkeypatch):
    """M-1:同 (旧id, reason) 的重复 supersede 幂等——预查命中已建取代记录直接返回,
    不再撞显式 id 冲突、不二次更正、只建一条取代记录。"""
    _patch_embed(monkeypatch)
    old = store.add_memory(text="甲怕黑", work="w")
    n1 = store.supersede_memory(old["id"], text="甲其实怕水", reason="author_correction")
    n2 = store.supersede_memory(old["id"], text="甲其实怕水", reason="author_correction")
    assert n1["id"] == n2["id"]                                  # 幂等:同一取代记录
    assert store.get_memory(old["id"])["status"] == "superseded"  # 旧记录只被更正一次
    sups = [m for m in store.list_memories(kind="episodic", work="w")
            if m.get("source_id") == f"supersede:{old['id']}"]
    assert len(sups) == 1                                        # 只建了一条取代记录


def test_forget_does_not_touch_canonical_domain(store, monkeypatch):
    """限知红线:forget 只删经验记忆,正典/领域 proposition 一概不碰。"""
    _patch_embed(monkeypatch)
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:loc", "role:甲", "location", "城东", valid_from=1))
    mem = store.add_memory(text="甲曾在城东露面", work="main", kind="episodic",
                           entity="role:甲", attribute="location")
    store.forget_memory(mem["id"], confirmed=True)
    assert store.get_memory(mem["id"]) is None                     # 经验记忆没了
    facts = store.facts_at(5)
    assert any(getattr(f, "entity_id", "") == "role:甲" for f in facts)  # 正典事实完好


# ---------- store 层:resolve_temporal_view 的 chapter×focalizer 投影矩阵 ----------

def test_resolve_temporal_view_projects_chapter_and_focalizer(store, monkeypatch):
    _patch_embed(monkeypatch)
    # 故事第4章成立;聚焦角色 role:a 第8章才知道
    m = store.add_memory(text="甲害怕红色", work="w", kind="episodic",
                         valid_from=4, known_from=8)

    def ids(chapter, focalizer):
        return [x["id"] for x in store.resolve_temporal_view("w", chapter, focalizer)]

    # 全知视角(focalizer=None):故事真值,ch>=4 可见
    assert m["id"] in ids(6, None)
    assert m["id"] not in ids(3, None)      # valid_from 之前,尚未成立
    # 限知视角(role:a):knowledge_time 门叠加,ch8 前不可见
    assert m["id"] not in ids(6, "role:a")
    assert m["id"] in ids(9, "role:a")
    # invalidate 后任何视角都投影不到(status 门)
    store.invalidate_memory(m["id"])
    assert m["id"] not in ids(9, None)
    assert m["id"] not in ids(9, "role:a")
