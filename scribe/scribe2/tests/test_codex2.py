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
