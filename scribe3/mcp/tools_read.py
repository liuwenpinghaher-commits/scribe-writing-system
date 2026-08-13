"""MCP tools — read surface (split from tools.py Phase C)."""
from __future__ import annotations



"""MCP s3_* tools (FastMCP decorators preserved)."""

from scribe3.mcp._common import *  # noqa: F403
from scribe3.mcp.gating import *  # noqa: F403

@mcp.tool(annotations=_RO)

def s3_project_frame(focalizer: str, chapter: int, work: str | None = None) -> list[dict]:
    """投影 focalizer 截至某章的知识帧(限知渲染的输入;帧外私密不在内)。"""
    fr = project_frame(_store_for(work), focalizer, chapter)
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute, "value": f.value,
             "is_secret": bool(f.secret)}
            for f in fr.facts]


def s3_find_leaks(prose: str, focalizer: str, chapter: int,
                  work: str | None = None) -> list[dict]:
    """兜底 POV 判官:扫散文里冒出的帧外私密破绽词。"""
    return [{"fact_id": x.fact_id, "marker": x.marker}
            for x in find_leaks_for_chapter(prose, _store_for(work), focalizer, chapter)]


def s3_causal_complete(chapter: int, work: str | None = None) -> list[dict]:
    """连贯性查询:每事件须因果入边+目标。返回违规列表(空=干净)。"""
    return [{"event": v.event_id, "reason": v.reason}
            for v in causal_complete(_store_for(work), chapter)]


def s3_setting_completeness(work: str | None = None) -> dict:
    """设定完整性检查:返回当前书缺少哪些设定维度(世界规则/势力/地点/角色深描/私密伏线)。
    主编据此引导作者补全设定。"""
    return _store_for(work).setting_completeness()


def s3_list_world_rules(category: str | None = None, work: str | None = None) -> list[dict]:
    """列世界规则(Sanderson 式:源头/能力/代价/限制/例外)。可按类别过滤。
    类别:magic/technology/social/physical/economic/political"""
    return _jsonable(_store_for(work).list_world_rules(category))


def _list_factions_impl(reveal_secret: bool, work: str | None) -> list[dict]:
    rows = _store_for(work).list_factions()
    result = []
    for row in rows:
        row = dict(row)
        for k in secret_capable_keys("faction"):
            is_secret = bool(row.get(secret_flag_key(k), False))
            row[k] = _mask_value(row.get(k) or "", is_secret, reveal_secret)
        result.append(row)
    return _jsonable(result)


def s3_list_factions(work: str | None = None) -> list[dict]:
    """列势力/组织(意识形态/领袖/已知成员/公开面目/起源/遗产运作等,CX-Task 3 起含
    codex_schema 注册的全部字段)。

    通用掩码(不硬编码字段名):按 codex_schema.secret_capable_keys('faction') 遍历,
    每个 `{key}_secret=True` 的字段恒显示 '🔒 私密',新增 secret 字段自动获得同款保护。
    本工具**没有** reveal_secret 参数(U-003 修复:能否解锁明文从"模型的参数"降格为
    "工具的名字",工具面白名单物理隔离,不再靠模型自律)。全知明文见孪生工具
    s3_list_factions_reveal。"""
    return _list_factions_impl(False, work)


def s3_list_factions_reveal(work: str | None = None) -> list[dict]:
    """s3_list_factions 的全知孪生:所有 secret_capable 字段返回明文(不掩码)。

    **仅供主编全知联查专用**,其输出严禁进入限知章续写 prompt。U-003 真机实测推翻了
    "只挂 scribe3_chief server"的旧设想——Hermes 的 server_label 不做过滤,主编对话与
    限知续写共用同一个网关进程(:8643),挂给任一 profile 就等于挂给了写作路径。
    **当前不挂载在任何网关**:两条路径的 profile include 白名单都不含这把工具,模型
    物理调不到(见 `_summarize_hermes_runtime` 的 `gateway_exposes_reveal_tools` 自检,
    钉死"任何 profile 的 include 都不得出现 *_reveal 工具"这条不变量)。要启用须另起
    一个**绝不服务写作/续写路径**的专用网关,而不是靠 label 隔离。"""
    return _list_factions_impl(True, work)


def s3_character_state(character_id: str, chapter: int, work: str | None = None) -> dict:
    """角色弧光状态查询:返回某角色在某章时刻的完整状态快照
    (能力/关系/性格阶段/弧光时间线)。动静结合:静态基石+动态演变。"""
    return _store_for(work).char_state_at(character_id, chapter)


def s3_character_timeline(character_id: str, work: str | None = None) -> list[dict]:
    """角色弧光时间线:列出该角色全部质变点(能力/关系/性格变化),按章排序。"""
    return _store_for(work).list_char_states(character_id)


def s3_relations_at(chapter: int, work: str | None = None) -> list[dict]:
    """某章有效的角色关系图(限知时间门:since_chapter <= chapter, until_chapter > chapter or NONE)。
    用于关系图可视化。"""
    return _store_for(work).relations_at(chapter)


def s3_get_voice_profile(character_id: str, work: str | None = None) -> dict:
    """获取角色声音指纹(9节:风格/口头禅/句式/用词/语气规则/独白风格/OOC信号/参考例句)。"""
    vp = _store_for(work).get_voice_profile(character_id)
    return vp or {}


def s3_check_ooc(character_id: str, dialogue: str, work: str | None = None) -> list[dict]:
    """OOC 检测:对照角色声音指纹的 ooc_signals 规则,检测对话是否违反角色声音。
    返回违规列表 [{signal, line, severity}]。"""
    return _store_for(work).check_ooc(character_id, dialogue)


def s3_list_items(state: str | None = None, work: str | None = None) -> list[dict]:
    """列物品/道具(含符号状态 active/lost/destroyed/unknown)。可按状态过滤。"""
    return _jsonable(_store_for(work).list_items(state))


def s3_list_terms(work: str | None = None) -> list[dict]:
    """列专有名词/术语(含别名)。"""
    return _jsonable(_store_for(work).list_terms())


def s3_resolve_entities(text: str, chapter: int = 9999, work: str | None = None) -> list[dict]:
    """解析文本中出现的实体引用(四路召回:精确名→别名→hint→向量语义)。
    返回相关设定候选 [{id, type, name, score, reason}]。"""
    return _store_for(work).resolve_entities(text, chapter)


def s3_validate_setting(chapter: int, prose: str, work: str | None = None) -> list[dict]:
    """设定校验:比对正文与设定圣经,产出冲突线索。
    覆盖:物品状态矛盾/OOC/规则违反。高精确率优先(宁漏不误)。"""
    return _store_for(work).validate_setting(chapter, prose)


def _dramatic_irony_impl(focalizer: str, chapter: int, reveal_secret: bool,
                         work: str | None) -> list[dict]:
    return [{"id": f.id,
            "value": _mask_value(f.value, bool(f.secret), reveal_secret),
            "is_secret": bool(f.secret)}
            for f in dramatic_irony(_store_for(work), focalizer, chapter)]


def s3_dramatic_irony(focalizer: str, chapter: int, work: str | None = None) -> list[dict]:
    """戏剧反讽点:读者已知、而视角角色不知的事实(KNOWS(reader,F)∧¬KNOWS(focal,F))。
    渲染该视角时据此写"角色安心、读者揪心"的张力(但角色台词只能用其帧内信息)。

    恒掩码私密命题的 value(显示 '🔒 私密'),is_secret 标志始终保留——本工具**没有**
    reveal_secret 参数(U-003 修复:能否解锁明文从"模型的参数"降格为"工具的名字",
    工具面白名单物理隔离,不再靠模型自律)。全知明文见孪生工具 s3_dramatic_irony_reveal。"""
    return _dramatic_irony_impl(focalizer, chapter, False, work)


def s3_dramatic_irony_reveal(focalizer: str, chapter: int,
                             work: str | None = None) -> list[dict]:
    """s3_dramatic_irony 的全知孪生:返回明文(secret 命题不掩码)。

    **仅供主编全知联查专用**,其输出严禁进入限知章续写 prompt。U-003 真机实测推翻了
    "只挂 scribe3_chief server"的旧设想——Hermes 的 server_label 不做过滤,主编对话与
    限知续写共用同一个网关进程(:8643),挂给任一 profile 就等于挂给了写作路径。
    **当前不挂载在任何网关**:两条路径的 profile include 白名单都不含这把工具,模型
    物理调不到(见 `_summarize_hermes_runtime` 的 `gateway_exposes_reveal_tools` 自检,
    钉死"任何 profile 的 include 都不得出现 *_reveal 工具"这条不变量)。要启用须另起
    一个**绝不服务写作/续写路径**的专用网关,而不是靠 label 隔离。"""
    return _dramatic_irony_impl(focalizer, chapter, True, work)


def s3_list_promises(work: str | None = None) -> list[dict]:
    """列伏笔(open/closed/abandoned + 埋/收章;含 kind=red_herring)。"""
    return _store_for(work).list_promises()


def s3_list_motifs(work: str | None = None) -> list[dict]:
    """列母题(名/绑定主题/物质回声/隐喻展开)——参照不透支。"""
    return _store_for(work).list_motifs()


def s3_get_chapter(seq: int, work: str | None = None) -> dict:
    """读某章（含场面合同，勿与 GATE 齐套混淆）。"""
    return _store_for(work).get_chapter(seq) or {}


@mcp.tool(annotations=_RO)
def s3_suggest_scene_contract(seq: int, work: str | None = None) -> dict:
    """只读场面建议：briefing + candidates + lock_warnings。persist 恒 false，无写权限。"""
    from scribe3.narrative_contract import load_scene_suggest
    sug = load_scene_suggest(_store_for(work), int(seq))
    sug["persist"] = False
    return sug


def s3_list_chapters(work: str | None = None) -> list[dict]:
    """列当前作品章节的序号、标题和结构元数据；建章前用于核实现状。"""
    return _jsonable(_store_for(work).list_chapters())


def s3_list_volumes(work: str | None = None) -> list[dict]:
    """列当前作品分卷的 ID、标题和排序；建章前用于选择可选卷归属。"""
    return _jsonable(_store_for(work).list_volumes())


def s3_move_retrieve(benyi: str, move_id: str | None = None, work: str | None = None) -> dict:
    """按本意或俗名取一张已批招式卡（三角/羁绊/一字/话死/延宕）。不读散文召回。"""
    from scribe3.story_move import retrieve_story_move
    hits = retrieve_story_move(benyi or "", move_id=move_id)
    return {"cards": hits[:1], "count": len(hits[:1])}


def s3_skill_read(slug: str, work: str | None = None) -> str:
    """读一篇通用写作技法全文(P1 渐进披露:instructions 只带索引行,触及才取全文)。
    slug 见 instructions 的「写作技法库」索引;未知 slug 抛错并列出可用清单(fail-loud)。"""
    from scribe3.craft_skills import read_skill
    return read_skill(slug)


def s3_qc_chapter(seq: int, work: str | None = None) -> dict:
    """对某章正文跑确定性 QC(复读/排比/升华/AI腔)——渲染层兜底。
    升华检测叠加本书题材正则(craft_rule purple_regex)。"""
    from scribe3.critique import quality_flags
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch:
        return {}
    extra = st.purple_patterns() if hasattr(st, "purple_patterns") else None
    return quality_flags(ch["prose"], extra_patterns=extra)


def s3_recent_phrases(chapter: int, lookback: int = 3, top: int = 40,
                      work: str | None = None) -> dict:
    """【写本章前必调】返回前 lookback 章已用过的独特措辞/意象短语清单——生成时**逐字避开**。

    根因:单遍长程生成的"复读病"——模型跨章自然复用自己偏爱的句式/意象(实测第2章逐字搬运
    第1章 14 个 ≥8 字短语,如「胡不为惨叫一声」「嗡鸣声越来越响」「要从嗓子眼里蹦出来」),
    而逐章 QC 只扫单章查不到。把前文招式喂进 prompt,在【生成时】就换一种写法,而非事后再删。
    返回 {avoid: [短语...]}。本章动笔前调用,把 avoid 当"已用过、本章另寻表达"的硬约束。"""
    from scribe3.critique import distinctive_phrases
    priors = _store_for(work).recent_proses(chapter, k=lookback)
    avoid: list[str] = []
    seen: set[str] = set()
    for c in priors:
        for p in distinctive_phrases(c.get("prose", ""), n=8, top=top):
            if p not in seen:
                seen.add(p)
                avoid.append(p)
    return {"avoid": avoid[: top * lookback], "from_chapters": [c["seq"] for c in priors]}


def s3_cross_repetition(seq: int, lookback: int = 8, work: str | None = None) -> dict:
    """某章 vs 前 lookback 章的【跨章逐字复读】(≥8字重叠,剔母题/专名)。逐章 QC 的盲区,长程一致性硬指标。
    返回 {count, phrases:[{phrase, prior_chapters}]};count>0 即本章有跨章搬运,调 s3_dedup_cross 改写。"""
    from scribe3.critique import find_cross_chapter_repetitions
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch:
        return {"count": 0, "phrases": []}
    allow = st.motif_terms() if hasattr(st, "motif_terms") else None
    priors = [c["prose"] for c in st.recent_proses(seq, k=lookback) if c.get("prose")]
    hits = find_cross_chapter_repetitions(ch.get("prose", ""), priors, n=8, allow=allow)
    return {"count": len(hits), "phrases": hits[:20]}


def s3_dedup_cross(seq: int, lookback: int = 8, work: str | None = None) -> dict:
    """【QC治层】确定性事后跨章改写:定位本章含跨章逐字复读的句子→定向 LLM 改写→返回新正文。

    比'prompt 预防'可靠(实测最严重章跨章复读 30→8,↓73%),契合本系统'确定性扫描+定向改'纪律。
    返回 {prose, rewritten, before, after};rewritten>0 时用 s3_save_chapter(seq, prose) 存回。
    幂等:无复读则原样返回、不调 LLM。"""
    from scribe3.critique import rewrite_cross_repetitions
    from scribe3.llm import hermes_complete
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"prose": "", "rewritten": 0, "before": 0, "after": 0}
    allow = st.motif_terms() if hasattr(st, "motif_terms") else None
    priors = [c["prose"] for c in st.recent_proses(seq, k=lookback) if c.get("prose")]
    return rewrite_cross_repetitions(ch["prose"], priors, hermes_complete, n=8, allow=allow)


def s3_emotion_palette(emotion: str = "") -> list | dict:
    """情感词典(引擎层,题材无关):空参返回15种情感名;带参返回该情感的身体信号/内部感觉。
    渲染某情感时查取 2-3 个身体信号编织进叙述(show 不 tell 的命门)。"""
    from scribe3.craft import PALETTE
    if not emotion:
        return list(PALETTE)
    return PALETTE.get(emotion, {})


def s3_craft_rule_list(work: str | None = None) -> list[dict]:
    """列本书题材层 craft 规则(升华正则/法器写法/角色覆盖动作)。"""
    return _store_for(work).list_craft_rules()


def s3_discipline_check(seq: int, brief: str = "", work: str | None = None) -> dict:
    """LLM 纪律判官(走 Hermes):判本章 双高潮/声音崩/解说倾泻(确定性检测的盲区)。
    返回 {ok, violations, cut_after, changed, text(若可截)};不自动写,作者/主编决定是否应用。"""
    from scribe3.critique import discipline_truncate
    from scribe3.llm import hermes_complete
    ch = _store_for(work).get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"ok": True, "violations": []}
    return discipline_truncate(ch["prose"], brief, hermes_complete)


def s3_get_intent(work: str | None = None) -> dict:
    """读取本书北极星意图(读者感受/情感弧/红线/字数目标)。只读。"""
    return _store_for(work).get_intent()


def s3_list_entity_relations(entity: str | None = None, chapter: int | None = None,
                             work: str | None = None) -> list[dict]:
    """列通用实体关系(双方认知 perception_a/perception_b + 主编独知 truth,任意实体
    类型,如 "faction:衔尾蛇秘会"/"role:焦三"/"item:碎片")。entity 给定则只看涉及该
    实体的关系(a 或 b 命中);chapter 给定则按时态过滤(仿 s3_relations_at)。

    truth 按 truth_secret 恒掩码(显示 '🔒 私密')。本工具**没有** reveal_secret 参数
    (U-003 修复:能否解锁明文从"模型的参数"降格为"工具的名字",工具面白名单物理隔离,
    不再靠模型自律)。全知明文见孪生工具 s3_list_entity_relations_reveal。"""
    return _list_entity_relations_impl(entity, chapter, False, work)


def s3_list_entity_relations_reveal(entity: str | None = None, chapter: int | None = None,
                                    work: str | None = None) -> list[dict]:
    """s3_list_entity_relations 的全知孪生:truth 字段返回明文(不掩码)。

    **仅供主编全知联查专用**,其输出严禁进入限知章续写 prompt。U-003 真机实测推翻了
    "只挂 scribe3_chief server"的旧设想——Hermes 的 server_label 不做过滤,主编对话与
    限知续写共用同一个网关进程(:8643),挂给任一 profile 就等于挂给了写作路径。
    **当前不挂载在任何网关**:两条路径的 profile include 白名单都不含这把工具,模型
    物理调不到(见 `_summarize_hermes_runtime` 的 `gateway_exposes_reveal_tools` 自检,
    钉死"任何 profile 的 include 都不得出现 *_reveal 工具"这条不变量)。要启用须另起
    一个**绝不服务写作/续写路径**的专用网关,而不是靠 label 隔离。"""
    return _list_entity_relations_impl(entity, chapter, True, work)


def s3_list_voice_flags(status: str = "open", work: str | None = None) -> list[dict]:
    """列声音演变 flag(默认 open;读,放行)。
    flag 由 ingest/add_char_state 在 affects_voice=True 时自动创建;
    取到的 id 供 s3_resolve_voice_flag / s3_fold_voice_flags 消化(补 P1-13 文档断链)。"""
    return _store_for(work).list_voice_flags(status)


def s3_promise_timeline(promise_id: str, work: str | None = None) -> dict:
    """读单条伏笔时间线(setup/clue/touch/closed/abandoned 按章排序)。只读放行。"""
    pid = (promise_id or "").strip()
    if not pid:
        return {"error": "promise_id required"}
    tl = _store_for(work).promise_timeline(pid)
    if tl is None:
        return {"error": f"promise '{pid}' 不存在"}
    return tl

