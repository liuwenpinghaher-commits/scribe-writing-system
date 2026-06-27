"""scribe3 领域 MCP server(FastMCP,名 "scribe3")。

读工具放行(readOnlyHint);写工具经 Hermes elicitation 待批,批准后才走 store 单点落库。
工具名带 s3_ 前缀(隔离标准:与 scribe2 同挂也不撞名)。
可测核心 = commit_if_approved 门控;elicitation 是生产侧(ctx.elicit,fail-closed)。
"""
from __future__ import annotations

from typing import Callable

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from scribe3.knowledge import dramatic_irony, project_frame
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge
from scribe3.verify import causal_complete, find_leaks

mcp = FastMCP("scribe3")
_store = None


def set_store(s) -> None:
    global _store
    _store = s


# ===== 写门控 =====
WRITE_GATED = {"s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge",
                "s3_plant_promise", "s3_advance_promise", "s3_craft_rule_add",
                "s3_craft_rule_remove", "s3_add_character_relation",
                "s3_add_world_rule", "s3_add_faction", "s3_add_char_state",
                "s3_set_voice_profile", "s3_add_item", "s3_add_term"}


def requires_approval(name: str) -> bool:
    return name in WRITE_GATED


def commit_if_approved(name: str, accepted: bool, do_write: Callable[[], None]) -> dict:
    """写门控单一落库点:WRITE_GATED 的工具须 accepted=True 才执行 do_write
    (do_write 内部走 store.execute_write 单点)。拒绝=fail-closed 不写。"""
    if name in WRITE_GATED and not accepted:
        return {"status": "declined", "tool": name}
    do_write()
    return {"status": "written", "tool": name}


class _Approve(BaseModel):
    confirm: bool = True


async def _ask(ctx: Context, summary: str) -> bool:
    """Hermes elicitation:写前向用户征求批准。异常/超时 → fail-closed(不写)。"""
    try:
        res = await ctx.elicit(message=f"批准写入?{summary}", schema=_Approve)
        return getattr(res, "action", None) == "accept"
    except Exception:
        return False


_RO = ToolAnnotations(readOnlyHint=True)
_RW = ToolAnnotations(readOnlyHint=False)


# ===== 读工具(放行)=====
@mcp.tool(annotations=_RO)
def s3_project_frame(focalizer: str, chapter: int) -> list[dict]:
    """投影 focalizer 截至某章的知识帧(限知渲染的输入;帧外私密不在内)。"""
    fr = project_frame(_store, focalizer, chapter)
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute, "value": f.value,
             "is_secret": bool(f.secret)}
            for f in fr.facts]


@mcp.tool(annotations=_RO)
def s3_find_leaks(prose: str, focalizer: str, chapter: int) -> list[dict]:
    """兜底 POV 判官:扫散文里冒出的帧外私密破绽词。"""
    return [{"fact_id": x.fact_id, "marker": x.marker}
            for x in find_leaks(prose, _store, focalizer, chapter)]


@mcp.tool(annotations=_RO)
def s3_causal_complete(chapter: int) -> list[dict]:
    """连贯性查询:每事件须因果入边+目标。返回违规列表(空=干净)。"""
    return [{"event": v.event_id, "reason": v.reason} for v in causal_complete(_store, chapter)]


@mcp.tool(annotations=_RO)
def s3_semantic_recall(query: str, k: int = 5) -> list[dict]:
    """语义召回最相关的设定/命题(向量 RAG,非字面匹配;头部工具仍多用字面,这是差异化)。"""
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute, "value": f.value,
             "is_secret": bool(f.secret)}
            for f in _store.semantic_recall(query, k)]


@mcp.tool(annotations=_RO)
def s3_hybrid_recall(query: str, chapter: int, k: int = 5) -> list[dict]:
    """混合召回:向量语义 + 中文关键词 → RRF 融合排名。
    比纯向量召回多关键词路(专名/法器名精确匹配),叠加限知时间门。"""
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute, "value": f.value,
             "is_secret": bool(f.secret)}
            for f in _store.hybrid_recall(query, chapter, k)]


@mcp.tool(annotations=_RO)
def s3_chapter_recall(query: str, k: int = 5) -> list[dict]:
    """章节语义召回:按标题+正文匹配语义最接近的章(向量 RAG)。
    用来查'与哪章描写接近'、'某主题首次出现在哪章'等。"""
    return _store.chapter_recall(query, k)


@mcp.tool(annotations=_RO)
def s3_graph_recall(query: str, chapter: int, k: int = 5) -> list[dict]:
    """Graph RAG 召回:语义相关命题 + 其知识子图(谁知道/来源事件/同场角色)。
    叠加章时间门(限知)。供主编全知联查,不喂限知渲染。"""
    results = _store.graph_recall(query, chapter, k)
    for item in results:
        if "is_secret" not in item:
            item["is_secret"] = bool(item.get("secret", False))
    return results


@mcp.tool(annotations=_RO)
def s3_setting_completeness() -> dict:
    """设定完整性检查:返回当前书缺少哪些设定维度(世界规则/势力/地点/角色深描/私密伏线)。
    主编据此引导作者补全设定。"""
    return _store.setting_completeness()


@mcp.tool(annotations=_RO)
def s3_list_world_rules(category: str | None = None) -> list[dict]:
    """列世界规则(Sanderson 式:源头/能力/代价/限制/例外)。可按类别过滤。
    类别:magic/technology/social/physical/economic/political"""
    return _store.list_world_rules(category)


@mcp.tool(annotations=_RO)
def s3_list_factions() -> list[dict]:
    """列势力/组织(意识形态/领袖/已知成员/公开面目/私下运作)。"""
    return _store.list_factions()


@mcp.tool(annotations=_RO)
def s3_character_state(character_id: str, chapter: int) -> dict:
    """角色弧光状态查询:返回某角色在某章时刻的完整状态快照
    (能力/关系/性格阶段/弧光时间线)。动静结合:静态基石+动态演变。"""
    return _store.char_state_at(character_id, chapter)


@mcp.tool(annotations=_RO)
def s3_character_timeline(character_id: str) -> list[dict]:
    """角色弧光时间线:列出该角色全部质变点(能力/关系/性格变化),按章排序。"""
    return _store.list_char_states(character_id)


@mcp.tool(annotations=_RO)
def s3_relations_at(chapter: int) -> list[dict]:
    """某章有效的角色关系图(限知时间门:since_chapter <= chapter, until_chapter > chapter or NONE)。
    用于关系图可视化。"""
    return _store.relations_at(chapter)


@mcp.tool(annotations=_RO)
def s3_get_voice_profile(character_id: str) -> dict:
    """获取角色声音指纹(9节:风格/口头禅/句式/用词/语气规则/独白风格/OOC信号/参考例句)。"""
    vp = _store.get_voice_profile(character_id)
    return vp or {}


@mcp.tool(annotations=_RO)
def s3_check_ooc(character_id: str, dialogue: str) -> list[dict]:
    """OOC 检测:对照角色声音指纹的 ooc_signals 规则,检测对话是否违反角色声音。
    返回违规列表 [{signal, line, severity}]。"""
    return _store.check_ooc(character_id, dialogue)


@mcp.tool(annotations=_RO)
def s3_list_items(state: str | None = None) -> list[dict]:
    """列物品/道具(含符号状态 active/lost/destroyed/unknown)。可按状态过滤。"""
    return _store.list_items(state)


@mcp.tool(annotations=_RO)
def s3_list_terms() -> list[dict]:
    """列专有名词/术语(含别名)。"""
    return _store.list_terms()


@mcp.tool(annotations=_RO)
def s3_resolve_entities(text: str, chapter: int = 9999) -> list[dict]:
    """解析文本中出现的实体引用(四路召回:精确名→别名→hint→向量语义)。
    返回相关设定候选 [{id, type, name, score, reason}]。"""
    return _store.resolve_entities(text, chapter)


@mcp.tool(annotations=_RO)
def s3_validate_setting(chapter: int, prose: str) -> list[dict]:
    """设定校验:比对正文与设定圣经,产出冲突线索。
    覆盖:物品状态矛盾/OOC/规则违反。高精确率优先(宁漏不误)。"""
    return _store.validate_setting(chapter, prose)


@mcp.tool(annotations=_RO)
def s3_dramatic_irony(focalizer: str, chapter: int) -> list[dict]:
    """戏剧反讽点:读者已知、而视角角色不知的事实(KNOWS(reader,F)∧¬KNOWS(focal,F))。
    渲染该视角时据此写"角色安心、读者揪心"的张力(但角色台词只能用其帧内信息)。"""
    return [{"id": f.id, "value": f.value, "is_secret": bool(f.secret)}
            for f in dramatic_irony(_store, focalizer, chapter)]


@mcp.tool(annotations=_RO)
def s3_list_promises() -> list[dict]:
    """列伏笔(open/closed + 埋/收章)。"""
    return _store.list_promises()


@mcp.tool(annotations=_RO)
def s3_list_motifs() -> list[dict]:
    """列母题(名/绑定主题/物质回声/隐喻展开)——参照不透支。"""
    return _store.list_motifs()


@mcp.tool(annotations=_RO)
def s3_get_chapter(seq: int) -> dict:
    """读某章正文(manuscript)。"""
    return _store.get_chapter(seq) or {}


@mcp.tool(annotations=_RO)
def s3_qc_chapter(seq: int) -> dict:
    """对某章正文跑确定性 QC(复读/排比/升华/AI腔)——渲染层兜底。
    升华检测叠加本书题材正则(craft_rule purple_regex)。"""
    from scribe3.critique import quality_flags
    ch = _store.get_chapter(seq)
    if not ch:
        return {}
    extra = _store.purple_patterns() if hasattr(_store, "purple_patterns") else None
    return quality_flags(ch["prose"], extra_patterns=extra)


@mcp.tool(annotations=_RO)
def s3_recent_phrases(chapter: int, lookback: int = 3, top: int = 40) -> dict:
    """【写本章前必调】返回前 lookback 章已用过的独特措辞/意象短语清单——生成时**逐字避开**。

    根因:单遍长程生成的"复读病"——模型跨章自然复用自己偏爱的句式/意象(实测第2章逐字搬运
    第1章 14 个 ≥8 字短语,如「胡不为惨叫一声」「嗡鸣声越来越响」「要从嗓子眼里蹦出来」),
    而逐章 QC 只扫单章查不到。把前文招式喂进 prompt,在【生成时】就换一种写法,而非事后再删。
    返回 {avoid: [短语...]}。本章动笔前调用,把 avoid 当"已用过、本章另寻表达"的硬约束。"""
    from scribe3.critique import distinctive_phrases
    priors = _store.recent_proses(chapter, k=lookback)
    avoid: list[str] = []
    seen: set[str] = set()
    for c in priors:
        for p in distinctive_phrases(c.get("prose", ""), n=8, top=top):
            if p not in seen:
                seen.add(p)
                avoid.append(p)
    return {"avoid": avoid[: top * lookback], "from_chapters": [c["seq"] for c in priors]}


@mcp.tool(annotations=_RO)
def s3_cross_repetition(seq: int, lookback: int = 8) -> dict:
    """某章 vs 前 lookback 章的【跨章逐字复读】(≥8字重叠,剔母题/专名)。逐章 QC 的盲区,长程一致性硬指标。
    返回 {count, phrases:[{phrase, prior_chapters}]};count>0 即本章有跨章搬运,调 s3_dedup_cross 改写。"""
    from scribe3.critique import find_cross_chapter_repetitions
    ch = _store.get_chapter(seq)
    if not ch:
        return {"count": 0, "phrases": []}
    allow = _store.motif_terms() if hasattr(_store, "motif_terms") else None
    priors = [c["prose"] for c in _store.recent_proses(seq, k=lookback) if c.get("prose")]
    hits = find_cross_chapter_repetitions(ch.get("prose", ""), priors, n=8, allow=allow)
    return {"count": len(hits), "phrases": hits[:20]}


@mcp.tool(annotations=_RO)
def s3_dedup_cross(seq: int, lookback: int = 8) -> dict:
    """【QC治层】确定性事后跨章改写:定位本章含跨章逐字复读的句子→定向 LLM 改写→返回新正文。

    比'prompt 预防'可靠(实测最严重章跨章复读 30→8,↓73%),契合本系统'确定性扫描+定向改'纪律。
    返回 {prose, rewritten, before, after};rewritten>0 时用 s3_save_chapter(seq, prose) 存回。
    幂等:无复读则原样返回、不调 LLM。"""
    from scribe3.critique import rewrite_cross_repetitions
    from scribe3.llm import hermes_complete
    ch = _store.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"prose": "", "rewritten": 0, "before": 0, "after": 0}
    allow = _store.motif_terms() if hasattr(_store, "motif_terms") else None
    priors = [c["prose"] for c in _store.recent_proses(seq, k=lookback) if c.get("prose")]
    return rewrite_cross_repetitions(ch["prose"], priors, hermes_complete, n=8, allow=allow)


@mcp.tool(annotations=_RO)
def s3_emotion_palette(emotion: str = "") -> list | dict:
    """情感词典(引擎层,题材无关):空参返回15种情感名;带参返回该情感的身体信号/内部感觉。
    渲染某情感时查取 2-3 个身体信号编织进叙述(show 不 tell 的命门)。"""
    from scribe3.craft import PALETTE
    if not emotion:
        return list(PALETTE)
    return PALETTE.get(emotion, {})


@mcp.tool(annotations=_RO)
def s3_craft_rule_list() -> list[dict]:
    """列本书题材层 craft 规则(升华正则/法器写法/角色覆盖动作)。"""
    return _store.list_craft_rules()


@mcp.tool(annotations=_RO)
def s3_discipline_check(seq: int, brief: str = "") -> dict:
    """LLM 纪律判官(走 Hermes):判本章 双高潮/声音崩/解说倾泻(确定性检测的盲区)。
    返回 {ok, violations, cut_after, changed, text(若可截)};不自动写,作者/主编决定是否应用。"""
    from scribe3.critique import discipline_truncate
    from scribe3.llm import hermes_complete
    ch = _store.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"ok": True, "violations": []}
    return discipline_truncate(ch["prose"], brief, hermes_complete)


# ===== manuscript 写(草稿,直接写,不待批——非世界状态)=====
@mcp.tool(annotations=_RW)
def s3_save_chapter(seq: int, prose: str, title: str = "", focalizer: str | None = None) -> dict:
    """落/覆盖某章正文(作者草稿,不经 elicitation;manuscript 非世界状态)。"""
    _store.save_chapter(seq, prose, title=title, focalizer=focalizer)
    return {"status": "saved", "seq": seq}


# ===== 写工具(elicitation 待批 → store 单点)=====
@mcp.tool(annotations=_RW)
async def s3_add_character(ctx: Context, oid: str, name: str) -> dict:
    """新增角色(写,待批)。"""
    ok = await _ask(ctx, f"新增角色 {oid}={name}")
    return commit_if_approved("s3_add_character", ok,
                              lambda: _store.add_entity(Entity(oid, "character", name)))


@mcp.tool(annotations=_RW)
async def s3_add_fact(ctx: Context, oid: str, entity: str, attribute: str, value: str,
                      valid_from: int, secret: bool = False) -> dict:
    """新增事实/状态@章(写,待批)。secret=True 标私密(泄露=穿帮)。"""
    ok = await _ask(ctx, f"新增事实 {oid}:{entity}·{attribute}={value}")

    def _write():
        _store.add_fact(Fact(oid, entity, attribute, value, valid_from, secret=secret))
        _store.semantic_index(oid, value)   # 写时建语义索引(设定即写即可召回)
    return commit_if_approved("s3_add_fact", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_add_event(ctx: Context, oid: str, etype: str, valid_from: int,
                       motivated_by_goal: str | None = None) -> dict:
    """新增事件(写,待批)。"""
    ok = await _ask(ctx, f"新增事件 {oid}:{etype}")
    return commit_if_approved("s3_add_event", ok,
                              lambda: _store.add_event(Event(oid, etype, story_time=valid_from,
                                                             motivated_by_goal=motivated_by_goal)))


@mcp.tool(annotations=_RW)
async def s3_add_character_relation(ctx: Context, src_oid: str, dst_oid: str,
                                     relation: str, since_chapter: int,
                                     note: str | None = None) -> dict:
    """添加角色关系(写,待批)。relation: ally/enemy/kin/master_disciple/lover"""
    ok = await _ask(ctx, f"添加角色关系 {src_oid}→{dst_oid} [{relation}](章{since_chapter})")
    return commit_if_approved("s3_add_character_relation", ok,
                              lambda: _store.add_character_relation(
                                  src_oid, dst_oid, relation, since_chapter, note))


@mcp.tool(annotations=_RW)
async def s3_add_world_rule(ctx: Context, name: str, category: str,
                             source: str | None = None,
                             capabilities: list | None = None,
                             cost: str | None = None,
                             limitations: list | None = None,
                             exceptions: list | None = None,
                             scope: str = "global",
                             established_chapter: int | None = None,
                             note: str | None = None) -> dict:
    """添加世界规则(写,待批)。Sanderson 式:源头/能力/代价/限制/例外。
    category: magic/technology/social/physical/economic/political"""
    ok = await _ask(ctx, f"添加世界规则 [{category}] {name}")
    return commit_if_approved("s3_add_world_rule", ok,
                              lambda: _store.add_world_rule(
                                  name, category, source, capabilities, cost,
                                  limitations, exceptions, scope, established_chapter, note))


@mcp.tool(annotations=_RW)
async def s3_add_faction(ctx: Context, name: str,
                          ideology: str | None = None,
                          leader: str | None = None,
                          known_members: list | None = None,
                          public_face: str | None = None,
                          private_operation: str | None = None,
                          first_mention_chapter: int | None = None) -> dict:
    """添加势力/组织(写,待批)。含公开面目和私下运作。"""
    ok = await _ask(ctx, f"添加势力 {name}")
    return commit_if_approved("s3_add_faction", ok,
                              lambda: _store.add_faction(
                                  name, ideology, "active", leader, known_members,
                                  public_face, private_operation, first_mention_chapter))


@mcp.tool(annotations=_RW)
async def s3_add_char_state(ctx: Context, character_id: str, chapter: int,
                             change_type: str, summary: str,
                             trigger_event: str | None = None,
                             arc_phase: str | None = None,
                             affects_voice: bool | None = None) -> dict:
    """记录角色弧光质变点(写,待批)。change_type: ability/relation/personality/composite。
    动静结合:静态基石不变,动态演变记录在此。"""
    ok = await _ask(ctx, f"记录弧光 {character_id} 第{chapter}章 [{change_type}]: {summary[:30]}")
    return commit_if_approved("s3_add_char_state", ok,
                              lambda: _store.add_char_state(
                                  character_id, chapter, change_type, summary,
                                  trigger_event=trigger_event, arc_phase=arc_phase,
                                  affects_voice=affects_voice))


@mcp.tool(annotations=_RW)
async def s3_set_voice_profile(ctx: Context, character_id: str,
                                style_summary: str,
                                catchphrases: list | None = None,
                                tone_rules: list | None = None,
                                ooc_signals: list | None = None) -> dict:
    """设置角色声音指纹(写,待批)。9节结构,至少提供 style_summary。
    ooc_signals: [{signal_id, description, detection_method, severity}] 可检测的 OOC 规则。"""
    ok = await _ask(ctx, f"设置声音指纹 {character_id}")
    profile = {"style_summary": style_summary, "catchphrases": catchphrases,
               "tone_rules": tone_rules, "ooc_signals": ooc_signals, "version": 1}
    return commit_if_approved("s3_set_voice_profile", ok,
                              lambda: _store.set_voice_profile(character_id, profile))


@mcp.tool(annotations=_RW)
async def s3_add_item(ctx: Context, name: str,
                       category: str | None = None,
                       description: str | None = None,
                       current_owner: str | None = None,
                       symbolic_state: str = "active",
                       special_properties: list | None = None) -> dict:
    """添加物品/道具(写,待批)。symbolic_state: active/lost/destroyed/unknown。"""
    ok = await _ask(ctx, f"添加物品 {name} [{symbolic_state}]")
    return commit_if_approved("s3_add_item", ok,
                              lambda: _store.add_item(name, category, description,
                                  current_owner, symbolic_state, special_properties))


@mcp.tool(annotations=_RW)
async def s3_add_term(ctx: Context, name: str,
                       category: str | None = None,
                       definition: str | None = None,
                       aliases: list | None = None) -> dict:
    """添加专有名词/术语(写,待批)。含别名列表。"""
    ok = await _ask(ctx, f"添加术语 {name}")
    return commit_if_approved("s3_add_term", ok,
                              lambda: _store.add_term(name, category, definition, aliases))


@mcp.tool(annotations=_RW)
async def s3_plant_promise(ctx: Context, text: str, setup_chapter: int,
                           kind: str = "promise") -> dict:
    """埋伏笔(写,待批)。kind=promise/red_herring。"""
    ok = await _ask(ctx, f"埋伏笔(第{setup_chapter}章):{text}")
    return commit_if_approved("s3_plant_promise", ok,
                              lambda: _store.plant_promise(text, setup_chapter, kind=kind))


@mcp.tool(annotations=_RW)
async def s3_advance_promise(ctx: Context, pid: str, payoff_chapter: int) -> dict:
    """回收伏笔(写,待批)。"""
    ok = await _ask(ctx, f"回收伏笔 {pid}(第{payoff_chapter}章)")
    return commit_if_approved("s3_advance_promise", ok,
                              lambda: _store.advance_promise(pid, payoff_chapter))


@mcp.tool(annotations=_RW)
def s3_ingest_chapter(seq: int) -> dict:
    """章节回写(客观回写,不待批):读定稿抽"谁新知道什么/做了什么"→更新知识账本。
    非创作虚构(add_fact/add_event 那些经 elicitation);ingest 反映已定稿正文,
    后端 save-chapter 也会自动后台跑同一逻辑。"""
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    return ingest_chapter(_store, seq, hermes_complete)


@mcp.tool(annotations=_RW)
async def s3_record_knowledge(ctx: Context, knower: str, proposition: str,
                              since_chapter: int, acquired_via: str = "saw") -> dict:
    """记知识边:某角色某章获知某命题(写,待批)。"""
    ok = await _ask(ctx, f"记知识 {knower} 知道 {proposition}(章{since_chapter})")
    return commit_if_approved("s3_record_knowledge", ok,
                              lambda: _store.add_knowledge(KnowledgeEdge(knower, proposition,
                                                                         since_chapter=since_chapter,
                                                                         acquired_via=acquired_via)))


@mcp.tool(annotations=_RW)
async def s3_craft_rule_add(ctx: Context, kind: str, pattern: str, note: str = "") -> dict:
    """加一条本书题材 craft 规则(写,待批)。kind=purple_regex|artifact_craft|cover_action。"""
    ok = await _ask(ctx, f"加题材规则 [{kind}] {pattern}")
    return commit_if_approved("s3_craft_rule_add", ok,
                              lambda: _store.add_craft_rule(kind, pattern, note))


@mcp.tool(annotations=_RW)
async def s3_craft_rule_remove(ctx: Context, rule_id: str) -> dict:
    """删一条本书题材 craft 规则(写,待批)。"""
    ok = await _ask(ctx, f"删题材规则 {rule_id}")
    return commit_if_approved("s3_craft_rule_remove", ok,
                              lambda: _store.delete_craft_rule(rule_id))


# ===== stdio 入口(供 Hermes 以 `python -m scribe3.mcp` 挂载)=====
def setup_store(ns: str = "scribe3", db: str | None = None):
    """连 NS=scribe3 + 幂等建 schema,挂上。db 缺省读 SCRIBE3_WORK 再回退 main(P30)。"""
    import os
    from scribe3.store import SurrealStore
    db = db or os.environ.get("SCRIBE3_WORK", "main")
    store = SurrealStore(ns=ns, db=db)
    store.apply_schema()
    set_store(store)
    return store


def main() -> None:
    setup_store()
    mcp.run()


if __name__ == "__main__":
    main()
