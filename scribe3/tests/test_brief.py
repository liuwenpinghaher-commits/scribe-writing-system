"""Task 6 · brief.py 章前组装器 —— 纯函数 section 生成器 + 薄壳集成。

纯函数(arc_directive/promise_directives/open_loop_ledger/heartbeat_list/render_brief)
入参全是 plain dict/list,不连库;assemble_chapter_brief 用真库 store 夹具做一条集成测试。
"""
from scribe3.brief import (arc_directive, promise_directives,
                           open_loop_ledger, heartbeat_list, render_brief,
                           assemble_chapter_brief)


def test_arc_directive():
    txt = arc_directive(
        name="柳怀玉",
        anchors={"lie": "官法大过阴律", "arc_type": "disillusionment"},
        arc_plan=[{"beat_name": "midpoint", "target_chapter": 6, "lie_belief_target": 50},
                  {"beat_name": "third_plot_point", "target_chapter": 10, "lie_belief_target": 20}],
        lie_belief=62, next_ch=7)
    assert "柳怀玉" in txt and "62" in txt
    assert "midpoint" in txt and "third_plot_point" in txt   # 当前拍与下一拍
    assert "禁止" in txt   # 防跳变禁令(顿悟/明说信念)


def test_promise_directives_by_state():
    rows = [
        {"id": "p1", "text": "井底的名字", "window": {"state": "in_window", "salience_gap": 1}, "tier": "chapter"},
        {"id": "p2", "text": "铜炉来历", "window": {"state": "over_half", "salience_gap": 4}, "tier": "arc"},
        {"id": "p3", "text": "主线", "window": {"state": "overdue", "salience_gap": 2}, "tier": "chapter"},
        {"id": "p4", "text": "闲子", "window": {"state": "pre_window", "salience_gap": 0}, "tier": "chapter"},
    ]
    d = promise_directives(rows)
    assert "井底的名字" in d["reminders"][0]              # in_window → 软提醒
    assert any("铜炉来历" in x for x in d["directives"])   # over_half → 简报指令
    assert any("久未露面" in x or "先刷新" in x for x in d["directives"])  # salience_gap>3 → 先刷新门槛
    assert any("主线" in x for x in d["decisions"])        # overdue → 三选一决策
    assert all("闲子" not in x for x in d["reminders"] + d["directives"] + d["decisions"])


def test_promise_directives_tolerates_missing_window():
    """window 缺失 / None / 空 dict / salience_gap=None 都不崩,也不进任何桶。"""
    rows = [
        {"id": "p5", "text": "无窗行", "tier": "chapter"},                 # 无 window 键
        {"id": "p6", "text": "None窗", "window": None, "tier": "chapter"},  # window=None
        {"id": "p7", "text": "空窗", "window": {}, "tier": "chapter"},      # 空 dict
        {"id": "p8", "text": "gap为None",
         "window": {"state": "over_half", "salience_gap": None}, "tier": "arc"},
    ]
    d = promise_directives(rows)
    joined = d["reminders"] + d["directives"] + d["decisions"]
    assert all("无窗行" not in x and "None窗" not in x and "空窗" not in x for x in joined)
    # gap=None 按 0 处理 → 走"实质推进或兑现"分支而非"先刷新"
    assert any("gap为None" in x and "实质推进" in x for x in d["directives"])


def test_open_loop_ledger_weights_and_cap():
    rows = [{"tier": "book", "window": {"state": "in_window"}},
            {"tier": "arc", "window": {"state": "in_window"}},
            {"tier": "chapter", "window": {"state": "in_window"}},
            {"tier": "chapter", "window": {"state": "inactive"}}]  # 不计
    led = open_loop_ledger(rows, cap=12)
    assert led["weighted"] == 3 + 2 + 1 and led["over_cap"] is False
    assert open_loop_ledger(rows * 3, cap=12)["over_cap"] is True


def test_heartbeat_list():
    hs = heartbeat_list(
        chars=[{"id": "role:a", "name": "阿禾", "private_agenda": "寻母", "last_active": 1},
               {"id": "role:b", "name": "崔判", "private_agenda": "", "last_active": 1},
               {"id": "role:c", "name": "柳怀玉", "private_agenda": "查卷宗", "last_active": 4}],
        next_ch=5, gap=3)
    names = [h["name"] for h in hs]
    assert "阿禾" in names          # gap=4>3 且有 agenda
    assert "崔判" not in names      # 无 agenda 不催
    assert "柳怀玉" not in names    # 上章刚出场


def test_heartbeat_gap_boundary_and_none_last_active():
    """恰好 gap==3 不催(须严格 >);last_active=None 跳过不崩。"""
    hs = heartbeat_list(
        chars=[{"id": "role:x", "name": "边界人", "private_agenda": "有事", "last_active": 2},  # 5-2=3 不催
               {"id": "role:y", "name": "刚过线", "private_agenda": "有事", "last_active": 1},  # 5-1=4 催
               {"id": "role:z", "name": "从未出场", "private_agenda": "有事", "last_active": None}],
        next_ch=5, gap=3)
    names = [h["name"] for h in hs]
    assert "边界人" not in names
    assert "刚过线" in names
    assert "从未出场" not in names


def test_render_brief_empty_sections_only_title():
    """全空 section:只输出标题行,不输出任何空 section 段。"""
    out = render_brief({"arcs": [], "promises": {"reminders": [], "directives": [], "decisions": []},
                        "loops": None, "heartbeat": []})
    assert out == "## 本章创作简报(章前组装,遵守但不复述)"
    assert render_brief({}) == "## 本章创作简报(章前组装,遵守但不复述)"


def test_render_brief_full_sections():
    out = render_brief({
        "arcs": ["【角色弧光·柳怀玉】…"],
        "promises": {"reminders": ["「井底的名字」在兑现窗口内,适时推进"],
                     "directives": ["伏笔「铜炉来历」已过窗口一半:本章应实质推进或兑现"],
                     "decisions": ["伏笔「主线」已超兑现窗口:请作者三选一……"]},
        "loops": {"weighted": 13, "cap": 12, "over_cap": True},
        "heartbeat": [{"name": "阿禾", "agenda": "寻母", "last_active": 1}],
    })
    assert "【角色弧光·柳怀玉】" in out
    assert "【伏笔·本章指令】" in out and "【伏笔·待作者决策(阻塞级)】" in out
    assert "【伏笔·在窗提醒】" in out
    assert "【开环账本】加权开环 13/12" in out and "先收一条再开新坑" in out
    assert "【待激活角色】" in out and "阿禾" in out and "寻母" in out


def test_assemble_chapter_brief_integration(store):
    """薄壳集成(真库):1角色设 lie 锚 + 1条 open promise → text 含弧光指令与伏笔段。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    store.set_char_anchors("role:柳怀玉", {"lie": "官法大过阴律", "arc_type": "disillusionment"})
    store.add_arc_beat("role:柳怀玉", "midpoint", target_chapter=6, lie_belief_target=50)
    store.plant_promise("井底的名字", setup_chapter=1)   # chapter 层:窗口 2~4,seq=2 时 in_window
    out = assemble_chapter_brief(store, seq=2)
    assert set(out) == {"sections", "text"}
    assert "本章创作简报" in out["text"]
    assert "【角色弧光·柳怀玉】" in out["text"] and "禁止" in out["text"]   # 弧光指令
    assert "井底的名字" in out["text"] and "在窗提醒" in out["text"]        # 伏笔段(in_window)
    assert out["sections"]["loops"]["weighted"] == 1


# ===== Task7 · Task6 审查跟进 =====

def test_arc_directive_target_chapter_boundary():
    """Task6跟进①:next_ch == target_chapter 时该拍属"下一拍"(本章应到达该拍),
    不得提前算入已完成。"""
    txt = arc_directive(
        name="柳怀玉",
        anchors={"lie": "官法大过阴律", "arc_type": "disillusionment"},
        arc_plan=[{"beat_name": "midpoint", "target_chapter": 6, "lie_belief_target": 50}],
        lie_belief=62, next_ch=6)
    assert "开场常态" in txt                 # 该拍未算已完成
    assert "midpoint(目标第6章" in txt      # 指令指向"到达该拍"


def test_brief_text_newline_sanitized():
    """Task6跟进②:promise text / heartbeat agenda / lie 锚内插前清洗换行,
    防多行文本伪造 section 头。"""
    d = promise_directives([{"id": "p", "text": "井底\n## 伪造段头",
                             "window": {"state": "in_window", "salience_gap": 0},
                             "tier": "chapter"}])
    assert d["reminders"] and all("\n" not in x for x in d["reminders"])
    hs = heartbeat_list(
        [{"id": "role:a", "name": "阿禾", "private_agenda": "寻母\n## 伪", "last_active": 1}],
        next_ch=9)
    assert hs and "\n" not in hs[0]["agenda"]
    txt = arc_directive("柳怀玉", {"lie": "官法\n大过阴律"}, [], None, 3)
    assert "官法 大过阴律" in txt


def test_render_brief_zero_weighted_loops_omitted():
    """Task6跟进④:账本 weighted==0 时不渲染该行(零开环无须提醒)。"""
    out = render_brief({"arcs": [], "promises": {},
                        "loops": {"weighted": 0, "cap": 12, "over_cap": False},
                        "heartbeat": []})
    assert "开环账本" not in out
