"""Task 6 · brief.py 章前组装器 —— 纯函数 section 生成器 + 薄壳集成。

纯函数(arc_directive/promise_directives/open_loop_ledger/heartbeat_list/render_brief)
入参全是 plain dict/list,不连库;assemble_chapter_brief 用真库 store 夹具做一条集成测试。
"""
from scribe3.brief import (arc_directive, promise_directives,
                           open_loop_ledger, heartbeat_list, render_brief,
                           assemble_chapter_brief, validate_beat_budgets,
                           find_tension_monotony, parse_chapter_meta,
                           heat_of, stale_entity_directives,
                           emotion_module_recall, inherited_open_block)


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


# ===== Task 8 · M6 设定三态注入(纯函数)=====

def test_select_injection_modes_budget_and_manifest():
    from scribe3.brief import select_injection
    items = [
        {"id": "f1", "entity": "role:崔判", "text": "崔判是阴司判官", "mode": "always", "priority": 9},
        {"id": "f2", "entity": "role:柳怀玉", "text": "柳怀玉左手有疤", "mode": "detected", "priority": 5},
        {"id": "f3", "entity": "role:阿禾", "text": "阿禾会口技", "mode": "detected", "priority": 5},
        {"id": "f4", "entity": "role:崔判", "text": "崔判怕铜镜", "mode": "never", "priority": 9},
    ]
    r = select_injection(items, mentioned_entities={"role:柳怀玉"}, budget_chars=1000)
    ids = [i["id"] for i in r["chosen"]]
    assert "f1" in ids          # always 恒注入
    assert "f2" in ids          # detected 且被提及
    assert "f3" not in ids      # detected 未提及
    assert "f4" not in ids      # never 恒不注入
    assert r["dropped"] == 0
    # 预算裁剪:预算极小 → 按 priority 保 always,记 dropped
    r2 = select_injection(items, {"role:柳怀玉", "role:阿禾"}, budget_chars=10)
    assert r2["dropped"] >= 1


def test_mentioned_entities_by_alias():
    from scribe3.brief import detect_mentions
    ents = [{"id": "role:柳怀玉", "name": "柳怀玉", "aliases": ["柳师爷"]},
            {"id": "role:阿禾", "name": "阿禾", "aliases": []}]
    hit = detect_mentions("这章柳师爷去义庄", ents)
    assert hit == {"role:柳怀玉"}


# ===== 方案B任务10 · 情节点字数预算契约(纯函数验证器)=====

class TestBeatBudgets:
    def test_budget_sum_within_window(self):
        beats = [{"text": "夜探义庄", "density": "密", "budget": 900},
                 {"text": "过场赶路", "density": "疏", "budget": 60},
                 {"text": "纸人现形", "density": "密", "budget": 1200}]
        r = validate_beat_budgets(beats, target_words=2000)
        assert r["ok"] and r["total"] == 2160   # ∈ [2000, 2200]

    def test_budget_overflow_flagged(self):
        beats = [{"text": "a", "density": "密", "budget": 3000}]
        r = validate_beat_budgets(beats, target_words=2000)
        assert not r["ok"] and r["reason"] == "over"

    def test_budget_underflow_flagged(self):
        assert not validate_beat_budgets([{"text": "a", "density": "疏", "budget": 40}],
                                         target_words=2000)["ok"]

    def test_missing_budget_tolerated(self):
        # 旧数据无 budget 字段:不判,ok=None(向后兼容)
        assert validate_beat_budgets([{"text": "旧节拍"}], target_words=2000)["ok"] is None


# ===== 方案B任务11 · 章节定位六型 + 卷级张弛基线(纯函数检测器)=====

class TestTensionMonotony:
    def test_same_role_run_over_3_flagged(self):
        meta = [{"seq": i, "role": "高压", "pressure": 5} for i in range(1, 5)]
        issues = find_tension_monotony(meta)
        assert any(i["kind"] == "role_run" for i in issues)

    def test_varied_roles_clean(self):
        meta = [{"seq": 1, "role": "高压", "pressure": 4}, {"seq": 2, "role": "低压", "pressure": 2},
                {"seq": 3, "role": "推进", "pressure": 3}, {"seq": 4, "role": "高压", "pressure": 5}]
        assert find_tension_monotony(meta) == []

    def test_all_high_pressure_flagged(self):
        meta = [{"seq": i, "role": r, "pressure": 5} for i, r in enumerate(["高压", "推进", "高压", "推进", "高压", "推进"], 1)]
        issues = find_tension_monotony(meta)
        assert any(i["kind"] == "pressure_flat" for i in issues)

    def test_missing_meta_tolerated(self):
        assert find_tension_monotony([{"seq": 1}, {"seq": 2}]) == []


class TestParseChapterMeta:
    def test_parses_role_and_pressure(self):
        text = "本章大纲……压力级:4\nchapter_role:高压\n后续文本"
        meta = parse_chapter_meta(text)
        assert meta == {"role": "高压", "pressure": 4}

    def test_parses_from_beats_list(self):
        beats = [{"text": "开场铺垫"}, {"text": "压力级:2 chapter_role:低压"}]
        assert parse_chapter_meta(beats) == {"role": "低压", "pressure": 2}

    def test_no_match_returns_none(self):
        assert parse_chapter_meta("旧数据无标注的大纲文本") is None
        assert parse_chapter_meta(None) is None
        assert parse_chapter_meta([]) is None


# ===== 方案B任务12 · 连续性 heat/last_touch 状态机 + 关系触碰追踪 =====

class TestHeat:
    def test_heat_tiers(self):
        assert heat_of(last_touch=9, current=10) == "hot"      # 距离≤2
        assert heat_of(last_touch=6, current=10) == "warm"     # 3-5
        assert heat_of(last_touch=2, current=10) == "cold"     # >5
        assert heat_of(last_touch=None, current=10) == "cold"

    def test_cold_entities_injected(self):
        rows = [{"name": "白纸人", "kind": "char", "last_touch": 2}]
        out = stale_entity_directives(rows, next_ch=10)
        assert "白纸人" in out["text"] and out["items"][0]["heat"] == "cold"

    def test_hot_warm_entities_not_injected(self):
        """只有 cold 才生成指令段——hot/warm 无需催。"""
        rows = [{"name": "阿禾", "kind": "char", "last_touch": 9},   # hot
                {"name": "柳怀玉", "kind": "char", "last_touch": 6}]  # warm
        out = stale_entity_directives(rows, next_ch=10)
        assert out["text"] == "" and out["items"] == []

    def test_directive_text_mentions_valid_touch_discipline_and_thresholds(self):
        """指令段须含有效触碰纪律 + 回顾阈值语境(核心角色/主要支线)。"""
        rows = [{"name": "老李", "kind": "promise", "last_touch": None}]
        out = stale_entity_directives(rows, next_ch=5)
        assert "有效触碰" in out["text"]
        assert "提名字" in out["text"] or "空头" in out["text"]
        assert "核心角色" in out["text"] and "主要支线" in out["text"]


# ===== 方案B任务15 · EM/RH/TR 情绪模式库(章前按目标情绪召回)=====

class TestEmotionModuleRecall:
    def test_recall_by_target_emotion(self):
        mats = [
            {"kind": "emotion_module", "title": "憋屈反杀",
             "content": '{"id":"EM-001","emotion":"憋屈","trigger":"当众羞辱","escalation":"隐忍蓄力","release":"当众反杀"}'},
            {"kind": "emotion_module", "title": "别的",
             "content": '{"id":"EM-002","emotion":"温情","trigger":"…","escalation":"…","release":"…"}'},
            {"kind": "note", "title": "无关", "content": "随手记"},
        ]
        out = emotion_module_recall(mats, target_emotion="憋屈")
        assert "EM-001" in out["text"] and "EM-002" not in out["text"]
        assert "反应篇幅比" in out["text"]        # 量化门
        assert "不可照搬" in out["text"]          # 反抄袭边界
        assert "权威真相源" in out["text"]        # canonical-read-order

    def test_no_match_returns_empty(self):
        assert emotion_module_recall([], target_emotion="憋屈")["text"] == ""

    def test_bad_json_tolerated(self):
        mats = [{"kind": "emotion_module", "title": "坏卡", "content": "不是JSON"}]
        assert emotion_module_recall(mats, target_emotion="憋屈")["text"] == ""

    def test_falls_back_to_body_field_when_no_content(self):
        """B15 审查盲区(收尾清理批 Minor):store.list_materials() 返回的元素用
        "body" 字段(无 "content" 键),emotion_module_recall 须回退读 body,
        不能因为没有 "content" 就漏召回。"""
        mats = [
            {"kind": "emotion_module", "title": "憋屈反杀",
             "body": '{"id":"EM-001","emotion":"憋屈","trigger":"当众羞辱","escalation":"隐忍蓄力","release":"当众反杀"}'},
        ]
        out = emotion_module_recall(mats, target_emotion="憋屈")
        assert "EM-001" in out["text"]
        assert out["items"] and out["items"][0]["id"] == "EM-001"


# ===== 方案B任务17 · 平台留存轴确定性指标(纯文本层,独立于 tension_deterministic)=====

class TestPlatformDeterministic:
    def test_dialogue_ratio(self):
        from scribe3.brief import platform_deterministic
        # 对话占比:引号内字数/总可见字数
        t = "「你走。」他说。「不走。」她答。叙述文字若干若干。"
        items = platform_deterministic(t, platform="qidian")
        dr = next(i for i in items if i["metric"] == "dialogue_ratio")
        assert 0 < dr["value"] < 1

    def test_word_count_range(self):
        from scribe3.brief import platform_deterministic
        items = platform_deterministic("字" * 100, platform="qidian")
        wc = next(i for i in items if i["metric"] == "word_count")
        assert wc["value"] == 100 and wc["ok"] is False   # 起点章通常 2000-4000,100 字不达标


# ===== 方案B任务19 · 跨批开放伏笔账本注入 reviewer(scribe3 DB 优势区)=====
# 背景(oh-story story-review/SKILL.md:133):审章前先读"预计回收章≤本章"的 open
# promises 作"继承的开放项"注入 reviewer。oh-story 靠读伏笔.md 文件做(demo 实锤:
# 51 条全 [待补充] 冻结);scribe3 有活 DB,直接对 promises_with_lifecycle 结果筛,
# 不依赖任何人工维护的台账文件。

class TestInheritedOpenBlock:
    def test_due_promises_injected(self):
        rows = [
            {"id": "p1", "text": "玉佩来历", "status": "open", "setup_chapter": 1, "payoff_min": 3, "payoff_max": 5, "tier": "arc"},
            {"id": "p2", "text": "远期书级", "status": "open", "setup_chapter": 1, "payoff_min": 40, "payoff_max": None, "tier": "book"},
            {"id": "p3", "text": "已关闭", "status": "closed", "setup_chapter": 1, "payoff_min": 2, "payoff_max": 3, "tier": "chapter"},
        ]
        out = inherited_open_block(rows, chapter=5)
        assert "玉佩来历" in out["text"]           # 窗口内到期,注入
        assert "远期书级" not in out["text"]        # 远未到期,不注入
        assert "已关闭" not in out["text"]          # closed 不注入
        assert "找问题" in out["text"] or "继承的开放项" in out["text"]

    def test_empty_when_nothing_due(self):
        assert inherited_open_block([], chapter=5)["text"] == ""

    def test_book_tier_past_payoff_min_not_injected(self):
        """B19 审查(收尾清理批 Minor):显式锁 book 级守卫分支——payoff_min<chapter
        但 payoff_max=None(book 层无远期上限)的 open promise 不被注入:
        第一条件(pmax<=chapter)因 pmax 为 None 为假,第二条件(窗口内)也因
        pmax 为 None 跳过——book 级悬念不该每章都被当作"到期继承项"催办。"""
        rows = [
            {"id": "pb", "text": "书级母题", "status": "open", "setup_chapter": 1,
             "payoff_min": 3, "payoff_max": None, "tier": "book"},
        ]
        out = inherited_open_block(rows, chapter=10)   # chapter=10 > payoff_min=3
        assert out["text"] == "" and out["items"] == []
