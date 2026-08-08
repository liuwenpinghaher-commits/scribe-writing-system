"""MCP tools — write surface (split from tools.py Phase C)."""
from __future__ import annotations



"""MCP s3_* tools (FastMCP decorators preserved)."""

from scribe3.mcp._common import *  # noqa: F403
from scribe3.mcp.gating import *  # noqa: F403

@mcp.tool(annotations=_RO)

def s3_save_chapter(seq: int, prose: str, title: str = "", focalizer: str | None = None,
                    work: str | None = None, danger_draft: bool = False) -> dict:
    """落/覆盖某章正文(作者草稿,不经 elicitation;manuscript 非世界状态)。

    C-1(正文覆写三路对称):覆写正文后与 app /save-chapter 对称落 final 版本——补版本历史断链
    (此前经此工具改稿的存档点缺失)。ingest 不在此内联:MCP 进程无 app 的 BackgroundTasks /
    _pending_ingest 去重队列,且有专用 s3_ingest_chapter 工具供 agent 显式客观回写;把慢 LLM 抽取
    硬塞进存稿工具会阻塞且跨进程无从与 app 去重集协同,故只落版,知识回写走 s3_ingest_chapter。

    门A/KR1:与 /save-chapter 共用 check_finalize_for_save;blocking 默认拒落 final。
    danger_draft=true 为显式危险旁路(须 agent/作者知情)。"""
    st = _store_for(work)
    from scribe3.finalize_gate import check_finalize_for_save
    fg = check_finalize_for_save(
        st, seq, prose, focalizer=focalizer, danger_draft=bool(danger_draft))
    if not fg.get("allowed"):
        return {
            "status": "blocked",
            "seq": seq,
            "code": fg.get("code") or "finalize_gate",
            "verdict": fg.get("verdict"),
            "message": fg.get("detail") or "定稿门闩未通过,正文未落库",
            "blocking": fg.get("blocking") or [],
            "danger_draft_hint": "传 danger_draft=true 可旁路(危险)",
        }
    st.save_chapter(seq, prose, title=title, focalizer=focalizer)
    # 落 final 版(fail-soft:留版失败不阻断存稿)
    try:
        stats = {"words": len("".join((prose or "").split()))}
        st.add_chapter_version(seq, prose, label="", kind="final",
                               stage="final", stats=stats)
    except Exception as e:
        import logging
        logging.getLogger("scribe3.mcp").warning(
            "s3_save_chapter 自动留 final 版失败(存稿已落库) seq=%s: %s", seq, e)
    return {
        "status": "saved", "seq": seq,
        "finalize_gate": {
            "code": fg.get("code"), "verdict": fg.get("verdict"),
            "danger_draft": bool(danger_draft),
        },
    }


async def s3_add_character(ctx: Context, oid: str, name: str,
                           aliases: list[str] | None = None,
                           appearance: str | None = None,
                           personality_detail: str | None = None,
                           personality_tags: list[str] | None = None,
                           backstory: str | None = None,
                           backstory_secret: bool = False,
                           surface_goal: str | None = None,
                           deep_need: str | None = None,
                           fear: str | None = None,
                           internal_conflict: str | None = None,
                           abilities: list[str] | None = None,
                           weaknesses: list[str] | None = None,
                           importance: str | None = None,
                           first_appearance: int | None = None,
                           work: str | None = None) -> dict:
    """新增角色完整档案(写,待批)。

    所有角色注册字段均可在新建时一次提交；`backstory_secret=true` 会标记前史为
    限知信息。后续任意字段补全请用 `s3_patch_codex`，避免 UI 草稿只停留在前端。
    """
    ok = await _ask(ctx, f"新增角色 {oid}={name}")
    traits = _normalize_character_fields({
        "aliases": aliases or [], "appearance": appearance,
        "personality_detail": personality_detail, "personality_tags": personality_tags or [],
        "backstory": backstory, "backstory_secret": backstory_secret,
        "surface_goal": surface_goal, "deep_need": deep_need, "fear": fear,
        "internal_conflict": internal_conflict, "abilities": abilities or [],
        "weaknesses": weaknesses or [], "importance": importance,
        "first_appearance": first_appearance,
    })
    return commit_if_approved("s3_add_character", ok,
                              lambda: _store_for(work).add_entity(
                                  Entity(oid, "character", name, traits=traits)))


async def s3_set_intent(ctx: Context,
                        reader_feeling: str | None = None,
                        emotional_arc: str | None = None,
                        red_lines: str | None = None,
                        overdue_threshold: int | None = None,
                        total_word_goal: int | None = None,
                        daily_word_goal: int | None = None,
                        work: str | None = None) -> dict:
    """写入/合并本书北极星意图(写,待批)。

    只传需要更新的字段;未传字段保留库中旧值(与 store.set_intent MERGE 语义一致)。
    作者对话驱动落库的正道——禁止要求作者去北极星表单失焦保存。"""
    fields: dict = {}
    if reader_feeling is not None:
        fields["reader_feeling"] = reader_feeling
    if emotional_arc is not None:
        fields["emotional_arc"] = emotional_arc
    if red_lines is not None:
        fields["red_lines"] = red_lines
    if overdue_threshold is not None:
        fields["overdue_threshold"] = overdue_threshold
    if total_word_goal is not None:
        fields["total_word_goal"] = total_word_goal
    if daily_word_goal is not None:
        fields["daily_word_goal"] = daily_word_goal
    if not fields:
        return {"status": "noop", "tool": "s3_set_intent", "reason": "no fields"}
    summary = " / ".join(f"{k}={str(v)[:40]}" for k, v in fields.items())
    ok = await _ask(ctx, f"写入北极星意图:{summary}")
    return commit_if_approved("s3_set_intent", ok,
                              lambda: _store_for(work).set_intent(fields))


async def s3_patch_character(ctx: Context, character_id: str,
                             appearance: str | None = None,
                             personality_detail: str | None = None,
                             surface_goal: str | None = None,
                             deep_need: str | None = None,
                             fear: str | None = None,
                             importance: str | None = None,
                             name: str | None = None,
                             work: str | None = None) -> dict:
    """更正已有角色字段(写,待批)。

    character_id: 裸名或 role:前缀(如「沈砚」或 role:沈砚)。
    只传要改的字段;None 表示不改。用于对话驱动设定返工(G-004),禁止表单失焦直填。"""
    local = character_id.split(":", 1)[-1] if character_id else ""
    if not local:
        return {"status": "error", "tool": "s3_patch_character", "reason": "empty character_id"}
    oid = f"role:{local}"
    fields: dict = {}
    for k, v in (
        ("name", name),
        ("appearance", appearance),
        ("personality_detail", personality_detail),
        ("surface_goal", surface_goal),
        ("deep_need", deep_need),
        ("fear", fear),
        ("importance", importance),
    ):
        if v is not None:
            fields[k] = v
    fields = _normalize_character_fields(fields)
    if not fields:
        return {"status": "noop", "tool": "s3_patch_character", "reason": "no fields"}
    summary = f"{oid} " + " / ".join(f"{k}={str(v)[:40]}" for k, v in fields.items())
    ok = await _ask(ctx, f"更正角色:{summary}")

    def _write():
        st = _store_for(work)
        if not st.exists(oid):
            # 角色不存在时先建最小实体再补字段,避免悬挂更正
            st.add_entity(Entity(oid, "character", local))
        st.update_record(oid, fields)

    return commit_if_approved("s3_patch_character", ok, _write)


async def s3_add_fact(ctx: Context, oid: str, entity: str, attribute: str, value: str,
                      valid_from: int, secret: bool = False,
                      work: str | None = None) -> dict:
    """新增事实/状态@章(写,待批)。secret=True 标私密(泄露=穿帮)。"""
    ok = await _ask(ctx, f"新增事实 {oid}:{entity}·{attribute}={value}")

    def _write():
        st = _store_for(work)
        st.add_fact(Fact(oid, entity, attribute, value, valid_from, secret=secret))
        st.semantic_index(oid, value)   # 写时建语义索引(设定即写即可召回)
    return commit_if_approved("s3_add_fact", ok, _write)


async def s3_add_event(ctx: Context, oid: str, etype: str, valid_from: int,
                       motivated_by_goal: str | None = None,
                       participants: list[dict] | None = None,
                       effects: list[dict] | None = None,
                       causal_in: list[dict] | None = None,
                       causal_root_reason: str | None = None,
                       narrative_position: int | None = None,
                       work: str | None = None) -> dict:
    """新增事件(写,待批)。

    valid_from: 事件发生在故事第几章(story_chapter,故事编年)。
    narrative_position: 可选叙事位——事件在"叙事顺序"里被讲述的位置(spec §3.1)。
      留空(None)= 与 valid_from 同序(线性叙事,默认,向后兼容)。
      非空 = 倒叙/闪回/插叙的独立叙事坐标(故事时间早、叙事位置晚,如第2章发生的事第9章才揭示)。
    participants: 角色参与列表,每项 {"role": "SUBJ|OBJ|WITNESS", "entity": "role:xxx"}。
      role 受控词:SUBJ(主体) / OBJ(受体) / WITNESS(目击者)。
      强烈建议:每个事件都填 participants + effects,否则限知传播(events_at 重建/看见即知道)断链。
    effects: 事件产生的事实列表,每项 {"id": "fact:xxx"}(或直接传 fact oid 字符串)。
      供"看见即知道"据此给在场者发知识边;缺少则 knowledge 传播不工作。
    causal_in: 因果前驱事件列表,每项 {"event": "ev:xxx", "ctype": "causes|enables|..."}。
      causal_complete 验证会检查此链;建议填写以保证连贯性验证通过。
    causal_root_reason: 仅当该事件是同章切换人物/地点/时间后的独立场景根且没有 causal_in 时填写。
    """
    parts = aggregate_event_participants(participants)
    effs = aggregate_event_effects(effects)
    causal = aggregate_event_causal_in(causal_in)

    ok = await _ask(ctx, f"新增事件 {oid}:{etype}")
    return commit_if_approved("s3_add_event", ok,
                              lambda: _store_for(work).add_event(
                                  Event(oid, etype, story_time=valid_from,
                                        motivated_by_goal=motivated_by_goal,
                                        participants=parts,
                                        effects=effs,
                                        causal_in=causal,
                                        causal_root_reason=causal_root_reason,
                                        narrative_position=narrative_position)))


async def s3_add_character_relation(ctx: Context, src_oid: str, dst_oid: str,
                                     relation: str, since_chapter: int,
                                     note: str | None = None,
                                     work: str | None = None) -> dict:
    """添加角色关系(写,待批)。
    relation 受控词表(029迁移后扩展为26词):
      亲属: 父子/母子/兄弟/姐妹/夫妻/师徒/养父子
      正面: 知己/战友/盟友/同门/恩人
      中性: 同行/熟人/上下级/雇主雇员
      对立: 仇敌/宿敌/竞争者/利益对立
      复杂: 爱恨交织/前恋人/背叛者
      兼容旧英文: ally/enemy/kin/master_disciple/lover
      自定义: custom
    """
    ok = await _ask(ctx, f"添加角色关系 {src_oid}→{dst_oid} [{relation}](章{since_chapter})")
    return commit_if_approved("s3_add_character_relation", ok,
                              lambda: _store_for(work).add_character_relation(
                                  src_oid, dst_oid, relation, since_chapter, note))


async def s3_evolve_relation(ctx: Context, src_oid: str, dst_oid: str,
                              new_relation: str, since_chapter: int,
                              note: str | None = None,
                              work: str | None = None) -> dict:
    """关系演变(写,待批):关闭 src→dst 所有开区间关系,写入新关系。
    用于表达敌变友、师徒决裂、盟友反目等弧线。
    new_relation 受控词表同 s3_add_character_relation。
    """
    ok = await _ask(ctx, f"关系演变 {src_oid}→{dst_oid} 变为 [{new_relation}](章{since_chapter})")
    return commit_if_approved("s3_evolve_relation", ok,
                              lambda: _store_for(work).evolve_relation(
                                  src_oid, dst_oid, new_relation, since_chapter, note))


async def s3_add_world_rule(ctx: Context, name: str, category: str,
                             source: str | None = None,
                             capabilities: list | None = None,
                             cost: str | None = None,
                             limitations: list | None = None,
                             exceptions: list | None = None,
                             scope: str = "global",
                             established_chapter: int | None = None,
                             note: str | None = None,
                             work: str | None = None) -> dict:
    """添加世界规则(写,待批)。Sanderson 式:源头/能力/代价/限制/例外。
    category: magic/technology/social/physical/economic/political"""
    ok = await _ask(ctx, f"添加世界规则 [{category}] {name}")
    return commit_if_approved("s3_add_world_rule", ok,
                              lambda: _store_for(work).add_world_rule(
                                  name, category, source, capabilities, cost,
                                  limitations, exceptions, scope, established_chapter, note))


async def s3_add_faction(ctx: Context, name: str,
                          status: str = _mcp_unset_field(),
                          ideology: str | None = _mcp_unset_field(),
                          leader: str | None = _mcp_unset_field(),
                          known_members: list | None = _mcp_unset_field(),
                          public_face: str | None = _mcp_unset_field(),
                          private_operation: str | None = _mcp_unset_field(),
                          private_operation_secret: bool = _mcp_unset_field(),
                          first_mention_chapter: int | None = _mcp_unset_field(),
                          origin: str | None = _mcp_unset_field(),
                          origin_secret: bool = _mcp_unset_field(),
                          artifact_operation: str | None = _mcp_unset_field(),
                          artifact_operation_secret: bool = _mcp_unset_field(),
                          external_manipulation: str | None = _mcp_unset_field(),
                          external_manipulation_secret: bool = _mcp_unset_field(),
                          acceleration_methods: str | None = _mcp_unset_field(),
                          acceleration_methods_secret: bool = _mcp_unset_field(),
                          internal_factions: list | None = _mcp_unset_field(),
                          structure: dict | None = _mcp_unset_field(),
                          key_figures: list | None = _mcp_unset_field(),
                          artifacts: list | None = _mcp_unset_field(),
                          scale: str | None = _mcp_unset_field(),
                          recruitment: str | None = _mcp_unset_field(),
                          symbols: str | None = _mcp_unset_field(),
                          motto: str | None = _mcp_unset_field(),
                          goals: list | None = _mcp_unset_field(),
                          world_rule_affinity: list | None = _mcp_unset_field(),
                          aliases: list | None = _mcp_unset_field(),
                          timeline: list | None = _mcp_unset_field(),
                          headquarters: str | None = _mcp_unset_field(),
                          communication: str | None = _mcp_unset_field(),
                          rituals: str | None = _mcp_unset_field(),
                          secret_agenda: str | None = _mcp_unset_field(),
                          secret_agenda_secret: bool = _mcp_unset_field(),
                          work: str | None = None) -> dict:
    """添加/更新势力/组织(写,待批;CX-Task 3 起支持 codex_schema 注册的全部字段,
    关键字实参)。

    status: 势力当前状态,可选 active/dissolved/dormant/reformed;新建势力不传时按 DB
    schema 默认落 active。各 `*_secret` 字段=true 时对应内容字段恒屏蔽(🔒 私密),
    全知明文见孪生工具 s3_list_factions_reveal(仅供主编全知联查专用;U-003:当前不挂
    载在任何网关,详见该工具自己的 docstring)。

    只传入本次要变更的字段——未传的字段保持库中原值不动(store 层 MERGE 部分更新语义,
    与 REST `POST /factions` 一致),不会被静默清空或重置为默认值。
    """
    ok = await _ask(ctx, f"添加势力 {name}")
    provided = {
        "status": status, "ideology": ideology, "leader": leader,
        "known_members": known_members, "public_face": public_face,
        "private_operation": private_operation,
        "private_operation_secret": private_operation_secret,
        "first_mention_chapter": first_mention_chapter,
        "origin": origin, "origin_secret": origin_secret,
        "artifact_operation": artifact_operation,
        "artifact_operation_secret": artifact_operation_secret,
        "external_manipulation": external_manipulation,
        "external_manipulation_secret": external_manipulation_secret,
        "acceleration_methods": acceleration_methods,
        "acceleration_methods_secret": acceleration_methods_secret,
        "internal_factions": internal_factions,
        "structure": structure,
        "key_figures": key_figures,
        "artifacts": artifacts,
        "scale": scale, "recruitment": recruitment, "symbols": symbols,
        "motto": motto, "goals": goals,
        "world_rule_affinity": world_rule_affinity,
        "aliases": aliases, "timeline": timeline,
        "headquarters": headquarters, "communication": communication,
        "rituals": rituals,
        "secret_agenda": secret_agenda,
        "secret_agenda_secret": secret_agenda_secret,
    }
    kwargs = {k: v for k, v in provided.items() if not _is_mcp_unset(v)}

    def _write():
        st = _store_for(work)
        res = st.add_faction(name, **kwargs)
        # 命题桥同步:与 REST 的 POST /factions(app.py)对称。少了这一步,MCP 建的势力
        # secret 字段就没有桥接命题 → _faction_prompt_block 找不到 fid → 即便作者给角色
        # 授了 knows 边也永远注入不进 prompt(方向安全但功能是坏的),且限知投影/泄露检测
        # /证据链全都看不见这些秘密。同 REST:同步失败只告警,不阻断势力写入本身。
        try:
            row = st.get_faction(name)
            if row is not None:
                sync_faction_secrets(st, name, row)
        except Exception:
            logging.getLogger("scribe3").warning(
                "sync_faction_secrets 命题桥同步失败,不阻断势力写入: %s", name, exc_info=True)
        return res

    return commit_if_approved("s3_add_faction", ok, _write)


def _list_entity_relations_impl(entity: str | None, chapter: int | None,
                                reveal_secret: bool, work: str | None) -> list[dict]:
    st = _store_for(work)
    rows = st.entity_relations_at(chapter, entity) if chapter is not None \
        else st.list_entity_relations(entity)
    result = []
    for row in rows:
        row = dict(row)
        is_secret = bool(row.get("truth_secret"))
        row["truth"] = _mask_value(row.get("truth") or "", is_secret, reveal_secret)
        result.append(row)
    return _jsonable(result)


async def s3_add_entity_relation(ctx: Context, a: str, b: str, relation_type: str,
                                 perception_a: str | None = None,
                                 perception_b: str | None = None,
                                 truth: str | None = None,
                                 truth_secret: bool | None = None,
                                 since_chapter: int | None = None,
                                 work: str | None = None) -> dict:
    """添加/更新通用实体关系(写,待批)。不锁实体类型——faction/character/item 等
    任意组合皆可,a/b 为「前缀:本地id」引用字符串(如 "faction:衔尾蛇秘会"/"role:焦三")。

    relation_type 受控词表:臣服/敌对/渗透/无视/共生/结盟/利用/未知。
    perception_a/perception_b 是 a/b 各自对这段关系的认知,**允许不对称、甚至任一方
    是错的**(如:秘会自认"虚与委蛇的台阶",天龙座却认定秘会是"地球代理人")。
    truth 是仅主编知道的客观真相,默认视为 secret(不传 truth_secret 时新建行按 True
    处理,宁可误锁不可误放);全知明文见孪生工具 s3_list_entity_relations_reveal
    (仅供主编全知联查专用;U-003:当前不挂载在任何网关,详见该工具自己的 docstring)。

    只传本次要变更的字段——未传的 perception_a/perception_b/truth/truth_secret 保持
    库中原值不动(store 层按 (a,b,relation_type,since_chapter) 自然键 MERGE,与
    REST `POST /entity-relations` 一致);a/b/relation_type/since_chapter 是定位关系
    用的键,每次调用都需显式给出。
    """
    ok = await _ask(ctx, f"添加实体关系 {a}→{b} [{relation_type}]")
    kwargs: dict = {}
    if perception_a is not None:
        kwargs["perception_a"] = perception_a
    if perception_b is not None:
        kwargs["perception_b"] = perception_b
    if truth is not None:
        kwargs["truth"] = truth
    if truth_secret is not None:
        kwargs["truth_secret"] = truth_secret
    return commit_if_approved("s3_add_entity_relation", ok,
                              lambda: _store_for(work).add_entity_relation(
                                  a, b, relation_type, since_chapter=since_chapter, **kwargs))


async def s3_add_char_state(ctx: Context, character_id: str, chapter: int,
                             change_type: str, summary: str,
                             before_state: dict | None = None,
                             after_state: dict | None = None,
                             trigger_event: str | None = None,
                             arc_phase: str | None = None,
                             affects_voice: bool | None = None,
                             work: str | None = None) -> dict:
    """记录角色弧光质变点(写,待批)。change_type: ability/relation/personality/composite。
    动静结合:静态基石不变,动态演变记录在此。

    after_state 按 change_type 填写对应快照键:
      ability     → {"ability_snapshot": {"技能名": "描述", ...}}
      relation    → {"relation_snapshot": {"角色/势力": "关系描述", ...}}
      personality → {"personality_snapshot": "简短描述字符串"}
      composite   → 可同时含 ability_snapshot / relation_snapshot / personality_snapshot
    before_state 结构同 after_state,记录变化前状态(可选)。
    char_state_at(character_id, chapter) 将按章序累积 after_state 合成时点快照。"""
    ok = await _ask(ctx, f"记录弧光 {character_id} 第{chapter}章 [{change_type}]: {summary[:30]}")
    return commit_if_approved("s3_add_char_state", ok,
                              lambda: _store_for(work).add_char_state(
                                  character_id, chapter, change_type, summary,
                                  before_state=before_state, after_state=after_state,
                                  trigger_event=trigger_event, arc_phase=arc_phase,
                                  affects_voice=affects_voice))


async def s3_set_voice_profile(ctx: Context, character_id: str,
                                style_summary: str,
                                catchphrases: list | None = None,
                                tone_rules: list | None = None,
                                ooc_signals: list | None = None,
                                work: str | None = None) -> dict:
    """设置角色声音指纹(写,待批)。9节结构,至少提供 style_summary。
    ooc_signals: [{signal_id, description, detection_method, severity}] 可检测的 OOC 规则。"""
    ok = await _ask(ctx, f"设置声音指纹 {character_id}")
    profile = {"style_summary": style_summary, "catchphrases": catchphrases,
               "tone_rules": tone_rules, "ooc_signals": ooc_signals, "version": 1}
    return commit_if_approved("s3_set_voice_profile", ok,
                              lambda: _store_for(work).set_voice_profile(character_id, profile))


async def s3_add_item(ctx: Context, name: str,
                       category: str | None = None,
                       description: str | None = None,
                       current_owner: str | None = None,
                       symbolic_state: str = "active",
                       special_properties: list | None = None,
                       first_chapter: int | None = None,
                       work: str | None = None) -> dict:
    """添加物品/道具(写,待批)。symbolic_state: active/lost/destroyed/unknown。first_chapter: 首次出现章号。"""
    ok = await _ask(ctx, f"添加物品 {name} [{symbolic_state}]")
    return commit_if_approved("s3_add_item", ok,
                              lambda: _store_for(work).add_item(name, category, description,
                                  current_owner, symbolic_state, special_properties,
                                  first_chapter))


async def s3_add_term(ctx: Context, name: str,
                       category: str | None = None,
                       definition: str | None = None,
                       aliases: list | None = None,
                       first_mention_chapter: int | None = None,
                       work: str | None = None) -> dict:
    """添加专有名词/术语(写,待批)。含别名列表。first_mention_chapter: 首次出现章号。"""
    ok = await _ask(ctx, f"添加术语 {name}")
    return commit_if_approved("s3_add_term", ok,
                              lambda: _store_for(work).add_term(
                                  name, category, definition, aliases, first_mention_chapter))


async def s3_plant_promise(ctx: Context, text: str, setup_chapter: int,
                           kind: str = "promise", tier: str = "chapter",
                           resolution: str = "", work: str | None = None) -> dict:
    """埋伏笔(写,待批)。kind=promise/red_herring。
    tier 三档决定兑现窗口与超期判定:
      chapter=近场伏笔(埋后 +1..+3 章内兑现,默认);
      arc=卷级伏笔(+5..+15 章窗口,跨情节弧);
      book=书级伏笔/母题(payoff_max=None,永不判超期,全书终章前兑现)。
    resolution(方案B任务21,收尾清理批 B21 与 REST /promises-new 同约束):
    tier∈{book,arc} 的长期悬念必须带 resolution(文档记录的真实答案),不能含糊
    留白;tier=chapter 短期悬念(本章内起落即兑现)豁免,向后兼容不传此字段的
    既有调用方。非法 tier 由 store 层 raise ValueError。
    成功时 result 含稳定 id,供 s3_advance_promise / s3_add_clue / s3_touch_promise 使用。"""
    if tier in ("book", "arc") and not resolution.strip():
        return {"error": "悬念必须有文档记录的真实答案+预计回收章(tier=chapter 短期悬念豁免)"}
    ok = await _ask(ctx, f"埋伏笔(第{setup_chapter}章·{tier}):{text}")
    return commit_if_approved(
        "s3_plant_promise", ok,
        lambda: _store_for(work).plant_promise(text, setup_chapter, kind=kind, tier=tier,
                                               resolution=resolution))


async def s3_register_purpose(ctx: Context, chapter: int, purpose_text: str,
                              deltas_json: str = "[]", work: str | None = None) -> dict:
    """登记章节目的合同(写,待批)——北极星任务6(蓝图 §3-④):与作者聊定本章目的后,
    把目的翻译成本章承诺改变的世界状态清单(delta),写前登记、写后逐条验收「做没做」。
    purpose_text:一句话目的。deltas_json:JSON 数组,每条
    {kind: knowledge|promise|fact|heat, subject, predicate, ref?}——ref 是 fact/promise id
    或 "甲|乙" 关系对(带 ref 才能机器验收);≤7 条(目的过载即拒)。
    认知类带 ref 的 delta 做写前预演:限知结构下不可实现 → 直接拒绝并给原因。"""
    from scribe3.purpose import (parse_deltas_strict, rehearse_delta_ex,
                                 validate_deltas)
    ds, errs = parse_deltas_strict(deltas_json)   # P1-5:非法条目报错,不静默丢
    if errs:
        return {"error": "deltas 有非法条目:" + ";".join(errs)}
    err = validate_deltas(ds)
    if err:
        return {"error": err}
    st = _store_for(work)
    foc = (st.get_chapter(chapter) or {}).get("focalizer")
    rehearse_degraded = False
    for d in ds:
        rerr, rdeg = rehearse_delta_ex(st, chapter, d, foc)
        rehearse_degraded = rehearse_degraded or rdeg
        if rerr:
            return {"error": rerr}
    ok = await _ask(ctx, f"登记第{chapter}章目的合同:{purpose_text}({len(ds)}条delta)")
    # 统一走 commit_if_approved:False → status=error(不假绿 written);
    # 预演降级标志经 dict 合并保留可见。
    def _write():
        if not st.update_chapter_meta(chapter, {
            "purpose_text": (purpose_text or "")[:200],
            "deltas": ds,
        }):
            return {"error": f"chapter {chapter} 不存在,未登记——先建章再登合同"}
        out = {"chapter": chapter, "deltas": len(ds)}
        if rehearse_degraded:
            out["rehearse_degraded"] = True
        return out

    return commit_if_approved("s3_register_purpose", ok, _write)


async def s3_advance_promise(ctx: Context, pid: str, payoff_chapter: int,
                             work: str | None = None) -> dict:
    """兑现/回收伏笔(写,待批):status→closed + payoff_chapter。
    弃置请用 s3_abandon_promise;障眼法请用 s3_mark_herring。"""
    ok = await _ask(ctx, f"回收伏笔 {pid}(第{payoff_chapter}章)")
    return commit_if_approved("s3_advance_promise", ok,
                              lambda: _store_for(work).advance_promise(pid, payoff_chapter))


async def s3_add_clue(ctx: Context, pid: str, note: str, chapter: int,
                      work: str | None = None) -> dict:
    """追加草蛇灰线中途线索到某条伏笔(写,待批)。
    pid: 伏笔 id(从 s3_list_promises / plant 返回 id 获取)。
    note: 线索描述(该章埋的草蛇灰线,伏笔的中间节点)。
    chapter: 线索所在章号。
    与 s3_advance_promise(回收)不同:不改变 status。
    统一推进:落 clues[] 同时写 promise_touch(与 brief refresh 同源)。"""
    ok = await _ask(ctx, f"追加线索到伏笔 {pid}(第{chapter}章): {note[:30]}")
    return commit_if_approved("s3_add_clue", ok,
                              lambda: _store_for(work).add_promise_clue(pid, note, chapter))


async def s3_mark_herring(ctx: Context, pid: str,
                          work: str | None = None) -> dict:
    """标为障眼法 red_herring(写,待批)。kind 变更,status 仍可为 open;
    不计入 GATE-A 有效 open / overdue 催收。真正弃置账本请用 s3_abandon_promise。"""
    ok = await _ask(ctx, f"标障眼法 {pid}")

    def _write():
        if not _store_for(work).mark_promise_herring(pid):
            return False
        return {"promise_id": pid, "kind": "red_herring"}

    return commit_if_approved("s3_mark_herring", ok, _write)


async def s3_touch_promise(ctx: Context, pid: str, chapter: int,
                           evidence: str = "", work: str | None = None) -> dict:
    """手工登记章触及 promise_touch(写,待批):推进/呼应证据,不改变 status。
    与 ingest 自动抽取同表;evidence 为正文引文或简述。"""
    ok = await _ask(ctx, f"登记伏笔触及 {pid}@第{chapter}章")

    def _write():
        st = _store_for(work)
        if not st.get_promise(pid):
            return False
        st.add_promise_touch(pid, chapter, evidence=evidence or "")
        return {"promise_id": pid, "chapter": chapter, "evidence": evidence or ""}

    return commit_if_approved("s3_touch_promise", ok, _write)


async def s3_abandon_promise(ctx: Context, pid: str,
                             work: str | None = None) -> dict:
    """弃置伏笔(写,待批):status→abandoned。账本结案,不再催收/不进 A6 open。
    与 s3_mark_herring(障眼法 kind)不同;与 s3_advance_promise(兑现 closed)不同。"""
    ok = await _ask(ctx, f"弃置伏笔 {pid}")

    def _write():
        if not _store_for(work).abandon_promise(pid):
            return False
        return {"promise_id": pid, "status": "abandoned"}

    return commit_if_approved("s3_abandon_promise", ok, _write)


async def s3_resolve_voice_flag(ctx: Context, flag_id: str, work: str | None = None) -> dict:
    """关闭声音演变 flag(status: open → done;写,待批)。
    更新声音库后调用此工具标记已处理。flag_id 从 s3_list_voice_flags 获取。"""
    ok = await _ask(ctx, f"关闭声音演变 flag {flag_id}")
    return commit_if_approved("s3_resolve_voice_flag", ok,
                              lambda: _store_for(work).resolve_voice_flag(flag_id))


async def s3_fold_voice_flags(ctx: Context, character_id: str, work: str | None = None) -> dict:
    """半自动声音演变折叠(写,待批):把角色的 open voice_evolution_flag 用 LLM 折叠进 voice_profile。
    声音随情节演变的真闭环——flag 由 ingest/add_char_state 自动创建(affects_voice=True),
    此工具消化 flag→更新声音指纹→resolve flag,完成"声音随情节演变"链路。
    返回 {"folded": n, "profile": {...}} 或 {"folded": 0, "degraded": true}(LLM/解析失败时 fail-soft)。
    无开放 flag 时直接返回 {"folded": 0}(不调 LLM)。"""
    ok = await _ask(ctx, f"折叠声音演变 flag → profile [{character_id}]")
    from scribe3.llm import hermes_complete
    return commit_if_approved(
        "s3_fold_voice_flags", ok,
        lambda: _store_for(work).fold_voice_flags(character_id, hermes_complete))


def s3_ingest_chapter(seq: int, work: str | None = None, force: bool = False) -> dict:
    """章节回写(客观回写,不待批):读定稿抽"谁新知道什么/做了什么"→更新知识账本。
    非创作虚构(add_fact/add_event 那些经 elicitation);ingest 反映已定稿正文,
    后端 save-chapter 也会自动后台跑同一逻辑。

    force=true 时忽略同正文指纹跳过,强制 purge+重抽。
    此工具运行在 Hermes MCP 桥内(单 tool call 上限 300 秒)，所以直连补全必须显式
    小于该上限且禁用内部重试；抽取层最多两次尝试，失败会诚实返回 parse_failed。"""
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete

    def bounded_complete(prompt: str) -> str:
        return hermes_complete(
            prompt,
            timeout=90.0,
            max_tokens=1600,
            retries_override=0,
        )

    w = (work or "main").strip() or "main"
    return ingest_chapter(
        _store_for(w), seq, bounded_complete, max_attempts=2, work=w, force=bool(force),
    )


async def s3_record_knowledge(ctx: Context, knower: str, proposition: str,
                              since_chapter: int, acquired_via: str = "saw",
                              work: str | None = None) -> dict:
    """记知识边:某角色某章获知某命题(写,待批)。
    proposition 必须是已存在的 fact: oid(如 fact:治眼),不接受自然语言文本;
    请先用 s3_add_fact 创建命题,再用本工具建知识边。
    knower 为 character oid(如 role:焦三)或特殊值 "reader"。
    acquired_via: saw/told/inferred/given/learned,默认 saw(枚举外的值会被 DB ASSERT 拒)。
    """
    err = _check_proposition(proposition, work)
    if err:
        return err
    ok = await _ask(ctx, f"记知识 {knower} 知道 {proposition}(章{since_chapter})")
    return commit_if_approved("s3_record_knowledge", ok,
                              lambda: _store_for(work).add_knowledge(
                                  KnowledgeEdge(knower, proposition,
                                                since_chapter=since_chapter,
                                                acquired_via=acquired_via)))


async def s3_supersede_fact(ctx: Context, entity_id: str, attribute: str, value: str,
                             since_chapter: int, secret: bool = False,
                             work: str | None = None) -> dict:
    """超越事实:关闭该 entity+attribute 的所有开区间先驱并写入新值(写,待批)。
    不自动破坏多值属性——调用方需显式控制。
    entity_id: 实体 oid(如 role:焦三);attribute: 属性名;value: 新值;
    since_chapter: 新值生效章号(同时是先驱的 valid_to)。"""
    ok = await _ask(ctx, f"超越事实 {entity_id}·{attribute}={value}(章{since_chapter}起)")
    return commit_if_approved("s3_supersede_fact", ok,
                              lambda: _store_for(work).supersede_fact(
                                  entity_id, attribute, value, since_chapter, secret=secret))


async def s3_forget_knowledge(ctx: Context, knower_id: str, proposition_id: str,
                               until_chapter: int, work: str | None = None) -> dict:
    """令知识遗忘:设置知识边的 until_chapter,使其在该章起失效(写,待批)。
    knower_id: 知者 oid(如 role:焦三);proposition_id: 命题 oid(如 fact:治眼);
    until_chapter: 遗忘生效章号(该章及以后不再知道)。"""
    ok = await _ask(ctx, f"令 {knower_id} 在章{until_chapter}起忘记 {proposition_id}")
    return commit_if_approved("s3_forget_knowledge", ok,
                              lambda: _store_for(work).forget_knowledge(
                                  knower_id, proposition_id, until_chapter))


async def s3_craft_rule_add(ctx: Context, kind: str, pattern: str, note: str = "",
                            work: str | None = None) -> dict:
    """加一条本书题材 craft 规则(写,待批)。kind=purple_regex|artifact_craft|allow_pattern|allow_word。"""
    ok = await _ask(ctx, f"加题材规则 [{kind}] {pattern}")
    return commit_if_approved("s3_craft_rule_add", ok,
                              lambda: _store_for(work).add_craft_rule(kind, pattern, note))


async def s3_author_pref_add(ctx: Context, text: str, work: str | None = None) -> dict:
    """记一条【作者跨书偏好】到 USER.md(写,待批)。只收人级风格倾向(如"偏短句""不煽情"
    "叙事距离偏远");**书内设定/人物/世界观/情节一律禁止**(那是正典,走设定工具)——
    拿不准算不算偏好就不要调用本工具(红线:偏好≠正典,兜底保守)。≤200字。"""
    ok = await _ask(ctx, f"记跨书作者偏好:{text[:80]}")
    from scribe3.author_prefs import append_pref
    return commit_if_approved("s3_author_pref_add", ok, lambda: append_pref(text))


async def s3_craft_rule_remove(ctx: Context, rule_id: str, work: str | None = None) -> dict:
    """删一条本书题材 craft 规则(写,待批)。"""
    ok = await _ask(ctx, f"删题材规则 {rule_id}")
    return commit_if_approved("s3_craft_rule_remove", ok,
                              lambda: _store_for(work).delete_craft_rule(rule_id))


async def s3_add_volume(ctx: Context, title: str, sort_order: int = 0,
                        intro: str | None = None, color: str | None = None,
                        work: str | None = None) -> dict:
    """新建卷(写,待批)。返回 volume 裸 id。"""
    ok = await _ask(ctx, f"新建卷《{title}》sort={sort_order}")

    def _write():
        vid = _store_for(work).add_volume(
            title, sort_order=sort_order, intro=intro, color=color)
        return {"volume_id": vid, "title": title}

    return commit_if_approved("s3_add_volume", ok, _write)


async def s3_patch_volume(ctx: Context, volume_id: str,
                          title: str | None = None,
                          sort_order: int | None = None,
                          intro: str | None = None,
                          color: str | None = None,
                          work: str | None = None) -> dict:
    """改卷元数据(写,待批)。仅提交非 None 字段;无字段→noop;卷不存在→error。"""
    fields = {k: v for k, v in {
        "title": title, "sort_order": sort_order,
        "intro": intro, "color": color,
    }.items() if v is not None}
    if not fields:
        return {"status": "noop", "tool": "s3_patch_volume", "reason": "no fields"}
    ok = await _ask(ctx, f"改卷 {volume_id}: {list(fields)}")

    def _write():
        st = _store_for(work)
        if not st.update_volume(volume_id, fields):
            return False
        return {"volume_id": volume_id, "fields": list(fields)}

    return commit_if_approved("s3_patch_volume", ok, _write)


async def s3_add_chapter(ctx: Context, title: str = "",
                         volume_id: str | None = None,
                         work: str | None = None) -> dict:
    """新建空章(写,待批)。seq=历史最大章号+1;可选挂到 volume_id。"""
    ok = await _ask(ctx, f"新建章《{title or '未命名'}》vol={volume_id}")

    def _write():
        return _store_for(work).create_chapter(title=title, volume_id=volume_id)

    return commit_if_approved("s3_add_chapter", ok, _write)


async def s3_patch_chapter_meta(
    ctx: Context, seq: int,
    title: str | None = None,
    label: str | None = None,
    volume_id: str | None = None,
    clear_volume: bool = False,
    work: str | None = None,
) -> dict:
    """改章身份元数据(标题/标签/卷归属;写,待批)。不改 synopsis/beats/prose。

    clear_volume=True 时清空卷归属(volume=None);否则 volume_id 非 None 时设归属。
    章不存在 → status=error。"""
    fields: dict = {}
    if title is not None:
        fields["title"] = title
    if label is not None:
        fields["label"] = label
    if clear_volume:
        fields["volume"] = None
    elif volume_id is not None:
        fields["volume"] = volume_id
    if not fields:
        return {"status": "noop", "tool": "s3_patch_chapter_meta", "reason": "no fields"}
    ok = await _ask(ctx, f"改第{seq}章 meta {list(fields)}")

    def _write():
        st = _store_for(work)
        if not st.update_chapter_meta(seq, fields):
            return False
        return {"seq": seq, "fields": list(fields)}

    return commit_if_approved("s3_patch_chapter_meta", ok, _write)


async def s3_patch_chapter_plan(
    ctx: Context, seq: int,
    synopsis: str | None = None,
    beats: list[dict[str, Any] | str] | None = None,
    scene_truth: str | None = None,
    deductions: list[dict[str, Any]] | None = None,
    involved_characters: list[str] | None = None,
    work: str | None = None,
) -> dict:
    """改章阶段内容:大纲/节拍/场景真相/演绎/出场角色(写,待批)。不改 prose/身份 meta。

    beats 每项必须有 text（beat/action 可作别名）；involved_characters 必须是书内角色
    id 或名字；deductions 每项必须是 {character_id, prose}。非法结构在审批前返回 error，
    绝不写入一个后续上下文无法消费的 plan。章不存在 → status=error。"""
    store = _store_for(work)
    fields: dict = {}
    if synopsis is not None:
        fields["synopsis"] = synopsis
    if beats is not None:
        normalized_beats, err = _normalize_plan_beats(beats)
        if err:
            return {"status": "error", "tool": "s3_patch_chapter_plan", "error": err}
        fields["beats"] = normalized_beats
    if scene_truth is not None:
        fields["scene_truth"] = scene_truth
    if deductions is not None:
        normalized_deductions, err = _normalize_plan_deductions(store, deductions)
        if err:
            return {"status": "error", "tool": "s3_patch_chapter_plan", "error": err}
        fields["deductions"] = normalized_deductions
    if involved_characters is not None:
        normalized_involved, err = _canonical_plan_characters(store, involved_characters, "involved_characters")
        if err:
            return {"status": "error", "tool": "s3_patch_chapter_plan", "error": err}
        fields["involved_characters"] = normalized_involved
    # 演绎若显式提交 deductions，必须覆盖本次（或已存）的全部出场角色。
    # 否则 `deductions=[]` 会经审批被写成成功，但 Gate-B/后续限知上下文均不可消费。
    if deductions is not None:
        current = store.get_chapter(seq) or {}
        effective_involved = fields.get("involved_characters", current.get("involved_characters") or [])
        effective_deductions = fields.get("deductions") or []
        projected = {str(item.get("character_id") or "") for item in effective_deductions}
        missing = [cid for cid in effective_involved if cid not in projected]
        if missing:
            return {
                "status": "error",
                "tool": "s3_patch_chapter_plan",
                "error": f"deductions 缺少涉及角色的限知投影: {missing}",
            }
    if not fields:
        return {"status": "noop", "tool": "s3_patch_chapter_plan", "reason": "no fields"}
    ok = await _ask(ctx, f"改第{seq}章 plan {list(fields.keys())}")

    def _write():
        if not store.update_chapter_meta(seq, fields):
            return False
        return {"seq": seq, "fields": list(fields.keys())}

    return commit_if_approved("s3_patch_chapter_plan", ok, _write)


async def s3_set_char_anchors(
    ctx: Context, character_id: str,
    want: str | None = None,
    need: str | None = None,
    lie: str | None = None,
    ghost: str | None = None,
    truth: str | None = None,
    arc_type: str | None = None,
    private_agenda: str | None = None,
    work: str | None = None,
) -> dict:
    """写角色弧光锚(写,待批)。局部更新;键限 store _ANCHOR_KEYS 白名单。

    character_id: 裸名或 role:前缀。只传要改的字段。"""
    anchors = {k: v for k, v in {
        "want": want, "need": need, "lie": lie, "ghost": ghost,
        "truth": truth, "arc_type": arc_type, "private_agenda": private_agenda,
    }.items() if v is not None}
    if not anchors:
        return {"status": "noop", "tool": "s3_set_char_anchors", "reason": "no fields"}
    ok = await _ask(ctx, f"设弧光锚 {character_id}: {list(anchors)}")

    def _write():
        _store_for(work).set_char_anchors(character_id, anchors)
        return {"character_id": character_id, "keys": list(anchors)}

    return commit_if_approved("s3_set_char_anchors", ok, _write)


async def s3_reorder_chapters(ctx: Context, volume_id: str | None = None,
                              order: list[int] | None = None,
                              work: str | None = None) -> dict:
    """重排某卷(或未分卷)内章节顺序(写,待批)。只改 sort_order/volume,不动 seq。

    order: 章号 seq 列表,顺序即新序。volume_id 空=未分卷基址。"""
    seqs = list(order or [])
    if not seqs:
        return {"status": "noop", "tool": "s3_reorder_chapters", "reason": "empty order"}
    ok = await _ask(ctx, f"重排章节 vol={volume_id or '未分卷'} order={seqs}")

    def _write():
        n = _store_for(work).reorder_chapters(volume_id, seqs)
        return {"volume_id": volume_id, "count": n, "order": seqs}

    return commit_if_approved("s3_reorder_chapters", ok, _write)


async def s3_delete_volume(ctx: Context, volume_id: str,
                           work: str | None = None) -> dict:
    """删除卷(写,待批)。该卷下章 volume 置空,不删章正文。"""
    vid = (volume_id or "").strip()
    if not vid:
        return {"status": "error", "tool": "s3_delete_volume", "error": "volume_id required"}
    ok = await _ask(ctx, f"删除卷 {vid}(章保留,仅清卷归属)")

    def _write():
        if not _store_for(work).delete_volume(vid):
            return False
        return {"volume_id": vid, "deleted": True}

    return commit_if_approved("s3_delete_volume", ok, _write)


async def s3_add_motif(ctx: Context, name: str, theme: str = "",
                       echoes: str = "", unfolding: str = "",
                       work: str | None = None) -> dict:
    """新建母题(写,待批)。"""
    n = (name or "").strip()
    if not n:
        return {"status": "error", "tool": "s3_add_motif", "error": "name required"}
    ok = await _ask(ctx, f"新建母题「{n}」")

    def _write():
        _store_for(work).add_motif(n, theme=theme or "", echoes=echoes or "",
                                   unfolding=unfolding or "")
        return {"name": n, "theme": theme or ""}

    return commit_if_approved("s3_add_motif", ok, _write)


async def s3_patch_faction(ctx: Context, name: str,
                           ideology: str | None = None,
                           leader: str | None = None,
                           public_face: str | None = None,
                           status: str | None = None,
                           work: str | None = None) -> dict:
    """更正势力字段(写,待批)。只传要改的字段;底层 add_faction MERGE。"""
    n = (name or "").strip()
    if not n:
        return {"status": "error", "tool": "s3_patch_faction", "error": "name required"}
    fields = {k: v for k, v in (
        ("ideology", ideology), ("leader", leader),
        ("public_face", public_face), ("status", status),
    ) if v is not None}
    if not fields:
        return {"status": "noop", "tool": "s3_patch_faction", "reason": "no fields"}
    ok = await _ask(ctx, f"更正势力「{n}」:{','.join(fields)}")

    def _write():
        st = _store_for(work)
        if not st.get_faction(n):
            return False
        st.add_faction(n, **fields)
        return {"name": n, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_faction", ok, _write)


async def s3_patch_item(ctx: Context, name: str,
                        description: str | None = None,
                        category: str | None = None,
                        current_owner: str | None = None,
                        symbolic_state: str | None = None,
                        work: str | None = None) -> dict:
    """更正物品字段(写,待批)。"""
    n = (name or "").strip()
    if not n:
        return {"status": "error", "tool": "s3_patch_item", "error": "name required"}
    fields = {k: v for k, v in (
        ("description", description), ("category", category),
        ("current_owner", current_owner), ("symbolic_state", symbolic_state),
    ) if v is not None}
    if not fields:
        return {"status": "noop", "tool": "s3_patch_item", "reason": "no fields"}
    ok = await _ask(ctx, f"更正物品「{n}」")

    def _write():
        if not _store_for(work).patch_item(n, fields):
            return False
        return {"name": n, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_item", ok, _write)


async def s3_patch_term(ctx: Context, name: str,
                        definition: str | None = None,
                        category: str | None = None,
                        work: str | None = None) -> dict:
    """更正术语字段(写,待批)。"""
    n = (name or "").strip()
    if not n:
        return {"status": "error", "tool": "s3_patch_term", "error": "name required"}
    fields = {k: v for k, v in (("definition", definition), ("category", category)) if v is not None}
    if not fields:
        return {"status": "noop", "tool": "s3_patch_term", "reason": "no fields"}
    ok = await _ask(ctx, f"更正术语「{n}」")

    def _write():
        if not _store_for(work).patch_term(n, fields):
            return False
        return {"name": n, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_term", ok, _write)


async def s3_patch_world_rule(ctx: Context, name: str,
                              category: str | None = None,
                              cost: str | None = None,
                              note: str | None = None,
                              source: str | None = None,
                              work: str | None = None) -> dict:
    """更正世界规则(写,待批)。"""
    n = (name or "").strip()
    if not n:
        return {"status": "error", "tool": "s3_patch_world_rule", "error": "name required"}
    fields = {k: v for k, v in (
        ("category", category), ("cost", cost), ("note", note), ("source", source),
    ) if v is not None}
    if not fields:
        return {"status": "noop", "tool": "s3_patch_world_rule", "reason": "no fields"}
    ok = await _ask(ctx, f"更正世界规则「{n}」")

    def _write():
        if not _store_for(work).patch_world_rule(n, fields):
            return False
        return {"name": n, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_world_rule", ok, _write)


async def s3_patch_codex(ctx: Context, kind: str, name: str, fields: dict[str, Any],
                         work: str | None = None) -> dict:
    """按 Codex 注册表更正完整设定档案(写,待批)。

    `kind` 仅可为 character/faction/item/term/world_rule；`fields` 是要更正的字段对象。
    字段必须来自对应的 `GET /codex-schema/{kind}` 注册表，未传字段保持原值。名称 `name`
    用来定位原对象，不能借此工具改名。适合一次提交人物完整档案或势力的嵌套字段；常用
    简单字段仍可使用具名 s3_patch_* 工具。
    """
    supported = {"character", "faction", "item", "term", "world_rule"}
    k = (kind or "").strip()
    n = (name or "").strip()
    if k not in supported:
        return {"status": "error", "tool": "s3_patch_codex", "error": f"unsupported kind:{k}"}
    if not n:
        return {"status": "error", "tool": "s3_patch_codex", "error": "name required"}
    if not isinstance(fields, dict) or not fields:
        return {"status": "noop", "tool": "s3_patch_codex", "reason": "no fields"}
    allowed = set(all_storage_keys(k))
    unknown = set(fields) - allowed
    if unknown:
        return {"status": "error", "tool": "s3_patch_codex",
                "error": f"unknown {k} fields:{sorted(unknown)}"}
    changes = dict(fields)
    if "name" in changes:
        if changes["name"] != n:
            return {"status": "error", "tool": "s3_patch_codex",
                    "error": "rename is not supported by s3_patch_codex; use the existing name"}
        changes.pop("name")
    if not changes:
        return {"status": "noop", "tool": "s3_patch_codex", "reason": "no mutable fields"}
    ok = await _ask(ctx, f"更正{k}「{n}」:{','.join(sorted(changes))}")

    def _write():
        st = _store_for(work)
        if k == "character":
            oid = f"role:{n}"
            if not st.exists(oid):
                return False
            st.update_record(oid, _normalize_character_fields(changes))
        elif k == "faction":
            if not st.get_faction(n):
                return False
            st.add_faction(n, **changes)
            row = st.get_faction(n)
            if row is not None:
                sync_faction_secrets(st, n, row)
        elif k == "item":
            if not st.patch_item(n, changes):
                return False
        elif k == "term":
            if not st.patch_term(n, changes):
                return False
        else:
            if not st.patch_world_rule(n, changes):
                return False
        return {"kind": k, "name": n, "patched": sorted(changes)}

    return commit_if_approved("s3_patch_codex", ok, _write)


async def s3_patch_motif(ctx: Context, motif_id: str,
                         name: str | None = None,
                         theme: str | None = None,
                         echoes: str | None = None,
                         unfolding: str | None = None,
                         phase: str | None = None,
                         tier: str | None = None,
                         scope: str | None = None,
                         work: str | None = None) -> dict:
    """更正母题(写,待批)。motif_id 为裸 id 或名称。
    phase: seed|echo|turn|payoff|rest; tier: book|volume|arc|chapter。"""
    mid = (motif_id or "").strip()
    if not mid:
        return {"status": "error", "tool": "s3_patch_motif", "error": "motif_id required"}
    fields = {k: v for k, v in (
        ("name", name), ("theme", theme), ("echoes", echoes), ("unfolding", unfolding),
        ("phase", phase), ("tier", tier), ("scope", scope),
    ) if v is not None}
    if not fields:
        return {"status": "noop", "tool": "s3_patch_motif", "reason": "no fields"}
    ok = await _ask(ctx, f"更正母题 {mid}")

    def _write():
        if not _store_for(work).patch_motif(mid, fields):
            return False
        return {"motif_id": mid, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_motif", ok, _write)


async def s3_patch_promise(ctx: Context, promise_id: str,
                           text: str | None = None,
                           resolution: str | None = None,
                           tier: str | None = None,
                           setup_chapter: int | None = None,
                           kind: str | None = None,
                           payoff_min: int | None = None,
                           payoff_max: int | None = None,
                           work: str | None = None) -> dict:
    """更正伏笔(写,待批)。经 store.update_promise:改 tier/setup 时自动重算兑现窗口
    (除非显式传 payoff_min/payoff_max)。
    回收请用 s3_advance_promise;弃置 s3_abandon_promise;障眼法 s3_mark_herring。
    tier∈{book,arc} 升格时须有 resolution(请求或库中已有)。"""
    pid = (promise_id or "").strip()
    if not pid:
        return {"status": "error", "tool": "s3_patch_promise", "error": "promise_id required"}
    fields: dict = {}
    if text is not None:
        fields["text"] = text
    if resolution is not None:
        fields["resolution"] = resolution
    if tier is not None:
        fields["tier"] = tier
    if setup_chapter is not None:
        fields["setup_chapter"] = setup_chapter
    if kind is not None:
        fields["kind"] = kind
    if payoff_min is not None:
        fields["payoff_min"] = payoff_min
    if payoff_max is not None:
        fields["payoff_max"] = payoff_max
    if not fields:
        return {"status": "noop", "tool": "s3_patch_promise", "reason": "no fields"}
    st = _store_for(work)
    # book/arc 升格须 resolution
    if fields.get("tier") in ("book", "arc"):
        res_in = (fields.get("resolution") or "").strip()
        if not res_in:
            row = st.get_promise(pid)
            if row is not None and not (row.get("resolution") or "").strip():
                return {"error": "悬念必须有文档记录的真实答案+预计回收章(tier=chapter 短期悬念豁免)"}
    ok = await _ask(ctx, f"更正伏笔 {pid}: {','.join(fields.keys())}")

    def _write():
        try:
            if not st.update_promise(pid, fields):
                return False
        except ValueError as e:
            return {"error": str(e)}
        return {"promise_id": pid, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_promise", ok, _write)


async def s3_delete_codex(ctx: Context, object_type: str, object_id: str,
                          archive: bool = True,
                          work: str | None = None) -> dict:
    """归档或删除设定对象(写,待批)。

    object_type: role|fact|material|faction|item|term|world_rule|promise|motif
    object_id: 裸 id 或 name(势力/物件/术语/规则用 name)。
    archive=True 优先软归档(role/fact/material);无 archive 能力的类型走硬删。
    """
    ot = (object_type or "").strip()
    oid = (object_id or "").strip()
    if not ot or not oid:
        return {"status": "error", "tool": "s3_delete_codex",
                "error": "object_type and object_id required"}
    mode = "归档" if archive else "删除"
    ok = await _ask(ctx, f"{mode}设定 {ot}:{oid}")

    def _write():
        st = _store_for(work)
        if ot == "material":
            if archive:
                if not st.update_material(oid, {"archived": True}):
                    return False
                return {"object_type": ot, "object_id": oid, "action": "archive"}
            if not st.delete_material(oid, cleanup_refs=True):
                return False
            return {"object_type": ot, "object_id": oid, "action": "delete"}
        if ot in ("role", "fact"):
            full = oid if ":" in oid else f"{ot}:{oid}"
            if ot == "role" and not full.startswith("role:"):
                full = f"role:{oid}"
            if ot == "fact" and not full.startswith("fact:"):
                full = f"fact:{oid}"
            if archive:
                if not st.exists(full):
                    return False
                st.update_record(full, {"archived": True})
                return {"object_type": ot, "object_id": full, "action": "archive"}
            if not st.delete_record(full, cleanup_refs=True):
                return False
            return {"object_type": ot, "object_id": full, "action": "delete"}
        if ot == "faction":
            if not st.get_faction(oid):
                return False
            st.delete_faction(oid)
            return {"object_type": ot, "object_id": oid, "action": "delete"}
        if ot == "item":
            if not st.get_item(oid):
                return False
            st.delete_item(oid)
            return {"object_type": ot, "object_id": oid, "action": "delete"}
        if ot == "term":
            if not st.get_term(oid):
                return False
            st.delete_term(oid)
            return {"object_type": ot, "object_id": oid, "action": "delete"}
        if ot == "world_rule":
            if not st.get_world_rule(oid):
                return False
            st.delete_world_rule(oid)
            return {"object_type": ot, "object_id": oid, "action": "delete"}
        if ot == "promise":
            rows = st._query("SELECT id FROM type::record('promise',$pid) LIMIT 1", {"pid": oid})
            if not rows:
                return False
            st._execute_write("DELETE type::record('promise',$pid)", {"pid": oid})
            return {"object_type": ot, "object_id": oid, "action": "delete"}
        if ot == "motif":
            row = st.get_motif(oid)
            if not row:
                return False
            st.delete_motif(row["id"])
            return {"object_type": ot, "object_id": row["id"], "action": "delete"}
        return {"error": f"unsupported object_type {ot!r}"}

    return commit_if_approved("s3_delete_codex", ok, _write)

