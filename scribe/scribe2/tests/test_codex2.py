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
