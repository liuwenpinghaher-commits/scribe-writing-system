"""Codex 2.0 设定库重构:人物深化字段 + 母题 Motif + 力量体系字段 + 注入升级。
依据 docs/superpowers/2026-06-21-设定库重构文档-codex-2.0.md。
"""
from scribe2.conn import domain_from
from scribe2.writing import build_writing_context


def test_character_rich_fields(db):
    """人物卡存内核(wound/lie/want/need)+ 核心矛盾 + 声音样本 + 弧光 —— 乱世铜炉判据3。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    d.add_character(
        w, "渡叔", motivation="守渡赎罪", voice="极静、短句、不解释",
        voice_samples=["三不渡，是规矩。", "你欠的，水替你还。"],
        core_contradiction="守规矩的执念 ↔ 为孩子愿破规矩",
        wound="四十年前破规渡苏清湄，害死师父、瞎了左眼",
        lie="守住规矩就能赎清罪",
        want="守好九原渡", need="放下赎罪执念、接纳自己",
        arc="从以规矩自惩 → 为护幼者主动破规、与自己和解",
    )
    c = next(x for x in d.list_characters(w) if x["name"] == "渡叔")
    assert c["voice_samples"] == ["三不渡，是规矩。", "你欠的，水替你还。"]
    assert c["core_contradiction"].startswith("守规矩")
    assert c["wound"] and c["lie"] and c["want"] == "守好九原渡" and c["need"]
    assert "和解" in c["arc"]
    # 向后兼容:旧式只传 motivation/voice 仍可用,新字段给默认空
    d.add_character(w, "阿砚", motivation="活命")
    a = next(x for x in d.list_characters(w) if x["name"] == "阿砚")
    assert a["voice_samples"] == [] and a["wound"] == ""


def test_motif_entity(db):
    """母题 Motif:核心意象的隐喻网 —— 乱世铜炉判据1(四位一体)。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    d.add_motif(
        w, "铜炉",
        metaphor_unfolding="天地为炉，造化为工，阴阳为炭，万物为铜——普世受苦、无可逃脱",
        bound_theme="乱世弱肉强食，一粒铜丸须自强方能立身",
        material_echoes=["香炉熄火", "身成火炉", "取名胡炭", "赶路日头如炉"],
        naming_logic="主角给儿子取名'炭'",
    )
    m = next(x for x in d.list_motifs(w) if x["name"] == "铜炉")
    assert "万物为铜" in m["metaphor_unfolding"]
    assert m["material_echoes"] == ["香炉熄火", "身成火炉", "取名胡炭", "赶路日头如炉"]
    assert m["bound_theme"] and m["naming_logic"]


def test_setting_structured_fields(db):
    """设定可带结构化自定义字段(力量体系:cost/limitations/会出什么乱子)—— 乱世铜炉判据2。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    d.add_setting(
        w, "内丹还魂", "以妖兽内丹聚魂还阳", "力量体系",
        fields={"cost": "属性反噬:火性内丹猛烈，不会运化则吐血伤身",
                "limitations": "四百年丹方能聚魂，越五百年反只助功力",
                "trouble_it_causes": "主角强吞蜈蚣丹被火力所伤、白白浪费道行"},
    )
    s = next(x for x in d.list_settings(w) if x["name"] == "内丹还魂")
    assert s["type"] == "力量体系"
    assert s["fields"]["cost"].startswith("属性反噬")
    assert s["fields"]["limitations"] and s["fields"]["trouble_it_causes"]
    # 旧式无 fields 仍可用,返回空 dict
    d.add_setting(w, "九原渡", "浊河北岸古渡", "place")
    s2 = next(x for x in d.list_settings(w) if x["name"] == "九原渡")
    assert s2["fields"] == {}


def test_injection_includes_rich_settings(db):
    """W2:深化设定(声音样本/核心矛盾/母题/规则代价)必须真正进入写作上下文。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    d.set_intent(w, reader_feeling="苍凉")
    d.add_character(w, "渡叔", motivation="守渡赎罪", voice="极静",
                    voice_samples=["三不渡，是规矩。"],
                    core_contradiction="守规矩↔为孩子破规矩")
    d.add_motif(w, "铜炉", metaphor_unfolding="万物为铜",
                bound_theme="弱肉强食", material_echoes=["香炉熄火"])
    d.add_setting(w, "内丹还魂", "聚魂还阳", "力量体系",
                  fields={"cost": "火性反噬吐血", "limitations": "四百年丹方能聚魂"})
    d.add_chapter(w, 1, "夜渡")
    ctx = build_writing_context(d, w, 1)
    # 确定性注入(非语义召回兜底):声音样本+核心矛盾须在「角色」块那一行
    char_line = next((l for l in ctx.split("\n") if "角色" in l and "渡叔" in l), "")
    assert "三不渡，是规矩。" in char_line, "声音样本须确定性注入角色块"
    assert "守规矩↔为孩子破规矩" in char_line, "核心矛盾须注入角色块"
    # 母题专属块
    assert "【核心意象" in ctx and "铜炉" in ctx and "弱肉强食" in ctx
    # 力量体系代价/限制专属块
    assert "【规则" in ctx and "火性反噬吐血" in ctx and "四百年丹方能聚魂" in ctx


def test_mcp_codex_write_tools(db):
    """W3:MCP 写工具覆盖 Codex 2.0 富 schema,且都登记进 WRITE_TOOLS(B3 待批)。"""
    import scribe2.mcp as M
    M.set_domain(domain_from(db)); M._domain().s.init_schema()
    w = M._domain().create_work("书")
    # upsert_character 富字段
    r = M.upsert_character(w, "渡叔", motivation="守渡", voice="极静",
                           voice_samples=["三不渡，是规矩。"], core_contradiction="守↔破", wound="赎罪")
    assert r["character_id"]
    c = M._domain().list_characters(w)[0]
    assert c["voice_samples"] == ["三不渡，是规矩。"] and c["wound"] == "赎罪"
    # add_motif
    rm = M.add_motif(w, "铜炉", metaphor_unfolding="万物为铜", bound_theme="弱肉强食",
                     material_echoes=["长明灯"])
    assert rm["motif_id"] and M._domain().list_motifs(w)[0]["name"] == "铜炉"
    assert M.list_motifs(w)[0]["name"] == "铜炉"   # 读工具
    # add_setting 结构化字段
    rs = M.add_setting(w, "三不渡", "三条铁律", "力量体系", fields={"cost": "破规左眼瞎"})
    assert rs["setting_id"]
    assert M._domain().list_settings(w)[0]["fields"]["cost"] == "破规左眼瞎"
    # 写工具登记进 WRITE_TOOLS(经 B3 待批)
    for t in ("add_motif", "upsert_character", "add_setting"):
        assert t in M.WRITE_TOOLS


def test_upsert_character_merges(db):
    """upsert_character 按名更新合并(对话式'改'的基础),不产生重复。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    d.add_character(w, "渡叔", motivation="守渡赎罪", voice="极静")
    # 同名 upsert:补声音样本+创伤,保留原 motivation/voice
    d.upsert_character(w, "渡叔", voice_samples=["三不渡，是规矩。"], wound="四十年前破规")
    chars = [c for c in d.list_characters(w) if c["name"] == "渡叔"]
    assert len(chars) == 1, "同名不应重复"
    c = chars[0]
    assert c["voice_samples"] == ["三不渡，是规矩。"] and c["wound"].startswith("四十年")
    assert c["motivation"] == "守渡赎罪" and c["voice"] == "极静"  # 原字段保留
    # 不存在则新建
    d.upsert_character(w, "阿砚", motivation="活命")
    assert any(c["name"] == "阿砚" for c in d.list_characters(w))


def test_rest_codex2(db):
    """W5:REST 暴露 Codex 2.0 —— 人物富字段+upsert、设定 fields、母题 CRUD。"""
    from fastapi.testclient import TestClient
    from scribe2.app import app, get_domain
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    c = TestClient(app); H = {"X-Owner-Id": "u1"}
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.post(f"/works/{w}/characters", json={
            "name": "渡叔", "motivation": "守渡", "voice": "极静",
            "voice_samples": ["三不渡，是规矩。"], "core_contradiction": "守↔破", "wound": "赎罪"}, headers=H)
        ch = c.get(f"/works/{w}/characters", headers=H).json()
        assert len(ch) == 1 and ch[0]["voice_samples"] == ["三不渡，是规矩。"] and ch[0]["wound"] == "赎罪"
        # 同名再 POST = upsert 合并不重复
        c.post(f"/works/{w}/characters", json={"name": "渡叔", "want": "守好九原渡"}, headers=H)
        ch2 = c.get(f"/works/{w}/characters", headers=H).json()
        assert len(ch2) == 1 and ch2[0]["want"] == "守好九原渡" and ch2[0]["wound"] == "赎罪"
        # 设定结构化 fields
        c.post(f"/works/{w}/settings", json={
            "name": "三不渡", "description": "三铁律", "type_": "力量体系",
            "fields": {"cost": "破规左眼瞎"}}, headers=H)
        st = c.get(f"/works/{w}/settings", headers=H).json()
        assert next(s for s in st if s["name"] == "三不渡")["fields"]["cost"] == "破规左眼瞎"
        # 母题 CRUD
        c.post(f"/works/{w}/motifs", json={
            "name": "铜炉", "metaphor_unfolding": "万物为铜", "bound_theme": "弱肉强食",
            "material_echoes": ["长明灯"]}, headers=H)
        mo = c.get(f"/works/{w}/motifs", headers=H).json()
        assert mo[0]["name"] == "铜炉" and mo[0]["material_echoes"] == ["长明灯"]
    finally:
        app.dependency_overrides.clear()


def test_progressions_time_gated_injection(db):
    """W7 Progressions:人物状态只在生效章<=当前写作位置时注入(防剧透),乱世铜炉"信息延迟揭晓"。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    d.add_character(w, "渡叔", motivation="守渡")
    d.add_char_state(w, "渡叔", 1, "初到九原渡，守渡四十年")
    d.add_char_state(w, "渡叔", 5, "为护小满破规，左眼又瞎一分")
    for s in (1, 2, 3, 4, 5, 6):
        d.add_chapter(w, s, f"第{s}章")
    ctx3 = build_writing_context(d, w, 3)
    assert "守渡四十年" in ctx3, "seq1<=3 已生效应注入"
    assert "左眼又瞎" not in ctx3, "seq5>3 未来,防剧透"
    ctx6 = build_writing_context(d, w, 6)
    assert "左眼又瞎" in ctx6, "seq5<=6 已生效应注入"


def test_scene_appearances_from_segments(db):
    """W8 出场追踪:复用段落引用(已自动检测的 citation_refs)聚合实体出场章节(一份数据双用)。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    d.add_character(w, "渡叔")
    d.add_character(w, "小满")
    c1 = d.add_chapter(w, 1, "一")
    c2 = d.add_chapter(w, 2, "二")
    d.save_segments(w, c1, "渡叔立于船头。\n\n小满在岸边看着。")  # 两人都在第1章
    d.save_segments(w, c2, "渡叔独自摇橹过河。")               # 只渡叔在第2章
    assert d.entity_appearances(w, "渡叔") == [1, 2]
    assert d.entity_appearances(w, "小满") == [1]
    assert d.entity_appearances(w, "阿砚") == []


def test_rest_progressions(db):
    """Progressions:人物状态轨迹 REST(增/列),供前端编辑 + 防剧透注入。"""
    from fastapi.testclient import TestClient
    from scribe2.app import app, get_domain
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    c = TestClient(app); H = {"X-Owner-Id": "u1"}
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.post(f"/works/{w}/characters", json={"name": "渡叔"}, headers=H)
        r = c.post(f"/works/{w}/char-states", json={
            "character": "渡叔", "chapter_seq": 5, "state_desc": "左眼又瞎一分", "change_type": "replace"}, headers=H)
        assert r.json().get("state_id")
        st = c.get(f"/works/{w}/char-states?character=渡叔", headers=H).json()
        assert len(st) == 1 and st[0]["state_desc"] == "左眼又瞎一分" and st[0]["chapter_seq"] == 5
    finally:
        app.dependency_overrides.clear()


def test_foreshadow_echoes_and_overdue(db):
    """PlotThread:伏笔加中途强化 echoes + 超期告警(跨度太大未回收 → overdue)。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    fid = d.plant_foreshadow(w, "渡叔左眼的来历", 1, "high")
    d.add_foreshadow_echo(w, fid, 5)
    d.add_foreshadow_echo(w, fid, 12)
    for s in range(1, 30):
        d.add_chapter(w, s, f"第{s}章")
    fs = d.list_foreshadows_status(w)
    f = next(x for x in fs if "左眼" in x["summary"])
    assert f["echoes"] == [5, 12]
    assert f["overdue"] is True            # planted@1, max=29, 跨度28>阈值,未回收
    # 近埋的不超期
    d.plant_foreshadow(w, "近的伏笔", 28, "normal")
    f2 = next(x for x in d.list_foreshadows_status(w) if "近的" in x["summary"])
    assert f2["overdue"] is False


def test_extract_entities(db, monkeypatch):
    """AI 抽取:从正文抽候选设定(不落库,供审批)。"""
    from fastapi.testclient import TestClient
    import scribe2.app as appmod
    from scribe2.app import app, get_domain
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    c = TestClient(app); H = {"X-Owner-Id": "u1"}
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H)
        c.post(f"/works/{w}/chapters/1/prose", json={"content": "渡叔立于船头。"}, headers=H)
        monkeypatch.setattr(appmod, "_complete", lambda *a, **k:
            '{"characters":[{"name":"渡叔","motivation":"守渡"}],"settings":[{"name":"九原渡","type":"place"}],"foreshadows":[]}')
        r = c.post(f"/works/{w}/chapters/1/extract-entities", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["characters"][0]["name"] == "渡叔" and data["settings"][0]["name"] == "九原渡"
        # 抽取不落库(仍只是候选)
        assert len(d.list_characters(w)) == 0
    finally:
        app.dependency_overrides.clear()


def test_promise_thread_fields(db):
    """承诺线(Promise→Progress→Payoff):plant 带 promise/type,set_payoff 记回收章,status 全暴露。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 21):
        d.add_chapter(w, s, f"第{s}章")
    fid = d.plant_foreshadow(w, "渡叔的左眼", 1, "high",
                             promise="左眼藏着四十年前的命案", ftype="伏笔")
    d.add_foreshadow_echo(w, fid, 6)        # progress 进展
    d.set_foreshadow_payoff(w, fid, 18)     # payoff 回收于第18章
    f = next(x for x in d.list_foreshadows_status(w) if "左眼" in x["summary"])
    assert f["promise"] == "左眼藏着四十年前的命案"
    assert f["ftype"] == "伏笔"
    assert f["echoes"] == [6]
    assert f["payoff_chapter"] == 18
    assert f["state"] == "paid"
    assert f["overdue"] is False            # 已回收 → 不超期


def test_rest_promise_thread(db):
    """REST:plant 带 promise/ftype + payoff 端点 → status 暴露(前端时间线所依赖)。"""
    from fastapi.testclient import TestClient
    from scribe2.app import app, get_domain
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    c = TestClient(app); H = {"X-Owner-Id": "u1"}
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        for s in range(1, 21):
            c.put(f"/works/{w}/chapters", json={"seq": s, "title": f"第{s}章"}, headers=H)
        fid = c.post(f"/works/{w}/foreshadows",
                     json={"summary": "左眼", "chapter": 1, "promise": "藏着命案", "ftype": "悬念"},
                     headers=H).json()["foreshadow_id"]
        c.post(f"/works/{w}/foreshadows-status/{fid}/echo", json={"chapter": 6}, headers=H)
        r = c.post(f"/works/{w}/foreshadows-status/{fid}/payoff", json={"chapter": 18}, headers=H)
        assert r.status_code == 200 and r.json()["payoff_chapter"] == 18
        st = next(x for x in c.get(f"/works/{w}/foreshadows-status", headers=H).json() if "左眼" in x["summary"])
        assert st["promise"] == "藏着命案" and st["ftype"] == "悬念"
        assert st["payoff_chapter"] == 18 and st["state"] == "paid"
    finally:
        app.dependency_overrides.clear()


def test_writing_context_injects_open_promises(db):
    """开着的承诺线注入写作上下文,引导主编照顾走向/节奏;已回收的不再注入。"""
    from scribe2.writing import build_writing_context
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 21):
        d.add_chapter(w, s, f"第{s}章")
    d.plant_foreshadow(w, "渡叔的左眼", 1, promise="左眼藏着四十年前的命案", ftype="伏笔")
    paid = d.plant_foreshadow(w, "已回收的", 2, promise="不该出现", ftype="悬念")
    d.set_foreshadow_payoff(w, paid, 5)
    ctx = build_writing_context(d, w, 15)
    assert "承诺线" in ctx                       # 有承诺线块
    assert "左眼藏着四十年前的命案" in ctx        # 开着的承诺被注入
    assert "不该出现" not in ctx                 # 已回收的不再注入


def test_update_foreshadow_fields(db):
    """编辑承诺线明细:改 summary/promise/type(空值不覆盖)。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    fid = d.plant_foreshadow(w, "旧名", 1, promise="旧承诺", ftype="伏笔")
    d.update_foreshadow(w, fid, summary="新名", promise="新承诺", ftype="悬念")
    f = next(x for x in d.list_foreshadows_status(w) if x["summary"] == "新名")
    assert f["promise"] == "新承诺" and f["ftype"] == "悬念"
    # 空值不覆盖
    d.update_foreshadow(w, fid, promise="")
    f = next(x for x in d.list_foreshadows_status(w) if x["summary"] == "新名")
    assert f["promise"] == "新承诺"


def test_promise_rich_fields(db):
    """承诺线富字段:想要效果/读者是否预知/回收效果/关联实体。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    fid = d.plant_foreshadow(w, "左眼", 1, promise="藏命案", ftype="伏笔",
                             intended_effect="戏剧反讽", audience_knows=True,
                             payoff_effect="读者重读前文恍然", links=["渡叔"])
    f = next(x for x in d.list_foreshadows_status(w) if "左眼" in x["summary"])
    assert f["intended_effect"] == "戏剧反讽"
    assert f["audience_knows"] is True
    assert f["payoff_effect"] == "读者重读前文恍然"
    assert "渡叔" in f["links"]
    # update 也能改富字段
    d.update_foreshadow(w, fid, intended_effect="惊讶", links=["渡叔", "阿砚"])
    f = next(x for x in d.list_foreshadows_status(w) if "左眼" in x["summary"])
    assert f["intended_effect"] == "惊讶" and "阿砚" in f["links"]


def test_foreshadow_beats(db):
    """承诺线节点 beats:加 plant/reinforce/payoff 节点(带 guidance/subtlety/effect)+ 同步骨架。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 21):
        d.add_chapter(w, s, f"第{s}章")
    fid = d.plant_foreshadow(w, "左眼", 1)
    d.add_foreshadow_beat(w, fid, 6, "reinforce", guidance="第三次提及,渡叔回避", subtlety=2, effect="读者起疑")
    d.add_foreshadow_beat(w, fid, 18, "payoff", guidance="揭示四十年前命案", effect="读者恍然")
    f = next(x for x in d.list_foreshadows_status(w) if "左眼" in x["summary"])
    beats = f["beats"]
    assert any(b["kind"] == "reinforce" and b["chapter"] == 6
               and b["guidance"] == "第三次提及,渡叔回避" and b["subtlety"] == 2 for b in beats)
    assert any(b["kind"] == "payoff" and b["chapter"] == 18 for b in beats)
    # 骨架同步:reinforce→echoes,payoff→payoff_chapter+state
    assert 6 in f["echoes"]
    assert f["payoff_chapter"] == 18 and f["state"] == "paid"


def test_writing_context_node_instructions(db):
    """本章节点指令注入:落在本章的 beat 的 guidance + 效果/读者预知框架,引导主编具体怎么写。"""
    from scribe2.writing import build_writing_context
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 21):
        d.add_chapter(w, s, f"第{s}章")
    fid = d.plant_foreshadow(w, "左眼", 1, promise="藏命案", ftype="伏笔",
                             intended_effect="戏剧反讽", audience_knows=True, links=["渡叔"])
    d.add_foreshadow_beat(w, fid, 15, "reinforce", guidance="第三次提及,渡叔回避目光", effect="读者起疑")
    ctx = build_writing_context(d, w, 15)
    assert "第三次提及,渡叔回避目光" in ctx     # 本章节点 guidance 注入
    assert "本章承诺·节点指令" in ctx            # 有节点指令块
    assert "戏剧反讽" in ctx                       # 想要效果框架进了上下文
    assert "渡叔" in ctx                           # 关联实体


def test_relevant_characters(db):
    """角色相关性:开着的伏笔关联 + 近章梗概点名 的角色优先;无关角色不全塞;无信号回退全给。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 12):
        d.add_chapter(w, s, f"第{s}章")
    for nm in ["渡叔", "阿砚", "小满"] + [f"路人{i}" for i in range(10)]:  # 13 个,超阈值
        d.add_character(w, nm)
    d.save_chapter_memory(w, 10, "渡叔在渡口等一个人,夜色沉")     # 渡叔 近章点名
    d.plant_foreshadow(w, "阿砚身世", 1, links=["阿砚"])           # 阿砚 被开着的伏笔关联
    rel = [c["name"] for c in d.relevant_characters(w, 11)]
    assert "渡叔" in rel and "阿砚" in rel                          # 相关的进
    assert "路人5" not in rel                                        # 无关路人不塞
    assert len(rel) < 13                                             # 聚焦,非全塞


def test_writing_context_relevant_chars_only(db):
    """写作上下文只注入本章相关角色,不再全塞(无关路人不进上下文)。"""
    from scribe2.writing import build_writing_context
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 12):
        d.add_chapter(w, s, f"第{s}章")
    for nm in ["渡叔"] + [f"路人{i}" for i in range(10)]:
        d.add_character(w, nm)
    d.save_chapter_memory(w, 10, "渡叔在渡口等人")
    ctx = build_writing_context(d, w, 11)
    assert "渡叔" in ctx          # 相关角色注入
    assert "路人5" not in ctx     # 无关角色不注入(相关性生效)


def test_aliases_and_relations(db):
    """别名:近章用别名点名也算相关;关系打通:relations_of 取某实体的关系(喂图谱/详情)。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 12):
        d.add_chapter(w, s, f"第{s}章")
    d.add_character(w, "渡叔", aliases=["老渡", "摆渡的"])
    for i in range(8):
        d.add_character(w, f"路人{i}")
    d.save_chapter_memory(w, 10, "老渡又在渡口点灯")     # 用别名点名
    rel = [c["name"] for c in d.relevant_characters(w, 11)]
    assert "渡叔" in rel                                  # 别名"老渡"被识别→渡叔相关
    # 关系打通
    d.add_relation(w, "渡叔", "阿砚", "师徒")
    rs = d.relations_of(w, "渡叔")
    assert any(r.get("dst_entity") == "阿砚" and r.get("relation") == "师徒" for r in rs)


def test_pinned_always_relevant(db):
    """钉住(pin)的角色总在场:即便没近章点名/伏笔关联,也注入(写作台手动控制相关性)。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 12):
        d.add_chapter(w, s, f"第{s}章")
    for i in range(10):
        d.add_character(w, f"路人{i}")
    d.add_character(w, "主角")          # 最后建,fallback 截断会漏掉
    d.set_character_pin(w, "主角", True)
    names = [c["name"] for c in d.relevant_characters(w, 11)]
    assert "主角" in names              # 钉住的必在场
    assert len(names) < 11              # 触发聚焦,非全塞


def test_check_chapter_power_rules(db):
    """一致性检查纳入力量体系规则:代价/限制进 prompt + 专项指令,违背可被挑出。"""
    from scribe2.consistency import check_chapter
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    c = d.add_chapter(w, 1, "一")
    d.save_prose(w, c, "他破了规矩,却毫发无伤,左眼依旧明亮。")
    d.add_setting(w, "三不渡", "渡口规矩", type_="力量体系",
                  fields={"cost": "破规一次左眼瞎一分", "limitations": "不渡自寻死者", "trouble_it_causes": "招报应"})
    captured = {}
    def fake(prompt):
        captured["p"] = prompt
        return '{"flags":["破规却没付代价"]}'
    flags = check_chapter(d, w, 1, fake)
    assert "破规一次左眼瞎一分" in captured["p"]    # 力量体系代价进检查 prompt
    assert "代价" in captured["p"]                   # 专项指令存在
    assert "破规却没付代价" in flags


def test_agent_memory_by_work(db):
    """跨会话记忆按书隔离(主编记得'这本书'的偏好):list_agent_memory 按 work 过滤。"""
    d = domain_from(db); d.s.init_schema()
    w1 = d.create_work("书1"); w2 = d.create_work("书2")
    d.write_agent_memory("u1", w1, "pref", "tone", "冷峻克制")
    d.write_agent_memory("u1", w2, "pref", "tone", "热烈")
    mem = d.list_agent_memory("u1", work=w1)
    pairs = [(m.get("key"), m.get("value")) for m in mem]
    assert ("tone", "冷峻克制") in pairs
    assert ("tone", "热烈") not in pairs   # 别串到另一本书


def test_revise_prompt_targets_worst_dims():
    """重写 prompt:针对最差维给具体改写指令,且逼模型真改(不原样照抄)。"""
    from scribe2.critique import build_revise_prompt
    p = build_revise_prompt("原文…", {"worst_dims": ["surprise", "voice"], "issues": ["太顺", "书面腔"]})
    assert "反转" in p or "信息差" in p          # surprise 专项指令
    assert "口语" in p or "书面语" in p          # voice 专项指令
    assert "原样照抄" in p or "放手改写" in p     # 逼真改,别返回原文


def _scores(sc):
    return '{"scores":{"texture":%d,"surprise":%d,"emotion_truth":%d,"pace":%d,"voice":%d,"anti_slop":%d,"intent_resonance":%d,"coherence":%d},"issues":["太顺、不够具体"]}' % ((sc,) * 8)


def test_compare_parse():
    """成对比较 prompt/parse:返回 B_better/same/A_better。"""
    from scribe2.critique import build_compare_prompt, parse_compare
    p = build_compare_prompt("A正文", "B正文", ["surprise"])
    assert "verdict" in p and ("更好" in p or "哪个" in p)
    assert parse_compare('{"verdict":"B_better","why":"更具体"}') == "B_better"
    assert parse_compare('乱七八糟') == "same"      # 解析失败=保守判持平


def test_critique_revise_pairwise_keep(monkeypatch):
    """取优改成对比较:B 更好才采纳,否则退回原稿(不靠噪声绝对分)。"""
    from scribe2.critique import critique_revise
    def fake_up(prompt):
        if "verdict" in prompt:                       # compare prompt
            return '{"verdict":"B_better","why":"更具体有意外"}'
        if "顶尖文学编辑" in prompt:                   # revise prompt
            return "改好的正文"
        return _scores(4 if "改好的正文" in prompt else 3)   # critique
    r = critique_revise("原稿", "", fake_up, max_rounds=1)
    assert r["final"] == "改好的正文"                 # 成对判更好 → 采纳
    def fake_down(prompt):
        if "verdict" in prompt:
            return '{"verdict":"A_better","why":"丢了原优点"}'
        if "顶尖文学编辑" in prompt:
            return "改差的正文"
        return _scores(3)
    r2 = critique_revise("原稿", "", fake_down, max_rounds=1)
    assert r2["final"] == "原稿"                      # 成对判没更好 → 退回


def test_critique_revise_gate_on_issues(monkeypatch):
    """闸门看问题不看分:无具体问题就不重写(不被噪声分数逼着改)。"""
    from scribe2.critique import critique_revise
    def fake(prompt):
        if "顶尖文学编辑" in prompt:
            raise AssertionError("无问题不该触发重写")
        return '{"scores":{"texture":3,"surprise":3,"emotion_truth":3,"pace":3,"voice":3,"anti_slop":3,"intent_resonance":3,"coherence":3},"issues":[]}'
    r = critique_revise("原稿", "", fake, max_rounds=1)
    assert r["final"] == "原稿" and r["improved"] is False


def test_entity_beats_unified(db):
    """统一实体节点:角色/母题也有 beats(发展/复现),逐章注入「各线指令」给主编。"""
    from scribe2.writing import build_writing_context
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 21):
        d.add_chapter(w, s, f"第{s}章")
    d.add_character(w, "渡叔")
    d.add_entity_beat(w, "character", "渡叔", 15, kind="develop",
                      guidance="第三次质疑三不渡的执念", effect="弧光推进")
    d.add_motif(w, "铜炉")
    d.add_entity_beat(w, "motif", "铜炉", 15, kind="reinforce", guidance="织入一处人如炉中铜")
    beats = d.list_entity_beats(w, etype="character", entity="渡叔")
    assert any(b["chapter"] == 15 and "质疑三不渡" in b["guidance"] for b in beats)
    ctx = build_writing_context(d, w, 15)
    assert "各线指令" in ctx                          # 有统一的实体线指令块
    assert "第三次质疑三不渡的执念" in ctx              # 角色 beat guidance 注入
    assert "织入一处人如炉中铜" in ctx                  # 母题 beat 也注入


def test_entity_lines_health(db):
    """统一健康检测:各实体线 久未推进/未兑现=overdue,泛化伏笔的"看断线"到所有线。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    for s in range(1, 21):
        d.add_chapter(w, s, f"第{s}章")
    d.add_character(w, "渡叔")
    d.add_entity_beat(w, "character", "渡叔", 2, kind="develop", guidance="埋下执念")  # 久未推进、未兑现
    d.add_motif(w, "铜炉")
    d.add_entity_beat(w, "motif", "铜炉", 18, kind="reinforce", guidance="近期复现")    # 近期活跃
    h = d.entity_lines_health(w, span=10)
    du = next(x for x in h if x["entity"] == "渡叔")
    tl = next(x for x in h if x["entity"] == "铜炉")
    assert du["overdue"] is True and du["last_chapter"] == 2      # 埋ch2,max20,gap18>10,未兑现
    assert tl["overdue"] is False                                  # ch18 近期,不超期


def test_writing_injects_character_kernel(db):
    """角色内核 wound/lie/want/need 须注入写作上下文,否则主编写不出有弧光的人物(达不到乱世铜炉)。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书")
    d.add_chapter(w, 1, "一")
    d.add_character(w, "渡叔", motivation="守渡口", wound="独子溺亡于河", lie="渡人即赎罪", want="守住三不渡", need="放下亡子")
    ctx = build_writing_context(d, w, 1)
    assert "独子溺亡于河" in ctx   # wound
    assert "渡人即赎罪" in ctx     # lie
    assert "守住三不渡" in ctx     # want
    assert "放下亡子" in ctx       # need


def test_constraint_artifact_and_antisublime():
    """缺口:CONSTRAINT_BLOCK 无'法器三件套'硬规则、升华点题句未禁用(Phase4 critic 定位)。"""
    from scribe2.writing import constraint_block
    cb = constraint_block()
    assert "三件套" in cb and "专名" in cb          # 法器/道具三件套硬规则
    assert "再也" in cb or "升华尾句" in cb          # 升华点题句式禁用


def test_voice_samples_richer(db):
    """缺口:声音样本截到 2×22 字,腔调传不动;放宽到 ≥3 条、更长。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书"); d.add_chapter(w, 1, "一")
    d.add_character(w, "甲", voice_samples=[
        "死者为大,小的这是替您积德——顺手也给自己积点阴德,您多担待",
        "这位大爷您都凉透了,就别跟小的客气这二两碎银了",
        "娘,儿今儿又接了桩好买卖,您把心搁肚里安生睡"])
    ctx = build_writing_context(d, w, 1)
    assert "安生睡" in ctx   # 第3条样本须出现(旧版只取前2条→漏)


def test_exemplar_injected(db):
    """缺口:style_exemplar 表存在却从未注入;范文是学技法的唯一正面锚。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书"); d.add_chapter(w, 1, "一")
    d.add_exemplar(w, "胡先生眼珠四转,却不知在想些甚么。", technique="冷笔收尾、不点题")
    ctx = build_writing_context(d, w, 1)
    assert "范文" in ctx and "眼珠四转" in ctx and "冷笔收尾" in ctx


def test_find_repetitions():
    """缺口:生成后无跨段去重通道,模型长程复读无人拦(v3 同句重复5次)。确定性扫描。"""
    from scribe2.critique import find_repetitions
    t = ("怀里的铜丸烫得他心口发疼,他想扔回去。走了几步。"
         "怀里的铜丸烫得他心口发疼,他攥得更紧。又一段过场。"
         "怀里的铜丸烫得他心口发疼,终究没松手。")
    reps = find_repetitions(t, n=8, min_count=3)
    assert reps, "应检出重复"
    assert any("烫得他心口发疼" in r["phrase"] for r in reps)
    assert reps[0]["count"] >= 3


def test_dedup_prompt_lists_repeats():
    from scribe2.critique import build_dedup_prompt
    p = build_dedup_prompt("正文……", [{"phrase": "烫得他心口发疼", "count": 5}])
    assert "烫得他心口发疼" in p and ("重复" in p or "去重" in p)


def test_revise_dedup_guards_and_rewrites():
    from scribe2.critique import revise_dedup
    rep_text = "铜丸烫得他心口发疼。过场甲。铜丸烫得他心口发疼。过场乙。铜丸烫得他心口发疼。"
    # 正常改写
    out = revise_dedup(rep_text, lambda p: "改写后的不重复正文，足够长足够长足够长足够长足够长。", n=8, min_count=3)
    assert out["changed"] and out["reps"]
    # 守护:改写过短→弃用,返回原文
    out2 = revise_dedup(rep_text, lambda p: "太短", n=8, min_count=3)
    assert not out2["changed"] and out2["text"] == rep_text
    # 无重复→不动
    assert revise_dedup("一句正常的话。另一句不同的话。", lambda p: "", n=8, min_count=3)["changed"] is False


def test_settings_locked_and_fuller(db):
    """缺口gap7:关键设定截30字看不全既定里子→模型自行新编致属性漂移(ch2 尸丹配方前后打架)。
    锁定指令 + 放宽截断。"""
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("书"); d.add_chapter(w, 1, "一")
    d.add_setting(w, "井龙镇尸丹",
                  "极北玄铁混三百年尸气、七七四十九天炼成,刻井为狱专镇厉鬼魂魄;取丹者须继路否则反噬",
                  "物品")
    ctx = build_writing_context(d, w, 1)
    assert "既定" in ctx or "不得前后" in ctx          # 锁定指令
    assert "取丹者须继路" in ctx                        # 后半(30字会被截掉)须可见


def test_find_structural_repeats():
    """缺口gap9:去重只查字面n-gram,不查句式/节拍复读(ch3 排比泛滥+单字断行滥用)。"""
    from scribe2.critique import find_structural_repeats
    t = "他想起娘的眼。他想起爹的死。他想起那场瘟疫。他想起乱岗的尸。火。井。血。是她。又是火。"
    sr = find_structural_repeats(t, min_anaphora=3, max_short=3)
    assert any(x.get("kind") == "anaphora" and "他想起" in x["phrase"] for x in sr)  # 排比开头≥3
    assert any(x.get("kind") == "short" for x in sr)                                # 单字断句过多
