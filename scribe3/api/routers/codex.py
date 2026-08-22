"""Domain router (extracted from app_impl). URLs unchanged."""
from __future__ import annotations

import types
from typing import Any, Optional, List, Dict, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    Body,
    Header,
    Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

router = APIRouter(tags=['codex'])


# Import app_impl constants/models used as signature defaults (late-safe for helpers).
def _import_core_defaults():
    from scribe3.api import app_impl as core
    g = globals()
    for k, v in core.__dict__.items():
        if k.startswith('__'):
            continue
        if k not in g:
            g[k] = v
try:
    _import_core_defaults()
except Exception:
    pass  # core may be partially init during first import cycle


def _codex_l1_http(kind: str, submitted: dict | None) -> None:
    """REST emergency 写口与 MCP 同 L1：薄字段 422，空/缺评则放行。"""
    from scribe3.iceberg import persist_codex_fields_blocked
    hit = persist_codex_fields_blocked(kind, submitted or {}, mode="incremental")
    if hit:
        raise HTTPException(status_code=422, detail=hit)


def facts(
    chapter: int = Query(ge=1),
    work: str = "main",
    reveal_secret: bool = False,
    entity: str | None = Query(default=None),
    include_closed: bool = Query(default=False),
    with_knowers: bool = Query(default=False),
):
    """本章有效命题（PR-4 扩展 entity / include_closed / with_knowers）。

    兼容矩阵：
    - 仅 chapter：同现网 facts_at + D4 + source/bucket 增量
    - chapter + entity + include_closed=false：open ∩ entity（D4 后再滤 entity）
    - chapter + entity + include_closed=true：list_entity_truth_history（**不**经 D4）
    - include_closed=true 且无 entity → 422
    - with_knowers：为 open 行附 knowers / reader_knows（禁止 graph ego）
    """
    st = _store_for(work)
    ent = (entity or "").strip() or None
    if include_closed and not ent:
        raise HTTPException(
            status_code=422,
            detail="include_closed=true 必须带 entity（禁止全表历史扫描）",
        )

    if ent and include_closed:
        rows = st.list_entity_truth_history(ent, chapter, include_closed=True)
        items = [_fact_item(r, reveal_secret=reveal_secret) for r in rows]
    elif ent:
        # 当前态 + D4，再按 entity 过滤
        fs = [f for f in st.facts_at(chapter) if (f.entity_id or "") == ent]
        items = _facts(fs, reveal_secret=reveal_secret)
    else:
        items = _facts(st.facts_at(chapter), reveal_secret=reveal_secret)

    if with_knowers:
        st.attach_knowers_to_fact_items(items, chapter, fill_closed=False)
    return items


def get_fact(local: str, work: str = "main", reveal_secret: bool = False):
    """单条命题全字段读回(批E-A1②)。含 valid_from/valid_to/leak_markers/is_secret,
    让在库 leak_markers 等私密字段可安全编辑(reveal_secret=true 解锁真 value/leak_markers)。
    PR-4: source / bucket。不存在 → 404。"""
    st = _store_for(work)
    f = st.fact(f"fact:{local}")
    if f is None:
        raise HTTPException(status_code=404, detail=f"命题 fact:{local} 不存在")
    item = _fact_item(f, reveal_secret=reveal_secret)
    # 软归档旗标:前端删批后轮询据此视为「已撤下」
    try:
        if hasattr(st, "get_proposition_archived"):
            item["archived"] = bool(st.get_proposition_archived(local))
        else:
            item["archived"] = False
    except Exception:
        item["archived"] = False
    return item


def get_fact_knowers(
    local: str,
    chapter: int = Query(ge=1),
    work: str = "main",
):
    """单命题知情列表（PR-4）。不返回 value / leak_markers。"""
    st = _store_for(work)
    f = st.fact(f"fact:{local}")
    if f is None:
        raise HTTPException(status_code=404, detail=f"命题 fact:{local} 不存在")
    return {
        "fact_id": f"fact:{local}",
        "chapter": int(chapter),
        "knowers": st.list_knowers_for_proposition(local, chapter),
        "reader_knows": st.reader_knows_at_chapter(local, chapter),
    }

def add_char(c: CharIn, work: str = "main"):
    # 掩码写哨兵:backstory 收到掩码占位符 → 视为未提供(不落库为字面掩码值)。
    backstory = None if c.backstory == _SECRET_MASK else c.backstory
    _codex_l1_http("character", {"backstory": backstory} if backstory else {})
    _store_for(work).add_entity(Entity(
        f"role:{c.name}", "character", c.name,
        traits={"backstory": backstory, "backstory_secret": c.backstory_secret,
                "personality_tags": c.personality_tags, "aliases": c.aliases,
                "gender": c.gender or ""}))
    return {"ok": True, "oid": f"role:{c.name}"}

def get_char(local: str, work: str = "main", reveal_secret: bool = False):
    """单条角色档案(设定详情禁止全表扫 entities)。不存在 → 404。"""
    st = _store_for(work)
    # 档案详情：走 store 公开 API（EH-05）
    if hasattr(st, "get_character_archive_row"):
        r = st.get_character_archive_row(local)
    else:
        r = None
    if not r:
        raise HTTPException(status_code=404, detail=f"character '{local}' 不存在")
    d = {
        "id": f"role:{r.get('local') or local}", "kind": "character", "name": r.get("name"),
        "backstory": r.get("backstory"),
        "backstory_secret": r.get("backstory_secret", False),
        "importance": r.get("importance"),
        "appearance": r.get("appearance"),
        "personality_tags": r.get("personality_tags"),
        "aliases": r.get("aliases") or [],
        "personality_detail": r.get("personality_detail"),
        "abilities": r.get("abilities"),
        "weaknesses": r.get("weaknesses"),
        "first_appearance": r.get("first_appearance"),
        "surface_goal": r.get("surface_goal"),
        "deep_need": r.get("deep_need"),
        "internal_conflict": r.get("internal_conflict"),
        "fear": r.get("fear"),
        "gender": r.get("gender") or "",
        "archived": bool(r.get("archived")),
    }
    from scribe3.iceberg import attach_codex_ready
    ready_src = dict(d)
    d = _mask_field(d, "backstory", "backstory_secret", reveal_secret)
    return attach_codex_ready("character", d, evaluate_from=ready_src)

def edit_char(local: str, c: CharIn, work: str = "main"):
    st = _store_for(work)
    # 掩码写哨兵:backstory 收到掩码占位符 → 置 None(下方 None 过滤剔除)= 视为未改,不覆盖库中真值。
    backstory = None if c.backstory == _SECRET_MASK else c.backstory
    fields = {"name": c.name, "backstory": backstory, "backstory_secret": c.backstory_secret,
              "importance": c.importance,
              "appearance": c.appearance, "personality_detail": c.personality_detail,
              "personality_tags": c.personality_tags, "aliases": c.aliases,
              "abilities": c.abilities, "weaknesses": c.weaknesses,
              "surface_goal": c.surface_goal, "deep_need": c.deep_need,
              "internal_conflict": c.internal_conflict, "fear": c.fear,
              "first_appearance": c.first_appearance, "gender": c.gender}
    written = {k: v for k, v in fields.items() if v is not None}
    from scribe3.iceberg import persist_codex_fields_blocked
    _blk = persist_codex_fields_blocked("character", written, mode="incremental")
    if _blk:
        raise HTTPException(status_code=422, detail=_blk)
    st.update_record(f"role:{local}", written)
    return {"ok": True}

def del_char(local: str, confirm_impact_token: str | None = None, work: str = "main"):
    return _delete_object_with_lifecycle(
        _store_for(work), "role", local, work, confirm_impact_token)

def add_fact_ep(f: FactIn, work: str = "main"):
    import uuid
    oid = f"fact:{uuid.uuid4().hex[:8]}"
    # REST 直写视为作者路径 source=author（正典路径优先 supersede）
    _store_for(work).add_fact(Fact(
        oid, f.entity, f.attribute, f.value, f.valid_from,
        valid_to=f.valid_to, secret=f.secret,
        leak_markers=f.leak_markers, source="author",
    ))
    return {"ok": True, "oid": oid}

def edit_fact(local: str, f: FactIn, work: str = "main"):
    """PR-9 · emergency：默认拒绝原地 PATCH，防抹历史。

    正典改值请用 POST /facts/supersede 或 MCP s3_supersede_fact。
    仅当环境变量 SCRIBE3_ALLOW_FACT_EDIT=1 时允许 emergency 原地改。
    见 docs/plans/2026-08-09-proposition-full-chain-optimization.md · PR-9。
    """
    import os
    allow = (os.environ.get("SCRIBE3_ALLOW_FACT_EDIT") or "0").strip().lower() in (
        "1", "true", "yes", "on",
    )
    if not allow:
        raise HTTPException(
            status_code=410,
            detail=(
                "edit_fact 已降级为 emergency："
                "请用 POST /facts/supersede（或 s3_supersede_fact）保留时态历史。"
                "确需原地改写时设置 SCRIBE3_ALLOW_FACT_EDIT=1。"
            ),
        )
    st = _store_for(work)
    st.update_record(f"fact:{local}", {
        "entity_id": f.entity,
        "attribute": f.attribute,
        "value": f.value,
        "valid_from": f.valid_from,
        "valid_to": f.valid_to,
        "secret": f.secret,
        "leak_markers": f.leak_markers,
    })
    # value 变更后重建 embedding,保持语义召回向量与当前值对齐
    try:
        st.semantic_index(f"fact:{local}", f.value)
    except Exception as _e:
        logging.getLogger("scribe3.app").warning(
            "edit_fact: 重建 embedding 失败,命题 fact:%s 将指向旧向量: %s", local, _e)
    return {"ok": True}

def del_fact(local: str, confirm_impact_token: str | None = None, work: str = "main"):
    return _delete_object_with_lifecycle(
        _store_for(work), "fact", local, work, confirm_impact_token)

def supersede_fact_ep(s: SupersedeIn, work: str = "main"):
    new_oid = _store_for(work).supersede_fact(
        s.entity_id, s.attribute, s.value, s.since_chapter, secret=s.secret)
    return {"ok": True, "oid": new_oid}

def list_rules(category: str | None = None, work: str = "main"):
    return _store_for(work).list_world_rules(category)

def get_rule(name: str, work: str = "main"):
    row = _store_for(work).get_world_rule(name)
    if not row:
        raise HTTPException(status_code=404, detail=f"world_rule '{name}' 不存在")
    from scribe3.iceberg import attach_codex_ready
    return attach_codex_ready("world_rule", dict(row))

def add_rule(r: RuleIn, work: str = "main"):
    if r.scope not in _WORLD_RULE_SCOPES:
        raise HTTPException(status_code=422,
                            detail=f"非法 scope='{r.scope}'(合法: {sorted(_WORLD_RULE_SCOPES)})")
    _codex_l1_http("world_rule", {k: v for k, v in (
        ("cost", r.cost), ("source", r.source),
        ("limitations", r.limitations), ("exceptions", r.exceptions),
        ("capabilities", r.capabilities),
    ) if v is not None})
    _store_for(work).add_world_rule(r.name, r.category, r.source, r.capabilities, r.cost,
                                     r.limitations, r.exceptions, r.scope,
                                     r.established_chapter, r.note)
    return {"ok": True}

def del_rule(name: str, work: str = "main"):
    _store_for(work).delete_world_rule(name)
    return {"ok": True}

def get_faction_ep(name: str, work: str = "main", reveal_secret: bool = False):
    """单条势力(设定详情 O(1))。"""
    row = _store_for(work).get_faction(name)
    if not row:
        raise HTTPException(status_code=404, detail=f"faction '{name}' 不存在")
    out = dict(row)
    for k in codex_secret_capable_keys("faction"):
        out = _mask_field(out, k, codex_secret_flag_key(k), reveal_secret)
    if "name" not in out:
        out["name"] = name
    from scribe3.iceberg import attach_codex_ready
    return attach_codex_ready("faction", out, evaluate_from=dict(row))

def list_factions(work: str = "main", reveal_secret: bool = False):
    rows = _store_for(work).list_factions()
    result = []
    for r in rows:
        row = dict(r)
        for k in codex_secret_capable_keys("faction"):
            row = _mask_field(row, k, codex_secret_flag_key(k), reveal_secret)
        result.append(row)
    return result

def add_faction_ep(fc: FactionIn, work: str = "main"):
    """势力 upsert:真 merge 语义(端点层,CX-Task 3 注册表驱动)。

    - exclude_unset:客户端未显式提交的字段一律不传给 store;store.add_faction(Task 2)
      的 `_UNSET` 哨兵保证 MERGE 不触碰旧值,这里不必再像旧版那样手工 pick() 回填全部字段。
    - 掩码写哨兵通用循环(防数据毁灭):任意 secret_capable 字段整行回传掩码占位符
      "🔒 私密" → 视为未改,丢弃(不落库为字面掩码)。旧代码只 pop 了 private_operation
      一个字段——新增 secret 字段若不进这个通用循环,前端整行回传掩码值就会把库里真相
      永久写死成字面 "🔒 私密"(已用测试实证复现,见 test_codex_faction.py ②)。
    - 白名单前置(未知字段 → 422):sent 先按 codex_schema.all_storage_keys('faction')
      过滤,未注册的键当场 422 并列出键名。不能指望 `**sent` 展开后由 store 的白名单去拒:
      键名若撞上方法签名的保留字(实测 `"self"`)会先抛 `TypeError`——不是 ValueError,
      躲过下面的异常映射 → 裸 500。前置过滤同时也免疫未来 store 签名变化引入的新保留字。
    - 取值校验(_field_violations):非法枚举值、array<object> 元素非对象、array<string>
      元素非字符串 → 422。这些 pydantic 拦不住(元素不带类型),漏过去就会在 DB 层
      coercion 失败炸成裸 500。
    - 异常映射(纵深防御,前置校验之后的兜底):store 白名单 ValueError → 422;并发同名
      撞 uniq_faction_name UNIQUE 索引 → 409(实测本仓 surrealdb Python SDK 2.0.0 +
      surreal 服务端 3.2.0:该冲突抛 `surrealdb.errors.InternalError`,message 含
      "already contains";按 message 内容匹配而非绑定具体异常子类,避免与 SDK 版本行为绑死)。
    """
    sent = fc.model_dump(exclude_unset=True)          # 仅客户端显式提交的字段
    name = sent.pop("name")
    for k in codex_secret_capable_keys("faction"):     # 掩码哨兵:通用循环,不逐字段手写
        if sent.get(k) == _SECRET_MASK:
            sent.pop(k, None)

    unknown = sorted(k for k in sent if k not in _FACTION_STORAGE_KEYS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"未知势力字段: {unknown}(不在 codex_schema 注册表内;"
                   "如需新增字段,先去 codex_schema.py 注册再补 migration)")

    violations = _field_violations(codex_fields_for("faction"), sent)
    if violations:
        raise HTTPException(status_code=422,
                            detail=f"势力字段非法: {'; '.join(violations)}")
    _codex_l1_http("faction", {k: v for k, v in sent.items() if v not in (None, "", [], {})})

    st = _store_for(work)
    try:
        st.add_faction(name, **sent)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except _SurrealServerError as e:
        if "already contains" in str(e):
            raise HTTPException(
                status_code=409,
                detail=f"势力名重复,可能是并发写入冲突: {name!r}") from e
        raise

    # CX-Task 4·命题桥:落库成功后把标了 `{key}_secret` 的字段同步成 proposition
    # (secret=true),真正接入既有限知链(project_frame/_secret_fact_ids/
    # _secret_guard_block),而不再只是界面掩码。fail-soft:设定字段本身已写入成功是
    # 第一优先级,桥接失败只告警、不回滚/不阻断本次响应——作者不该因桥接层的 bug
    # 而存不进势力设定。回读完整行(而非本次 `sent` 增量)传入,防止"这次没提交但
    # 之前已标 secret 的字段"被误判无值而错删桥接命题。
    try:
        bridge_row = st.get_faction(name)
        if bridge_row is not None:
            sync_faction_secrets(st, name, bridge_row)
            try:
                from scribe3.codex_digest import sync_entity_digests
                sync_entity_digests(st, "faction", f"faction:{name}", bridge_row)
            except Exception:
                pass
    except Exception:
        logging.getLogger("scribe3").warning(
            "sync_faction_secrets 命题桥同步失败,不阻断势力写入: %s", name, exc_info=True)

    return {"ok": True}

def del_faction(name: str, work: str = "main"):
    _store_for(work).delete_faction(name)
    return {"ok": True}

def get_codex_schema(kind: str):
    """设定字段元数据(只读,CX-Task 3):前端按此渲染表单,不再硬编码字段清单。"""
    try:
        return codex_schema_for(kind)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知设定类型: {kind!r}")

def codex_search_ep(q: str = "", limit: int = Query(default=40, ge=1, le=100),
                    work: str = "main"):
    """设定库跨类型搜索(name/alias/text)。"""
    return {"items": _store_for(work).codex_search(q, limit=limit), "q": q}

def codex_health_ep(work: str = "main"):
    """设定库健康度:计数 + 稀疏档案 + 孤立角色。"""
    return _store_for(work).codex_health()

def faction_consistency_ep(work: str = "main"):
    """势力结构化一致性校验(只读,CX-Task 6):关系矛盾/核心圈超编/信物传承章超前/
    权力占比超100%。不落库,供作者自检;不登记写路由台账(纯 GET,无副作用)。"""
    return validate_faction_consistency(_store_for(work))

def list_items_endpoint(state: str | None = None, work: str = "main"):
    return _store_for(work).list_items(state)

def get_item_endpoint(name: str, work: str = "main"):
    row = _store_for(work).get_item(name)
    if not row:
        raise HTTPException(status_code=404, detail=f"item '{name}' 不存在")
    from scribe3.iceberg import attach_codex_ready
    return attach_codex_ready("item", dict(row))

def add_item_endpoint(req: dict, work: str = "main"):
    """物品 upsert:PATCH/merge 语义(端点层,参照 /factions)。

    P1-9:store.add_item 是 DELETE+CREATE 整行覆盖(state_history 硬置 []);编辑物品任一
    字段(如描述)都会清空状态流转史。此处根治:客户端「真正提交」的键才更新,未提交字段
    (含 state_history)一律读回旧值保留。这样编辑其它字段不再清 state_history;状态流转走
    专用 POST /items/{name}/state(update_item_state 追加史)。"""
    st = _store_for(work)
    name = req.get("name", "")
    old = next((i for i in st.list_items() if i.get("name") == name), {})

    def pick(k, default):
        # 客户端提交了该字段 → 用提交值;否则保留旧值,再退默认。
        return req[k] if k in req else old.get(k, default)

    _codex_l1_http("item", {k: req[k] for k in (
        "description", "current_owner", "special_properties",
    ) if k in req})
    st.add_item(name,
                category=pick("category", None),
                description=pick("description", None),
                current_owner=pick("current_owner", None),
                symbolic_state=pick("symbolic_state", "active"),
                special_properties=pick("special_properties", None),
                first_chapter=pick("first_chapter", None),
                state_history=pick("state_history", old.get("state_history", [])))
    return {"ok": True}

def update_item_state_endpoint(name: str, req: dict, work: str = "main"):
    """记录物品符号状态流转(P1-9:暴露 store.update_item_state,此前无可达调用方)。
    body: {"state": "lost"|"destroyed"|"active"|"unknown", "chapter": int, "note": str?}
    追加一条 state_history(如「镇煞钉 lost@第3章」),不清空既有史。"""
    new_state = req.get("state") or req.get("symbolic_state")
    chapter = req.get("chapter")
    if not new_state or chapter is None:
        raise HTTPException(status_code=422, detail="缺少必填字段: state/chapter")
    # 批E-A3:chapter 畸形(非数字串如 'abc')→ int() ValueError,返 422 而非 500 未处理异常
    try:
        chapter_int = int(chapter)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail=f"chapter 须为整数,收到: {chapter!r}")
    _store_for(work).update_item_state(name, new_state, chapter_int, note=req.get("note", ""))
    return {"ok": True}

def delete_item_endpoint(name: str, work: str = "main"):
    _store_for(work).delete_item(name)
    return {"ok": True}

def list_terms_endpoint(work: str = "main"):
    return _store_for(work).list_terms()

def get_term_endpoint(name: str, work: str = "main"):
    row = _store_for(work).get_term(name)
    if not row:
        raise HTTPException(status_code=404, detail=f"term '{name}' 不存在")
    from scribe3.iceberg import attach_codex_ready
    return attach_codex_ready("term", dict(row))

def add_term_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    _codex_l1_http("term", {"definition": req["definition"]} if req.get("definition") else {})
    st.add_term(req.get("name",""), category=req.get("category"),
                definition=req.get("definition"), aliases=req.get("aliases"),
                first_mention_chapter=req.get("first_mention_chapter"))
    return {"ok": True}

def delete_term_endpoint(name: str, work: str = "main"):
    _store_for(work).delete_term(name)
    return {"ok": True}

def character_relations(chapter: int | None = None, work: str = "main"):
    st = _store_for(work)
    if chapter:
        return st.relations_at(chapter)
    return st.relations_at(9999)

def add_character_relation_endpoint(req: dict, work: str = "main"):
    # R2.1: 缺字段返回 422;ValueError(实体不存在)→422
    src = req.get("src")
    dst = req.get("dst")
    relation = req.get("relation")
    since_chapter = req.get("since_chapter")
    if not src or not dst or not relation or since_chapter is None:
        raise HTTPException(status_code=422, detail="缺少必填字段: src/dst/relation/since_chapter")
    st = _store_for(work)
    try:
        st.add_character_relation(src, dst, relation, since_chapter, req.get("note"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}

def evolve_relation_endpoint(req: dict, work: str = "main"):
    # R2.1: 缺字段返回 422;ValueError(实体不存在)→422
    src = req.get("src")
    dst = req.get("dst")
    relation = req.get("relation")
    since_chapter = req.get("since_chapter")
    if not src or not dst or not relation or since_chapter is None:
        raise HTTPException(status_code=422, detail="缺少必填字段: src/dst/relation/since_chapter")
    st = _store_for(work)
    try:
        st.evolve_relation(src, dst, relation, since_chapter, req.get("note"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}

def end_relation_endpoint(req: dict, work: str = "main"):
    # R2.1: 缺字段返回 422;ValueError(实体不存在)→422
    src = req.get("src")
    dst = req.get("dst")
    until_chapter = req.get("until_chapter")
    if not src or not dst or until_chapter is None:
        raise HTTPException(status_code=422, detail="缺少必填字段: src/dst/until_chapter")
    st = _store_for(work)
    try:
        st.end_relation(src, dst, until_chapter)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    # 重绑定后 handler 在 app_impl globals 里找名字；本模块私有 helper 必须先注入。
    setattr(core, "_codex_l1_http", _codex_l1_http)
    core.__dict__["_codex_l1_http"] = _codex_l1_http
    _fn = g['facts']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'facts', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'facts', _re)
    g['facts'] = _re
    router.add_api_route('/facts', _re, methods=['GET'], name='facts')

    _fn = g['get_fact']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_fact', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_fact', _re)
    g['get_fact'] = _re
    router.add_api_route('/facts/{local}', _re, methods=['GET'], name='get_fact')

    _fn = g['get_fact_knowers']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_fact_knowers', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_fact_knowers', _re)
    g['get_fact_knowers'] = _re
    # 必须在 /facts/{local} 之外单独注册；路径更具体，Starlette 按注册顺序匹配
    router.add_api_route('/facts/{local}/knowers', _re, methods=['GET'], name='get_fact_knowers')

    _fn = g['add_char']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_char', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_char', _re)
    g['add_char'] = _re
    router.add_api_route('/characters', _re, methods=['POST'], name='add_char')

    _fn = g['get_char']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_char', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_char', _re)
    g['get_char'] = _re
    router.add_api_route('/characters/{local}', _re, methods=['GET'], name='get_char')

    _fn = g['edit_char']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'edit_char', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'edit_char', _re)
    g['edit_char'] = _re
    router.add_api_route('/characters/{local}', _re, methods=['PATCH'], name='edit_char')

    _fn = g['del_char']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'del_char', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'del_char', _re)
    g['del_char'] = _re
    router.add_api_route('/characters/{local}', _re, methods=['DELETE'], name='del_char')

    _fn = g['add_fact_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_fact_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_fact_ep', _re)
    g['add_fact_ep'] = _re
    router.add_api_route('/facts', _re, methods=['POST'], name='add_fact_ep')

    _fn = g['edit_fact']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'edit_fact', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'edit_fact', _re)
    g['edit_fact'] = _re
    router.add_api_route('/facts/{local}', _re, methods=['PATCH'], name='edit_fact')

    _fn = g['del_fact']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'del_fact', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'del_fact', _re)
    g['del_fact'] = _re
    router.add_api_route('/facts/{local}', _re, methods=['DELETE'], name='del_fact')

    _fn = g['supersede_fact_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'supersede_fact_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'supersede_fact_ep', _re)
    g['supersede_fact_ep'] = _re
    router.add_api_route('/facts/supersede', _re, methods=['POST'], name='supersede_fact_ep')

    _fn = g['list_rules']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'list_rules', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'list_rules', _re)
    g['list_rules'] = _re
    router.add_api_route('/world-rules', _re, methods=['GET'], name='list_rules')

    _fn = g['get_rule']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_rule', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_rule', _re)
    g['get_rule'] = _re
    router.add_api_route('/world-rules/{name}', _re, methods=['GET'], name='get_rule')

    _fn = g['add_rule']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_rule', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_rule', _re)
    g['add_rule'] = _re
    router.add_api_route('/world-rules', _re, methods=['POST'], name='add_rule')

    _fn = g['del_rule']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'del_rule', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'del_rule', _re)
    g['del_rule'] = _re
    router.add_api_route('/world-rules', _re, methods=['DELETE'], name='del_rule')

    _fn = g['get_faction_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_faction_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_faction_ep', _re)
    g['get_faction_ep'] = _re
    router.add_api_route('/factions/{name}', _re, methods=['GET'], name='get_faction_ep')

    _fn = g['list_factions']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'list_factions', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'list_factions', _re)
    g['list_factions'] = _re
    router.add_api_route('/factions', _re, methods=['GET'], name='list_factions')

    _fn = g['add_faction_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_faction_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_faction_ep', _re)
    g['add_faction_ep'] = _re
    router.add_api_route('/factions', _re, methods=['POST'], name='add_faction_ep')

    _fn = g['del_faction']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'del_faction', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'del_faction', _re)
    g['del_faction'] = _re
    router.add_api_route('/factions', _re, methods=['DELETE'], name='del_faction')

    _fn = g['get_codex_schema']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_codex_schema', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_codex_schema', _re)
    g['get_codex_schema'] = _re
    router.add_api_route('/codex-schema/{kind}', _re, methods=['GET'], name='get_codex_schema')

    _fn = g['codex_search_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'codex_search_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'codex_search_ep', _re)
    g['codex_search_ep'] = _re
    router.add_api_route('/codex/search', _re, methods=['GET'], name='codex_search_ep')

    _fn = g['codex_health_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'codex_health_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'codex_health_ep', _re)
    g['codex_health_ep'] = _re
    router.add_api_route('/codex/health', _re, methods=['GET'], name='codex_health_ep')

    _fn = g['faction_consistency_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'faction_consistency_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'faction_consistency_ep', _re)
    g['faction_consistency_ep'] = _re
    router.add_api_route('/faction-consistency', _re, methods=['GET'], name='faction_consistency_ep')

    _fn = g['list_items_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'list_items_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'list_items_endpoint', _re)
    g['list_items_endpoint'] = _re
    router.add_api_route('/items', _re, methods=['GET'], name='list_items_endpoint')

    _fn = g['get_item_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_item_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_item_endpoint', _re)
    g['get_item_endpoint'] = _re
    router.add_api_route('/items/{name}', _re, methods=['GET'], name='get_item_endpoint')

    _fn = g['add_item_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_item_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_item_endpoint', _re)
    g['add_item_endpoint'] = _re
    router.add_api_route('/items', _re, methods=['POST'], name='add_item_endpoint')

    _fn = g['update_item_state_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'update_item_state_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'update_item_state_endpoint', _re)
    g['update_item_state_endpoint'] = _re
    router.add_api_route('/items/{name}/state', _re, methods=['POST'], name='update_item_state_endpoint')

    _fn = g['delete_item_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'delete_item_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'delete_item_endpoint', _re)
    g['delete_item_endpoint'] = _re
    router.add_api_route('/items', _re, methods=['DELETE'], name='delete_item_endpoint')

    _fn = g['list_terms_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'list_terms_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'list_terms_endpoint', _re)
    g['list_terms_endpoint'] = _re
    router.add_api_route('/terms', _re, methods=['GET'], name='list_terms_endpoint')

    _fn = g['get_term_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_term_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_term_endpoint', _re)
    g['get_term_endpoint'] = _re
    router.add_api_route('/terms/{name}', _re, methods=['GET'], name='get_term_endpoint')

    _fn = g['add_term_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_term_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_term_endpoint', _re)
    g['add_term_endpoint'] = _re
    router.add_api_route('/terms', _re, methods=['POST'], name='add_term_endpoint')

    _fn = g['delete_term_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'delete_term_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'delete_term_endpoint', _re)
    g['delete_term_endpoint'] = _re
    router.add_api_route('/terms', _re, methods=['DELETE'], name='delete_term_endpoint')

    _fn = g['character_relations']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'character_relations', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'character_relations', _re)
    g['character_relations'] = _re
    router.add_api_route('/character-relations', _re, methods=['GET'], name='character_relations')

    _fn = g['add_character_relation_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_character_relation_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_character_relation_endpoint', _re)
    g['add_character_relation_endpoint'] = _re
    router.add_api_route('/character-relations', _re, methods=['POST'], name='add_character_relation_endpoint')

    _fn = g['evolve_relation_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'evolve_relation_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'evolve_relation_endpoint', _re)
    g['evolve_relation_endpoint'] = _re
    router.add_api_route('/character-relations/evolve', _re, methods=['POST'], name='evolve_relation_endpoint')

    _fn = g['end_relation_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'end_relation_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'end_relation_endpoint', _re)
    g['end_relation_endpoint'] = _re
    router.add_api_route('/character-relations/end', _re, methods=['POST'], name='end_relation_endpoint')

_bind_and_register()
