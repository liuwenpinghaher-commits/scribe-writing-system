"""MCP tools — write surface (split from tools.py Phase C)."""
from __future__ import annotations

from scribe3.feature_flags import get_flag
from scribe3.mcp._common import *  # noqa: F403
from scribe3.mcp.gating import *  # noqa: F403

# O13：生产写工具自动把调用方参数送入审批幂等指纹（否则 args= 全空、短路死）
import inspect as _inspect
from scribe3.mcp import gating as _gating_mod
from scribe3.write_commit import args_from_tool_locals as _args_from_tool_locals

_gate_commit_if_approved = _gating_mod.commit_if_approved


def commit_if_approved(name, accepted, do_write, args=None):  # noqa: F811
    """Shadow gating.commit_if_approved：args 缺省时从调用方 frame 收集稳定参数。

    所有本模块 ``return commit_if_approved(...)`` 均经此路径，幂等指纹生效。
    """
    if args is None:
        fr = _inspect.currentframe()
        try:
            caller = fr.f_back if fr else None
            raw = dict(caller.f_locals) if caller else {}
        finally:
            del fr
        args = _args_from_tool_locals(raw)
    return _gate_commit_if_approved(name, accepted, do_write, args=args)


@mcp.tool(annotations=_RO)

def s3_save_chapter(seq: int, prose: str, title: str = "", focalizer: str | None = None,
                    work: str | None = None, danger_draft: bool = False,
                    skip_craft_gate: bool = False) -> dict:
    """落/覆盖某章正文(作者草稿,不经 elicitation;manuscript 非世界状态)。

    C-1(正文覆写三路对称):覆写正文后与 app /save-chapter 对称落 final 版本——补版本历史断链
    (此前经此工具改稿的存档点缺失)。ingest 不在此内联:MCP 进程无 app 的 BackgroundTasks /
    _pending_ingest 去重队列,且有专用 s3_ingest_chapter 工具供 agent 显式客观回写;把慢 LLM 抽取
    硬塞进存稿工具会阻塞且跨进程无从与 app 去重集协同,故只落版,知识回写走 s3_ingest_chapter。

    KD16:与 HTTP 共用 evaluate_save_craft_gate;blocking → 不落库。
    门A/KR1:质控 check_finalize_for_save（danger 可旁路 QC）。
    G4:kind=final 仅经 try_stamp_kind_final（craft hard，danger 不旁路）。
    danger_draft=true 为显式危险旁路(须 agent/作者知情)——仅 QC，不旁路 craft stamp。"""
    st = _store_for(work)
    from scribe3.finalize_gate import check_finalize_for_save, try_stamp_kind_final
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
            "danger_draft_hint": "传 danger_draft=true 可旁路质控(危险；不旁路 craft stamp)",
        }
    st.save_chapter(seq, prose, title=title, focalizer=focalizer)
    # G4：仅 craft hard 通过才 stamp kind=final
    stats = {"words": len("".join((prose or "").split()))}
    final_stamp = try_stamp_kind_final(
        st, seq, prose, label="", stage="final", stats=stats,
        skip_craft=bool(skip_craft_gate),
    )
    # 不内联 ingest;返回策略建议(active hold / auto required)
    from scribe3.ingest_policy import GateSnapshot, decide_ingest
    _verdict = str(fg.get("verdict") or "pass").lower()
    if fg.get("advisory_items") and _verdict in ("", "pass", "ok"):
        _verdict = "advisory"
    _cm = None
    try:
        import os as _os
        _cm = (get_flag("SCRIBE3_CREATE_MODE") or "standard").strip().lower()
    except Exception:
        _cm = "standard"
    dec = decide_ingest(
        st, (work or "main").strip() or "main", seq,
        gate=GateSnapshot(
            path="mcp_save", craft_allowed=True,
            finalize_verdict=_verdict, danger_draft=bool(danger_draft),
            create_mode=_cm,
        ),
        prose=prose, source="mcp_save",
    )
    if dec.action == "hold":
        from scribe3.ingest_policy import write_hold
        write_hold(
            st, seq, reason=dec.hold_reason or dec.reason,
            token=dec.confirm_token, prose_fp=dec.prose_fp,
        )
    return {
        "status": "saved", "seq": seq,
        "finalize_gate": {
            "code": fg.get("code"), "verdict": fg.get("verdict"),
            "danger_draft": bool(danger_draft),
        },
        "final_stamp": final_stamp,
        "final_version_stamped": bool(final_stamp.get("stamped")),
        "ingest": {
            "action": dec.action,
            "reason": dec.reason or dec.skip_reason or dec.hold_reason,
            "held": dec.action == "hold",
            "required": dec.action == "auto",
            "confirm_token": dec.confirm_token or None,
            "hold_reason": dec.hold_reason or None,
            "prose_fp": dec.prose_fp,
            "hint": "调用 s3_ingest_chapter 执行客观回写" if dec.action == "auto"
                    else ("确认后 s3_ingest_chapter(force=true) 或 POST /ingest/confirm"
                          if dec.action == "hold" else "无需回写"),
        },
    }


@mcp.tool(annotations=_RW)
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
                           gender: str | None = None,
                           work: str | None = None) -> dict:
    """新增角色完整档案(写,待批)。

    所有角色注册字段均可在新建时一次提交；`backstory_secret=true` 会标记前史为
    限知信息。后续任意字段补全请用 `s3_patch_codex`，避免 UI 草稿只停留在前端。
    """
    traits = _normalize_character_fields({
        "aliases": aliases or [], "appearance": appearance,
        "personality_detail": personality_detail, "personality_tags": personality_tags or [],
        "backstory": backstory, "backstory_secret": backstory_secret,
        "surface_goal": surface_goal, "deep_need": deep_need, "fear": fear,
        "internal_conflict": internal_conflict, "abilities": abilities or [],
        "weaknesses": weaknesses or [], "importance": importance,
        "first_appearance": first_appearance, "gender": gender or "",
    })
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("character", traits)
    if _l1:
        return {**_l1, "tool": "s3_add_character"}
    ok = await _ask(ctx, f"新增角色 {oid}={name}")
    return commit_if_approved("s3_add_character", ok,
                              lambda: _store_for(work).add_entity(
                                  Entity(oid, "character", name, traits=traits)))


@mcp.tool(annotations=_RW)
async def s3_set_intent(ctx: Context,
                        reader_feeling: str | None = None,
                        emotional_arc: str | None = None,
                        red_lines: str | None = None,
                        who_pays: str | None = None,
                        axis_terms: str | None = None,
                        clock_start: str | None = None,
                        clock_end: str | None = None,
                        imagery: str | None = None,
                        north_star: str | None = None,
                        overdue_threshold: int | None = None,
                        total_word_goal: int | None = None,
                        daily_word_goal: int | None = None,
                        arc_tracking: str | None = None,
                        structure_mode: bool | None = None,
                        structure_budget: str | None = None,
                        work: str | None = None) -> dict:
    """写入/合并本书北极星意图(写,待批)。

    只传需要更新的字段;未传字段保留库中旧值(与 store.set_intent MERGE 语义一致)。
    arc_tracking: on|off — 作品级关闭弧光追踪（PR8）。
    作者对话驱动落库的正道——禁止要求作者去北极星表单失焦保存。"""
    fields: dict = {}
    if reader_feeling is not None:
        fields["reader_feeling"] = reader_feeling
    if emotional_arc is not None:
        fields["emotional_arc"] = emotional_arc
    if red_lines is not None:
        fields["red_lines"] = red_lines
    if who_pays is not None:
        fields["who_pays"] = who_pays
    if axis_terms is not None:
        fields["axis_terms"] = axis_terms
    if clock_start is not None:
        fields["clock_start"] = clock_start
    if clock_end is not None:
        fields["clock_end"] = clock_end
    if imagery is not None:
        fields["imagery"] = imagery
    if north_star is not None:
        fields["north_star"] = north_star
    if overdue_threshold is not None:
        fields["overdue_threshold"] = overdue_threshold
    if total_word_goal is not None:
        fields["total_word_goal"] = total_word_goal
    if daily_word_goal is not None:
        fields["daily_word_goal"] = daily_word_goal
    if arc_tracking is not None:
        at = str(arc_tracking).strip().lower()
        if at not in ("on", "off"):
            return {"status": "error", "tool": "s3_set_intent",
                    "reason": "arc_tracking 须为 on|off"}
        fields["arc_tracking"] = at
    if structure_mode is not None:
        fields["structure_mode"] = bool(structure_mode)
    if structure_budget is not None:
        fields["structure_budget"] = structure_budget
    if not fields:
        return {"status": "noop", "tool": "s3_set_intent", "reason": "no fields"}
    summary = " / ".join(f"{k}={str(v)[:40]}" for k, v in fields.items())
    ok = await _ask(ctx, f"写入北极星意图:{summary}")
    return commit_if_approved("s3_set_intent", ok,
                              lambda: _store_for(work).set_intent(fields))


@mcp.tool(annotations=_RW)
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
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("character", fields)
    if _l1:
        return {**_l1, "tool": "s3_patch_character"}
    summary = f"{oid} " + " / ".join(f"{k}={str(v)[:40]}" for k, v in fields.items())
    ok = await _ask(ctx, f"更正角色:{summary}")

    def _write():
        st = _store_for(work)
        if not st.exists(oid):
            # 角色不存在时先建最小实体再补字段,避免悬挂更正
            st.add_entity(Entity(oid, "character", local))
        st.update_record(oid, fields)

    return commit_if_approved("s3_patch_character", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_add_fact(ctx: Context, oid: str, entity: str, attribute: str, value: str,
                      valid_from: int, secret: bool = False,
                      work: str | None = None) -> dict:
    """新增世界真相/状态@章(写,待批)。作者表面亦称「世界真相」。

    参数语义（业务话术）：
    - entity：关于谁（如 role:焦三）
    - attribute：哪方面状态（如 state / 位置）
    - value：具体内容
    - valid_from：从第几章起成立
    - secret：私密（限知；非持有者视角不可直说）

    同 entity+attribute 的开区间旧命题会被关闭(valid_to=valid_from)，避免改设定后
    新旧真值并存污染检索/写作（记忆质量 D4）。改已有状态请优先 s3_supersede_fact
    （勿依赖 REST edit_fact 原地抹历史）。"""
    ok = await _ask(ctx, f"新增世界真相 {oid}:{entity}·{attribute}={value}")

    def _write():
        st = _store_for(work)
        st.add_fact(
            Fact(oid, entity, attribute, value, valid_from, secret=secret, source="author"),
            supersede_open=True,
        )
        # add_fact 内已 semantic_index；保留二次调用幂等（旧行为兼容）
        try:
            st.semantic_index(oid, value)
        except Exception:
            pass
    return commit_if_approved("s3_add_fact", ok, _write)


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
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
    if note is not None and str(note).strip() and len(str(note).strip()) < 10:
        return {"status": "error", "tool": "s3_add_character_relation", "code": "note_thin",
                "error": "关系备注过短（<10）"}
    ok = await _ask(ctx, f"添加角色关系 {src_oid}→{dst_oid} [{relation}](章{since_chapter})")
    return commit_if_approved("s3_add_character_relation", ok,
                              lambda: _store_for(work).add_character_relation(
                                  src_oid, dst_oid, relation, since_chapter, note))


@mcp.tool(annotations=_RW)
async def s3_evolve_relation(ctx: Context, src_oid: str, dst_oid: str,
                              new_relation: str, since_chapter: int,
                              note: str | None = None,
                              work: str | None = None) -> dict:
    """关系演变(写,待批):关闭 src→dst 所有开区间关系,写入新关系。
    用于表达敌变友、师徒决裂、盟友反目等弧线。
    new_relation 受控词表同 s3_add_character_relation。
    """
    if note is not None and str(note).strip() and len(str(note).strip()) < 10:
        return {"status": "error", "tool": "s3_evolve_relation", "code": "note_thin",
                "error": "关系备注过短（<10）"}
    ok = await _ask(ctx, f"关系演变 {src_oid}→{dst_oid} 变为 [{new_relation}](章{since_chapter})")
    return commit_if_approved("s3_evolve_relation", ok,
                              lambda: _store_for(work).evolve_relation(
                                  src_oid, dst_oid, new_relation, since_chapter, note))


@mcp.tool(annotations=_RW)
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
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("world_rule", {
        k: v for k, v in (
            ("cost", cost), ("limitations", limitations),
            ("exceptions", exceptions), ("capabilities", capabilities),
            ("source", source),
        ) if v is not None
    })
    if _l1:
        return {**_l1, "tool": "s3_add_world_rule"}
    ok = await _ask(ctx, f"添加世界规则 [{category}] {name}")
    return commit_if_approved("s3_add_world_rule", ok,
                              lambda: _store_for(work).add_world_rule(
                                  name, category, source, capabilities, cost,
                                  limitations, exceptions, scope, established_chapter, note))


@mcp.tool(annotations=_RW)
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
    from scribe3.iceberg import persist_codex_fields_blocked
    _probe = {}
    for _key, _val in (
        ("private_operation", private_operation),
        ("ideology", ideology),
        ("public_face", public_face),
        ("recruitment", recruitment),
        ("structure", structure),
        ("origin", origin),
        ("artifact_operation", artifact_operation),
        ("external_manipulation", external_manipulation),
        ("acceleration_methods", acceleration_methods),
        ("secret_agenda", secret_agenda),
        ("goals", goals),
    ):
        if not _is_mcp_unset(_val) and _val not in (None, "", [], {}):
            _probe[_key] = _val
    _blk = persist_codex_fields_blocked("faction", _probe, mode="incremental") if _probe else None
    if _blk:
        return {"status": "error", "tool": "s3_add_faction", "error": _blk["message"], "code": _blk["code"]}
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


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
async def s3_add_char_state(ctx: Context, character_id: str, chapter: int,
                             change_type: str, summary: str,
                             before_state: dict | None = None,
                             after_state: dict | None = None,
                             trigger_event: str | None = None,
                             arc_phase: str | None = None,
                             affects_voice: bool | None = None,
                             lie_belief: int | None = None,
                             confidence: str | None = None,
                             work: str | None = None) -> dict:
    """记录角色弧光质变点(写,待批)。
    change_type: ability/relation/personality/composite/belief。

    after_state 按 change_type 填写对应快照键:
      ability     → {"ability_snapshot": {"技能名": "描述", ...}}
      relation    → {"relation_snapshot": {"角色/势力": "关系描述", ...}}
      personality → {"personality_snapshot": "简短描述字符串"}
      composite   → 可同时含 ability_snapshot / relation_snapshot / personality_snapshot
      belief      → 须提供 lie_belief(0-100)，summary 可写 why 依据
    before_state 结构同 after_state,记录变化前状态(可选)。
    lie_belief: 该章结束时对核心错误信念的信奉度(0-100)；belief 类型必填。
    confidence: confirmed|inferred 等，默认 confirmed。
    char_state_at(character_id, chapter) 将按章序累积 after_state 合成时点快照。"""
    if lie_belief is not None:
        if isinstance(lie_belief, bool) or not isinstance(lie_belief, (int, float)) \
                or not (0 <= float(lie_belief) <= 100):
            return {"status": "error", "tool": "s3_add_char_state",
                    "reason": "lie_belief 须为 0-100 的数值"}
        lie_belief = int(lie_belief)
    if change_type == "belief" and lie_belief is None:
        return {"status": "error", "tool": "s3_add_char_state",
                "reason": "change_type=belief 时须提供 lie_belief(0-100)"}
    conf = confidence if confidence is not None else "confirmed"
    ok = await _ask(ctx, f"记录弧光 {character_id} 第{chapter}章 [{change_type}]: {summary[:30]}")
    return commit_if_approved("s3_add_char_state", ok,
                              lambda: _store_for(work).add_char_state(
                                  character_id, chapter, change_type, summary,
                                  before_state=before_state, after_state=after_state,
                                  trigger_event=trigger_event, arc_phase=arc_phase,
                                  affects_voice=affects_voice,
                                  confidence=conf, lie_belief=lie_belief))


@mcp.tool(annotations=_RW)
async def s3_add_arc_beat(ctx: Context, character_id: str, beat_name: str,
                          target_chapter: int,
                          lie_belief_target: int | None = None,
                          trigger_event: str = "",
                          work: str | None = None) -> dict:
    """加弧光里程碑节拍(写,待批)。对齐 REST POST /arc-beats。
    lie_belief_target 若给须 0-100；角色存在性与 REST 同宽(不 404)。"""
    if lie_belief_target is not None:
        if isinstance(lie_belief_target, bool) \
                or not isinstance(lie_belief_target, (int, float)) \
                or not (0 <= float(lie_belief_target) <= 100):
            return {"status": "error", "tool": "s3_add_arc_beat",
                    "reason": "lie_belief_target 须为 0-100 的数值或不传"}
        lie_belief_target = int(lie_belief_target)
    ok = await _ask(
        ctx,
        f"规划弧光里程碑 {character_id}「{beat_name}」→第{target_chapter}章"
        + (f" 信奉度趋{lie_belief_target}" if lie_belief_target is not None else ""))
    return commit_if_approved(
        "s3_add_arc_beat", ok,
        lambda: _store_for(work).add_arc_beat(
            character_id, beat_name, int(target_chapter),
            lie_belief_target, trigger_event or ""))


@mcp.tool(annotations=_RW)
async def s3_delete_arc_beat(ctx: Context, beat_id: str,
                             work: str | None = None) -> dict:
    """删除弧光里程碑(写,待批)。对齐 REST DELETE /arc-beats/{id}：静默删。"""
    ok = await _ask(ctx, f"删除弧光里程碑 {beat_id}")
    return commit_if_approved(
        "s3_delete_arc_beat", ok,
        lambda: _store_for(work).delete_arc_beat(beat_id))


@mcp.tool(annotations=_RW)
async def s3_set_voice_profile(ctx: Context, character_id: str,
                                style_summary: str,
                                catchphrases: list | None = None,
                                tone_rules: list | None = None,
                                ooc_signals: list | None = None,
                                internal_monologue_style: str | None = None,
                                sentence_patterns: dict | None = None,
                                work: str | None = None) -> dict:
    """设置角色声音指纹(写,待批)。9节结构,至少提供 style_summary。
    ooc_signals: [{signal_id, description, detection_method, severity}] 可检测的 OOC 规则。"""
    from scribe3.iceberg import persist_codex_fields_blocked
    _blk = persist_codex_fields_blocked(
        "voice", {"style_summary": style_summary} if style_summary else {},
        mode="incremental",
    )
    if _blk:
        return {"status": "error", "tool": "s3_set_voice_profile", **_blk}
    ok = await _ask(ctx, f"设置声音指纹 {character_id}")
    profile = {"style_summary": style_summary, "catchphrases": catchphrases,
               "tone_rules": tone_rules, "ooc_signals": ooc_signals,
               "internal_monologue_style": internal_monologue_style,
               "sentence_patterns": sentence_patterns, "version": 1}
    return commit_if_approved("s3_set_voice_profile", ok,
                              lambda: _store_for(work).set_voice_profile(character_id, profile))


@mcp.tool(annotations=_RW)
async def s3_add_item(ctx: Context, name: str,
                       category: str | None = None,
                       description: str | None = None,
                       current_owner: str | None = None,
                       symbolic_state: str = "active",
                       special_properties: list | None = None,
                       first_chapter: int | None = None,
                       work: str | None = None) -> dict:
    """添加物品/道具(写,待批)。symbolic_state: active/lost/destroyed/unknown。first_chapter: 首次出现章号。"""
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("item", {
        k: v for k, v in (
            ("description", description), ("current_owner", current_owner),
            ("special_properties", special_properties),
        ) if v is not None
    })
    if _l1:
        return {**_l1, "tool": "s3_add_item"}
    ok = await _ask(ctx, f"添加物品 {name} [{symbolic_state}]")
    return commit_if_approved("s3_add_item", ok,
                              lambda: _store_for(work).add_item(name, category, description,
                                  current_owner, symbolic_state, special_properties,
                                  first_chapter))


@mcp.tool(annotations=_RW)
async def s3_add_term(ctx: Context, name: str,
                       category: str | None = None,
                       definition: str | None = None,
                       aliases: list | None = None,
                       first_mention_chapter: int | None = None,
                       work: str | None = None) -> dict:
    """添加专有名词/术语(写,待批)。含别名列表。first_mention_chapter: 首次出现章号。"""
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("term", {"definition": definition} if definition else {})
    if _l1:
        return {**_l1, "tool": "s3_add_term"}
    ok = await _ask(ctx, f"添加术语 {name}")
    return commit_if_approved("s3_add_term", ok,
                              lambda: _store_for(work).add_term(
                                  name, category, definition, aliases, first_mention_chapter))


@mcp.tool(annotations=_RW)
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
    blob = (text or "").strip()
    if len(blob) < 20:
        return {"status": "error", "tool": "s3_plant_promise", "code": "promise_thin",
                "error": "伏笔正文至少 20 字"}
    if tier in ("book", "arc") and not resolution.strip():
        return {"error": "悬念必须有文档记录的真实答案+预计回收章(tier=chapter 短期悬念豁免)"}
    ok = await _ask(ctx, f"埋伏笔(第{setup_chapter}章·{tier}):{text}")
    return commit_if_approved(
        "s3_plant_promise", ok,
        lambda: _store_for(work).plant_promise(text, setup_chapter, kind=kind, tier=tier,
                                               resolution=resolution))


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
async def s3_advance_promise(ctx: Context, pid: str, payoff_chapter: int,
                             work: str | None = None) -> dict:
    """兑现/回收伏笔(写,待批):status→closed + payoff_chapter。
    弃置请用 s3_abandon_promise;障眼法请用 s3_mark_herring。"""
    ok = await _ask(ctx, f"回收伏笔 {pid}(第{payoff_chapter}章)")
    return commit_if_approved("s3_advance_promise", ok,
                              lambda: _store_for(work).advance_promise(pid, payoff_chapter))


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
async def s3_resolve_voice_flag(ctx: Context, flag_id: str, work: str | None = None) -> dict:
    """关闭声音演变 flag(status: open → done;写,待批)。
    更新声音库后调用此工具标记已处理。flag_id 从 s3_list_voice_flags 获取。"""
    ok = await _ask(ctx, f"关闭声音演变 flag {flag_id}")
    return commit_if_approved("s3_resolve_voice_flag", ok,
                              lambda: _store_for(work).resolve_voice_flag(flag_id))


@mcp.tool(annotations=_RW)
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


def s3_ingest_chapter(seq: int, work: str | None = None, force: bool = False,
                      confirm_token: str | None = None) -> dict:
    """章节回写(客观回写,不待批):读定稿抽"谁新知道什么/做了什么"→更新知识账本。
    非创作虚构(add_fact/add_event 那些经 elicitation);ingest 反映已定稿正文,
    后端 save-chapter 也会自动后台跑同一逻辑。

    经 IngestPolicy + 共享 lease(与 HTTP 同 choke point)。held 且无 force/token → 拒绝。
    force=true 时忽略 hold / 同正文指纹跳过,强制 purge+重抽。
    此工具运行在 Hermes MCP 桥内(单 tool call 上限 300 秒)，所以直连补全必须显式
    小于该上限且禁用内部重试；抽取层最多两次尝试，失败会诚实返回 parse_failed。"""
    from scribe3.llm import hermes_complete
    from scribe3.api.services.ingest_bg import schedule_ingest
    from scribe3.ingest_policy import GateSnapshot

    def bounded_complete(prompt: str) -> str:
        return hermes_complete(
            prompt,
            timeout=90.0,
            max_tokens=1600,
            retries_override=0,
        )

    w = (work or "main").strip() or "main"
    st = _store_for(w)
    ch = st.get_chapter(int(seq)) or {}
    prose = ch.get("prose") or ""
    src = "confirm" if confirm_token else "mcp_ingest"
    out = schedule_ingest(
        st, w, int(seq),
        prose=prose,
        gate=GateSnapshot(path="mcp_ingest", craft_allowed=True, finalize_verdict="pass"),
        force=bool(force),
        source=src,
        mode="sync",
        confirm_token=confirm_token,
        complete_fn=bounded_complete,
        max_attempts=2,
    )
    if out.get("held"):
        return {
            "status": "held",
            "code": "held",
            "seq": seq,
            "hold_reason": out.get("hold_reason") or out.get("reason"),
            "confirm_token": out.get("confirm_token"),
            "prose_fp": out.get("prose_fp"),
            "message": "章处于 ingest hold,传 force=true 或 confirm_token 后重试",
        }
    if out.get("action") == "skip" and out.get("reason") == "lease_busy":
        return {
            "status": "busy",
            "code": "lease_busy",
            "seq": seq,
            "message": "同章 ingest 租约被占用(HTTP/MCP 并发),请稍后重试",
            "lease_owner": out.get("lease_owner"),
        }
    # 透传 ingest 结果字段
    ing = out.get("ingest") or {}
    return {
        "status": "ok" if out.get("action") == "auto" else out.get("action"),
        "seq": seq,
        "action": out.get("action"),
        "reason": out.get("reason"),
        "prose_fp": out.get("prose_fp") or ing.get("prose_fp"),
        "skipped": bool(ing.get("skipped")),
        "parse_failed": bool(ing.get("parse_failed")),
        "distilled": out.get("distilled"),
    }


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
async def s3_supersede_fact(ctx: Context, entity_id: str, attribute: str, value: str,
                             since_chapter: int, secret: bool = False,
                             work: str | None = None) -> dict:
    """演变世界真相（超越）:关闭该 entity+attribute 开区间先驱并写入新值(写,待批)。

    作者话术：请自第 since_chapter 章起，将「entity」的「attribute」演变为 value。
    保留历史段（valid_to），勿用 edit_fact 原地抹历史。
    entity_id: 关于谁（如 role:焦三）；attribute: 哪方面；value: 新内容；
    since_chapter: 新值生效章（同时是先驱 valid_to）；secret: 是否私密。"""
    ok = await _ask(ctx, f"演变真相 {entity_id}·{attribute}={value}(章{since_chapter}起)")
    return commit_if_approved("s3_supersede_fact", ok,
                              lambda: _store_for(work).supersede_fact(
                                  entity_id, attribute, value, since_chapter, secret=secret))


@mcp.tool(annotations=_RW)
async def s3_forget_knowledge(ctx: Context, knower_id: str, proposition_id: str,
                               until_chapter: int, work: str | None = None) -> dict:
    """令知识遗忘:设置知识边的 until_chapter,使其在该章起失效(写,待批)。
    knower_id: 知者 oid(如 role:焦三);proposition_id: 命题 oid(如 fact:治眼);
    until_chapter: 遗忘生效章号(该章及以后不再知道)。"""
    ok = await _ask(ctx, f"令 {knower_id} 在章{until_chapter}起忘记 {proposition_id}")
    return commit_if_approved("s3_forget_knowledge", ok,
                              lambda: _store_for(work).forget_knowledge(
                                  knower_id, proposition_id, until_chapter))


@mcp.tool(annotations=_RW)
async def s3_craft_rule_add(ctx: Context, kind: str, pattern: str, note: str = "",
                            work: str | None = None) -> dict:
    """加一条本书题材 craft 规则(写,待批)。kind=purple_regex|artifact_craft|allow_pattern|allow_word。"""
    ok = await _ask(ctx, f"加题材规则 [{kind}] {pattern}")
    return commit_if_approved("s3_craft_rule_add", ok,
                              lambda: _store_for(work).add_craft_rule(kind, pattern, note))


@mcp.tool(annotations=_RW)
async def s3_author_pref_add(ctx: Context, text: str, work: str | None = None) -> dict:
    """记一条【作者跨书偏好】到 USER.md(写,待批)。只收人级风格倾向(如"偏短句""不煽情"
    "叙事距离偏远");**书内设定/人物/世界观/情节一律禁止**(那是正典,走设定工具)——
    拿不准算不算偏好就不要调用本工具(红线:偏好≠正典,兜底保守)。≤200字。"""
    ok = await _ask(ctx, f"记跨书作者偏好:{text[:80]}")
    from scribe3.author_prefs import append_pref
    return commit_if_approved("s3_author_pref_add", ok, lambda: append_pref(text))


@mcp.tool(annotations=_RW)
async def s3_craft_rule_remove(ctx: Context, rule_id: str, work: str | None = None) -> dict:
    """删一条本书题材 craft 规则(写,待批)。"""
    ok = await _ask(ctx, f"删题材规则 {rule_id}")
    return commit_if_approved("s3_craft_rule_remove", ok,
                              lambda: _store_for(work).delete_craft_rule(rule_id))


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
async def s3_plan_volumes(ctx: Context, work: str | None = None) -> dict:
    """按卷把账立住：每一卷的 intro 要对着该卷每一章各办哪一件。不写节拍，不写正文。"""
    st = _store_for(work)
    outline = st.outline() if hasattr(st, "outline") else {"volumes": [], "chapters": []}
    vols = outline.get("volumes") or []
    chs = outline.get("chapters") or []
    lines = ["请按卷把账立住。每一卷 intro 必须按章写出各办哪一件，禁止只写其中一章的夜。"]
    for v in vols:
        vid = v.get("id")
        peers = [c for c in chs if str(c.get("volume") or "") == str(vid or "")]
        lines.append(f"卷《{v.get('title') or vid}》volume_id={vid} 现有 {len(peers)} 章。")
        for c in peers:
            lines.append(f"  第{c.get('seq')}章《{c.get('title') or ''}》：{(c.get('synopsis') or '还没立要办的事')}")
    ok = await _ask(ctx, "\n".join(lines)[:1500])
    return commit_if_approved("s3_plan_volumes", ok, lambda: {"volumes": len(vols), "planned": True})


@mcp.tool(annotations=_RW)
async def s3_plan_chapter_accounts(ctx: Context, volume_id: str, work: str | None = None) -> dict:
    """只给这一卷的每一章立一句话账（梗概）。不写戏，不写正文。"""
    if not str(volume_id or "").strip():
        return {"status": "error", "code": "volume_required", "message": "一次只给一卷立账，请点名 volume_id。"}
    ok = await _ask(ctx, f"给卷 {volume_id} 的每一章立一句话账（谁、在哪、办成什么）。不写戏。")

    def _write():
        st = _store_for(work)
        outline = st.outline() if hasattr(st, "outline") else {"chapters": []}
        seqs = [c.get("seq") for c in (outline.get("chapters") or [])
                if str(c.get("volume") or "") == str(volume_id)]
        return {"volume_id": volume_id, "seqs": seqs, "note": "账目由主编按章补进 synopsis，本工具只锁定这一卷。"}

    return commit_if_approved("s3_plan_chapter_accounts", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_refine_volume_outline(ctx: Context, volume_id: str, intro: str, work: str | None = None) -> dict:
    """重写这一卷的卷纲。必须按章列出各办哪一件。"""
    if not str(volume_id or "").strip():
        return {"status": "error", "code": "volume_required", "message": "请点名要改的那一卷。"}
    if not str(intro or "").strip():
        return {"status": "error", "code": "intro_required", "message": "请写出这一卷每一章各办哪一件。"}
    ok = await _ask(ctx, f"改卷纲 {volume_id}：{intro[:400]}")

    def _write():
        st = _store_for(work)
        if not st.update_volume(volume_id, {"intro": intro}):
            return False
        return {"volume_id": volume_id, "intro_len": len(intro)}

    return commit_if_approved("s3_refine_volume_outline", ok, _write)


def _structure_mode_or_error(st) -> dict | None:
    try:
        intent = st.get_intent() or {}
    except Exception:
        intent = {}
    if intent.get("structure_mode"):
        return None
    return {
        "status": "error",
        "http": 422,
        "code": "structure_mode_off",
        "message": "这本书没打开长篇结构。",
    }


@mcp.tool(annotations=_RW)
async def s3_add_arc_unit(
    ctx: Context, volume_id: str, seq: int, title: str,
    goal: str | None = None, work: str | None = None,
) -> dict:
    st = _store_for(work)
    off = _structure_mode_or_error(st)
    if off:
        return off
    ok = await _ask(ctx, f"给卷 {volume_id} 加情节单元 {seq}《{title}》")
    return commit_if_approved(
        "s3_add_arc_unit", ok,
        lambda: st.add_arc_unit(volume_id, seq, title, goal=goal or ""),
    )


@mcp.tool(annotations=_RW)
async def s3_expand_arc_window(ctx: Context, volume_id: str, work: str | None = None) -> dict:
    st = _store_for(work)
    off = _structure_mode_or_error(st)
    if off:
        return off
    ok = await _ask(ctx, f"只铺卷 {volume_id} 眼前这一段和接下来一段，不铺全书")
    return commit_if_approved(
        "s3_expand_arc_window", ok,
        lambda: {"volume_id": volume_id, "window": "current_and_next", "status": "draft"},
    )


@mcp.tool(annotations=_RW)
async def s3_settle_arc_event(
    ctx: Context, volume_id: str, unit_seq: int, event_id: str, done_seq: int,
    work: str | None = None,
) -> dict:
    st = _store_for(work)
    off = _structure_mode_or_error(st)
    if off:
        return off
    ok = await _ask(ctx, f"记下第{done_seq}章办的是单元{unit_seq}的 {event_id}")
    return commit_if_approved(
        "s3_settle_arc_event", ok,
        lambda: st.settle_arc_event(volume_id, unit_seq, event_id, done_seq),
    )


@mcp.tool(annotations=_RW)
async def s3_batch_stage(
    ctx: Context,
    volume_id: str,
    stage: str,
    work: str | None = None,
    persist: bool = True,
) -> dict:
    """只给这一卷批跑责任或戏。禁止演绎/草稿/正文，禁止一次全书。"""
    from scribe3.playbook.stages import normalize_stage
    stg = normalize_stage(stage)
    if stg not in ("duty", "design"):
        return {
            "status": "error",
            "http": 422,
            "code": "batch_stage_forbidden",
            "message": "一次只跑一卷的责任和戏，不写演绎和正文。",
        }
    if not str(volume_id or "").strip():
        return {"status": "error", "http": 422, "code": "volume_required", "message": "请点名这一卷。"}
    ok = await _ask(ctx, f"给卷 {volume_id} 批跑 {stg}（只这一卷，不写正文）")

    def _write():
        st = _store_for(work)
        outline = st.outline() if hasattr(st, "outline") else {"chapters": []}
        seqs = [int(c.get("seq")) for c in (outline.get("chapters") or [])
                if str(c.get("volume") or "") == str(volume_id) and c.get("seq") is not None]
        if not seqs:
            return {"volume_id": volume_id, "stage": stg, "seqs": [], "note": "这一卷还没有章。"}
        from scribe3.stage_generate import thicken_stage, STAGE_MAX_TOKENS
        results = []
        for seq in seqs:
            ch = st.get_chapter(int(seq)) or {}
            def llm_fn(prompt, max_tokens=STAGE_MAX_TOKENS.get(stg, 4096), **kwargs):
                from scribe3.api.services.misc_helpers import _pilot_llm_gen
                return _pilot_llm_gen(
                    st, work or "main", int(seq), stg, prompt,
                    max_tokens=max_tokens, system=kwargs.get("system"),
                )
            out = thicken_stage(
                stg, ch, llm_fn=llm_fn, persist_fn=None, seq=int(seq), st=st, work=work or "main",
            )
            results.append({"seq": int(seq), "ok": bool(out.get("ok")), "code": out.get("code") or out.get("status")})
        return {"volume_id": volume_id, "stage": stg, "results": results}

    return commit_if_approved("s3_batch_stage", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_add_chapter(ctx: Context, title: str = "",
                         volume_id: str | None = None,
                         work: str | None = None) -> dict:
    """新建空章(写,待批)。seq=历史最大章号+1;可选挂到 volume_id。"""
    ok = await _ask(ctx, f"新建章《{title or '未命名'}》vol={volume_id}")

    def _write():
        return _store_for(work).create_chapter(title=title, volume_id=volume_id)

    return commit_if_approved("s3_add_chapter", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_patch_chapter_meta(
    ctx: Context, seq: int,
    title: str | None = None,
    label: str | None = None,
    volume_id: str | None = None,
    clear_volume: bool = False,
    prose_lock: bool | None = None,
    synopsis: str | None = None,
    confidence: str | None = None,
    work: str | None = None,
) -> dict:
    """改章身份元数据(标题/标签/卷归属/定稿锁/梗概/把握;写,待批)。不改 beats/prose。

    synopsis=None 表示不改;空白字符串拒绝。clear_volume=True 时清空卷归属。
    confidence 只收 high/low：high=改纲后要人看一眼，low=改纲后先拦住演绎/草稿。
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
    if prose_lock is not None:
        fields["prose_lock"] = bool(prose_lock)
    if synopsis is not None:
        syn = str(synopsis)
        if not syn.strip():
            return {
                "status": "error", "tool": "s3_patch_chapter_meta",
                "code": "synopsis_blank", "error": "梗概不能是空白",
            }
        fields["synopsis"] = syn
    if confidence is not None:
        c = str(confidence).strip().lower()
        if c not in ("high", "low"):
            return {
                "status": "error", "tool": "s3_patch_chapter_meta",
                "code": "confidence_invalid", "error": "把握只能标 high 或 low",
            }
        fields["confidence"] = c
    if not fields:
        return {"status": "noop", "tool": "s3_patch_chapter_meta", "reason": "no fields"}
    ok = await _ask(ctx, f"改第{seq}章 {list(fields)}")

    def _write():
        st = _store_for(work)
        if not st.update_chapter_meta(seq, fields):
            return False
        return {"seq": seq, "fields": list(fields)}

    return commit_if_approved("s3_patch_chapter_meta", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_refreeze_chapter(ctx: Context, seq: int, work: str | None = None) -> dict:
    """核对完这一章的纲，冻回去。之后才能写演绎和草稿。已经冻着的再调一次不算错。"""
    ok = await _ask(ctx, f"把第{seq}章的纲冻回去")

    def _write():
        from scribe3.outline_status import refreeze_chapter
        out = refreeze_chapter(_store_for(work), int(seq))
        if not out.get("ok"):
            return False
        return {"seq": int(seq), **out}

    return commit_if_approved("s3_refreeze_chapter", ok, _write)


async def s3_patch_chapter_plan(
    ctx: Context, seq: int,
    synopsis: str | None = None,
    beats: list[dict[str, Any] | str] | None = None,
    scene_truth: str | None = None,
    deductions: list[dict[str, Any]] | None = None,
    involved_characters: list[str] | None = None,
    story_move_plan: dict | None = None,
    narrative_contract: dict | None = None,
    reveal_secret_ids: list[str] | None = None,
    chapter_spine: dict | None = None,
    work: str | None = None,
) -> dict:
    """已废。请改用 s3_generate_stage 或 s3_patch_play / s3_patch_contract。"""
    return {
        "status": "error",
        "http": 410,
        "code": "stage_gone",
        "tool": "s3_patch_chapter_plan",
        "error": "s3_patch_chapter_plan 的 spine/beats 已废。请改用 s3_generate_stage(stage=duty|design|deduce|draft|final) 或人工 s3_patch_play / s3_patch_contract（仍需法官复审才能冻结）。",
    }


@mcp.tool(annotations=_RW)
async def s3_patch_play(
    ctx: Context, seq: int, text: str, work: str | None = None,
) -> dict:
    """人工改戏。法官过审后冻结为新版本，旧冻结戏与下游一并作废。"""
    ok = await _ask(ctx, f"人工改第{seq}章戏并送审")

    def _write():
        st = _store_for(work)
        from scribe3.playbook.pipeline import review_and_freeze_play

        def llm_fn(prompt, max_tokens=2048, **_kw):
            from scribe3.api.services.misc_helpers import _pilot_llm_gen
            return _pilot_llm_gen(st, work or "main", int(seq), "design", prompt, max_tokens=max_tokens)

        out = review_and_freeze_play(st, int(seq), text, llm_fn=llm_fn, persist=True)
        if not out.get("ok"):
            return {"status": "error", "tool": "s3_patch_play", **out}
        return {"status": "written", "tool": "s3_patch_play", "seq": int(seq), **out}

    return commit_if_approved("s3_patch_play", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_patch_contract(
    ctx: Context, seq: int, contract: dict, work: str | None = None,
) -> dict:
    """人工指定契约 quote。写入 draft，须再走 design 法官才能冻结。"""
    ok = await _ask(ctx, f"人工改第{seq}章契约")

    def _write():
        st = _store_for(work)
        play = st.get_frozen("chapter_play", int(seq)) if hasattr(st, "get_frozen") else None
        if not play:
            return {"status": "error", "tool": "s3_patch_contract", "error": "还没有冻结的戏"}
        from scribe3.playbook.structural import check_contract_struct
        hit = check_contract_struct(contract, play.get("text") or "")
        if not hit.get("ok"):
            return {"status": "error", "tool": "s3_patch_contract", **hit}
        from scribe3.playbook.quote import PLAYBOOK_VERSION
        rec = dict(contract)
        rec.update({
            "seq": int(seq), "status": "draft", "play_sha": play.get("sha"),
            "schema": "chapter_contract.v1", "playbook_version": PLAYBOOK_VERSION,
            "version": st.next_version("chapter_contract", int(seq)) if hasattr(st, "next_version") else 1,
        })
        if hasattr(st, "insert"):
            st.insert("chapter_contract", rec)
        return {"status": "written", "tool": "s3_patch_contract", "seq": int(seq), "note": "仍需法官复审才能冻结"}

    return commit_if_approved("s3_patch_contract", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_save_chapter_draft(
    seq: int, draft: str, work: str | None = None,
) -> dict:
    """落/覆盖某章排演稿 chapter.draft（≠ prose）。空稿拒绝；字数不是通过条件。不经 elicitation。"""
    from scribe3.iceberg import cn_len
    n = cn_len(draft)
    if not (draft or "").strip():
        return {
            "status": "error",
            "tool": "s3_save_chapter_draft",
            "code": "empty_draft",
            "error": "排演稿为空，禁止把空稿存进 chapter.draft",
        }
    st = _store_for(work)
    st.save_chapter_draft(int(seq), draft or "")
    return {"status": "ok", "tool": "s3_save_chapter_draft", "seq": int(seq), "cn": n}


@mcp.tool(annotations=_RW)
async def s3_generate_stage(
    ctx: Context,
    seq: int,
    stage: str,
    persist: bool = False,
    extra: str = "",
    work: str | None = None,
    brief_only: bool = False,
    force: bool = False,
    rewrite: bool = False,
    focalizer: str | None = None,
) -> dict:
    """五层管线：duty / design / deduce / draft / final。"""
    from scribe3.stage_generate import (
        STAGE_MAX_TOKENS,
        dispatch_design_stage,
        normalize_stage,
        resolve_stage_focalizer,
        thicken_stage,
    )
    from scribe3.playbook.stages import extra_authors, reject_gone_stage
    stg = normalize_stage(stage)
    gone = reject_gone_stage(stg)
    if gone:
        return {"status": "error", "http": 410, "tool": "s3_generate_stage", **gone}
    if stg not in ("duty", "design", "deduce", "draft", "final"):
        return {"status": "error", "tool": "s3_generate_stage", "error": f"未知阶段 {stage}"}
    if force and "force=1" not in (extra or ""):
        extra = ((extra or "") + " force=1").strip()
    if rewrite and "rewrite=1" not in (extra or ""):
        extra = ((extra or "") + " rewrite=1").strip()
    st = _store_for(work)
    ch = st.get_chapter(int(seq)) or {}
    foc = resolve_stage_focalizer(focalizer, ch)
    if persist and stg == "final" and bool((ch or {}).get("prose_lock")) and not brief_only:
        return {
            "status": "error",
            "tool": "s3_generate_stage",
            "code": "prose_locked",
            "error": "本章定稿已锁，禁止覆盖正文。",
        }
    if extra_authors(extra or ""):
        return {
            "status": "error",
            "tool": "s3_generate_stage",
            "code": "extra_authors",
            "missing": ["extra_authors"],
            "error": "extra 不得当作者：禁止「必须原样 / 必须有一句 / 必须以时空」",
        }
    hit = dispatch_design_stage(stg, ch, extra=extra or "")
    if hit is not None:
        if hit.get("ok") is False:
            return {
                "status": "error",
                "tool": "s3_generate_stage",
                "error": hit.get("message") or hit.get("code"),
                **hit,
            }
        return {"status": "ok", "tool": "s3_generate_stage", **hit}

    def llm_fn(prompt, max_tokens=STAGE_MAX_TOKENS.get(stg, 4096), **kwargs):
        from scribe3.api.services.misc_helpers import _pilot_llm_gen
        return _pilot_llm_gen(
            st, work or "main", int(seq), stg, prompt,
            max_tokens=max_tokens, system=kwargs.get("system"),
        )

    persist_fn = None
    if persist and stg == "draft":
        def persist_fn(fields: dict) -> None:
            st.save_chapter_draft(int(seq), fields.get("draft") or "")
    if persist and stg == "final":
        def persist_fn(fields: dict) -> None:
            if fields.get("prose"):
                st.save_chapter(int(seq), fields.get("prose") or "")
    if persist and stg not in ("draft", "final"):
        if bool((ch or {}).get("prose_lock")) and not brief_only:
            return {
                "status": "error",
                "tool": "s3_generate_stage",
                "code": "prose_locked",
                "error": "本章定稿已锁，请用 brief_only 只写章纲",
            }
    from scribe3.pipeline_trace_hooks import finish_failed, finish_ok, open_write_chain
    from scribe3.stage_generate import _emit_fate_artifacts
    mt: dict = {}
    open_write_chain(st, mt, work=work or "main", chapter=int(seq), kind="write", phase=stg)
    try:
        out = thicken_stage(
            stg, ch, llm_fn=llm_fn, persist_fn=persist_fn,
            seq=int(seq), extra=extra or "",
            st=st, work=work, focalizer=foc,
        )
    except Exception as exc:
        try:
            finish_failed(st, mt, err=exc)
        except Exception:
            pass
        raise
    try:
        _emit_fate_artifacts(stg, out, dict(out or {}), {**(ch or {}), **(out or {})})
        fr: list[str] = []
        for x in (out or {}).get("fail_reasons") or []:
            if x and str(x) not in fr:
                fr.append(str(x))
        ok = bool((out or {}).get("ok") or (out or {}).get("skipped"))
        if not ok and not fr:
            fr = [str((out or {}).get("code") or "needs_human")]
        finish_ok(
            st, mt,
            extra={"fail_reasons": fr} if fr else None,
            status="ok" if ok else "failed",
        )
    except Exception:
        pass
    status = "ok" if out.get("ok") or out.get("skipped") else "error"
    return {"status": status, "tool": "s3_generate_stage", "seq": int(seq), **out}


def _codex_llm_fn(st, work: str | None, kind: str):
    def llm_fn(prompt, max_tokens=4096, **kwargs):
        from scribe3.api.services.misc_helpers import _pilot_llm_gen
        return _pilot_llm_gen(
            st, work or "main", 1, kind, prompt,
            max_tokens=max_tokens, system=kwargs.get("system"),
        )
    return llm_fn


@mcp.tool(annotations=_RW)
async def s3_generate_codex(
    ctx: Context,
    kind: str,
    name: str,
    persist: bool = False,
    extra: str = "",
    include_secret: bool = False,
    force: bool = False,
    work: str | None = None,
) -> dict:
    """按合同 LLM 写厚一张设定卡。persist=true 待批落库；false 只回厚稿。"""
    from scribe3.codex_generate import (
        apply_codex_persist_fields, load_codex_row, persist_codex_row, thicken_codex,
    )
    st = _store_for(work)
    row = load_codex_row(st, kind, name) or {"name": name}
    out = thicken_codex(
        kind, row, llm_fn=_codex_llm_fn(st, work, kind), extra=extra or "",
        force=force, include_secret=bool(include_secret), st=st, work=work, name=name,
    )
    if not persist:
        return {"status": "ok" if out.get("ok") or out.get("skipped") else "error",
                "tool": "s3_generate_codex", **out}
    if not out.get("ok") or out.get("skipped"):
        return {"status": "ok" if out.get("skipped") else "error", "tool": "s3_generate_codex", **out}
    try:
        fields = apply_codex_persist_fields(
            kind,
            out.get("public_fields"),
            out.get("secret_fields") if include_secret else {},
            out.get("chief_only_fields") if include_secret else {},
        )
    except ValueError as e:
        return {"status": "error", "tool": "s3_generate_codex",
                "code": "deprecated_field", "error": str(e)}
    ok = await _ask(ctx, f"生成并落库 {kind}:{name}")

    def _write():
        if not persist_codex_row(st, kind, name, fields):
            return False
        return {"kind": kind, "name": name, "source": "llm"}

    gated = commit_if_approved("s3_generate_codex", ok, _write)
    if isinstance(gated, dict):
        gated["generated"] = {k: out.get(k) for k in ("cn", "ok", "public_fields")}
    return gated


@mcp.tool(annotations=_RW)
async def s3_generate_codex_batch(
    ctx: Context,
    kinds: list[str] | None = None,
    persist: bool = False,
    force: bool = False,
    extra: str = "",
    include_secret: bool = False,
    offset: int = 0,
    max_items: int = 50,
    work: str | None = None,
) -> dict:
    """批量写厚本书 stub/thin。persist=true 过闸直接落库，无需批准。"""
    from scribe3.codex_generate import thicken_codex_batch
    st = _store_for(work)
    out = thicken_codex_batch(
        st, llm_fn=_codex_llm_fn(st, work, "batch"), persist=bool(persist),
        kinds=kinds, force=force, extra=extra or "",
        include_secret=bool(include_secret), offset=int(offset or 0),
        max_items=int(max_items or 50), work=work,
    )
    return {"tool": "s3_generate_codex_batch", **out}


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
async def s3_add_motif(ctx: Context, name: str, theme: str = "",
                       echoes: str = "", unfolding: str = "",
                       work: str | None = None) -> dict:
    """新建母题(写,待批)。"""
    n = (name or "").strip()
    if not n:
        return {"status": "error", "tool": "s3_add_motif", "error": "name required"}
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("motif", {k: v for k, v in (
        ("theme", theme), ("echoes", echoes), ("unfolding", unfolding),
    ) if v})
    if _l1:
        return {**_l1, "tool": "s3_add_motif"}
    ok = await _ask(ctx, f"新建母题「{n}」")

    def _write():
        _store_for(work).add_motif(n, theme=theme or "", echoes=echoes or "",
                                   unfolding=unfolding or "")
        return {"name": n, "theme": theme or ""}

    return commit_if_approved("s3_add_motif", ok, _write)


@mcp.tool(annotations=_RW)
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
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("faction", fields)
    if _l1:
        return {**_l1, "tool": "s3_patch_faction"}
    ok = await _ask(ctx, f"更正势力「{n}」:{','.join(fields)}")

    def _write():
        st = _store_for(work)
        if not st.get_faction(n):
            return False
        st.add_faction(n, **fields)
        return {"name": n, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_faction", ok, _write)


@mcp.tool(annotations=_RW)
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
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("item", fields)
    if _l1:
        return {**_l1, "tool": "s3_patch_item"}
    ok = await _ask(ctx, f"更正物品「{n}」")

    def _write():
        if not _store_for(work).patch_item(n, fields):
            return False
        return {"name": n, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_item", ok, _write)


@mcp.tool(annotations=_RW)
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
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("term", fields)
    if _l1:
        return {**_l1, "tool": "s3_patch_term"}
    ok = await _ask(ctx, f"更正术语「{n}」")

    def _write():
        if not _store_for(work).patch_term(n, fields):
            return False
        return {"name": n, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_term", ok, _write)


@mcp.tool(annotations=_RW)
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
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("world_rule", fields)
    if _l1:
        return {**_l1, "tool": "s3_patch_world_rule"}
    ok = await _ask(ctx, f"更正世界规则「{n}」")

    def _write():
        if not _store_for(work).patch_world_rule(n, fields):
            return False
        return {"name": n, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_world_rule", ok, _write)


@mcp.tool(annotations=_RW)
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
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error(k, changes)
    if _l1:
        return {**_l1, "tool": "s3_patch_codex"}
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


@mcp.tool(annotations=_RW)
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
    from scribe3.iceberg import codex_l1_error
    _l1 = codex_l1_error("motif", {k: fields[k] for k in (
        "theme", "echoes", "echo_terms", "unfolding",
    ) if k in fields})
    if _l1:
        return {**_l1, "tool": "s3_patch_motif"}
    ok = await _ask(ctx, f"更正母题 {mid}")

    def _write():
        if not _store_for(work).patch_motif(mid, fields):
            return False
        return {"motif_id": mid, "patched": list(fields.keys())}

    return commit_if_approved("s3_patch_motif", ok, _write)


@mcp.tool(annotations=_RW)
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


@mcp.tool(annotations=_RW)
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
            if not st.promise_exists(oid):
                return False
            st.delete_promise_record(oid)
            return {"object_type": ot, "object_id": oid, "action": "delete"}
        if ot == "motif":
            row = st.get_motif(oid)
            if not row:
                return False
            st.delete_motif(row["id"])
            return {"object_type": ot, "object_id": row["id"], "action": "delete"}
        return {"error": f"unsupported object_type {ot!r}"}

    return commit_if_approved("s3_delete_codex", ok, _write)

