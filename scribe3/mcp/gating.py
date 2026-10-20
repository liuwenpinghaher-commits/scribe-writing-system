"""MCP gating and shared private helpers used by tools."""
from __future__ import annotations

from scribe3.mcp._common import *  # noqa: F403

def _default_work() -> str:
    return os.environ.get("SCRIBE3_WORK", "main")


def _store_work(s) -> str | None:
    return getattr(s, "db_name", None) or getattr(s, "db", None)



def _store_for(work: str | None = None):
    """返回目标书 store。省略 work 时 fail-closed，禁止回落默认库（单测显式 set_store 注入除外）。"""
    from scribe3.mcp import _common as C
    if not work:
        if C._store is not None:
            return C._store
        raise ValueError("work is required (fail-closed: refuse default store)")
    if work in C._stores:
        C._stores.move_to_end(work)
        return C._stores[work]
    from scribe3.store import SurrealStore
    st = SurrealStore(ns="scribe3", db=work)
    st.apply_schema()
    C._stores[work] = st
    C._stores.move_to_end(work)
    while len(C._stores) > C._STORE_CACHE_MAX:
        _, old = C._stores.popitem(last=False)
        if old is not C._store:
            try:
                old.close()
            except Exception:
                pass
    return st


def requires_approval(name: str) -> bool:
    return name in WRITE_GATED


def commit_if_approved(name: str, accepted: bool | None,
                       do_write: Callable[[], object],
                       args: dict | None = None) -> dict:
    """写门控单一落库点:WRITE_GATED 的工具须 accepted=True 才执行 do_write
    (do_write 内部走 store 单点落库)。拒绝/过期均 fail-closed 不写，且状态分开。

    O13：可选 ``args`` 时用审批幂等指纹，重复同 payload 返回首次 written 结果。
    实现 SSOT：``scribe3.write_commit.commit_if_approved``（纯函数，可无 mcp SDK）。
    """
    from scribe3.write_commit import commit_if_approved as _pure_commit
    return _pure_commit(
        name, accepted, do_write, args=args, write_gated=WRITE_GATED,
    )


class _Approve(BaseModel):
    confirm: bool = True


async def _ask(ctx: Context, summary: str) -> bool | None:
    """Hermes elicitation:写前征求批准。超时/异常与作者显式拒绝分开审计。"""
    try:
        res = await ctx.elicit(message=f"批准写入?{summary}", schema=_Approve)
        return getattr(res, "action", None) == "accept"
    except Exception:
        return None


def _jsonable(obj):
    """把 store 原始行(SELECT *)转成 FastMCP 能序列化的纯 JSON 值。

    2026-07-15 真机探针撞出的既有 bug:`SELECT *` 的每一行都带 `id`,类型是
    `surrealdb.data.types.record_id.RecordID`——FastMCP 用 pydantic 严格序列化,
    直接抛 `Unable to serialize unknown type: RecordID`,**整个工具调用失败**。
    受害的是 s3_list_factions / s3_list_world_rules / s3_list_items / s3_list_terms
    (以及 CX-Task 5 新加的 s3_list_entity_relations)——也就是说主编从来就没法
    通过 MCP 列出势力/世界规则/物件/术语。REST 侧不炸只是因为 FastAPI 的
    jsonable_encoder 会兜底(它把 RecordID 拆成 dict),掩盖了这个洞。

    修在 MCP 边界而不是 store/REST:store 的返回值被 REST、prompt 组装、检测器
    等一堆地方消费,改那里会波及全系统;这里只管把要过 MCP 协议的行洗干净。
    保留 id(转成字符串,对模型仍可用),不做删字段。"""
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)   # RecordID / datetime / Duration 等 SurrealDB 原生类型


def _mask_value(value: str, is_secret: bool, reveal_secret: bool) -> str | None:
    """统一掩码函数:is_secret=True 且 reveal_secret=False → 返回掩码占位符。
    与 store.graph() 使用同一占位符 '🔒 私密'。"""
    if is_secret and not reveal_secret:
        return _SECRET_MASK
    return value


def _normalize_character_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """把作者在中文 UI 中自然填写的重要度映射到现有 DB 枚举。"""
    normalized = dict(fields)
    importance = normalized.get("importance")
    if isinstance(importance, str):
        normalized["importance"] = _CHARACTER_IMPORTANCE_ALIASES.get(importance.strip(), importance)
    return normalized


def aggregate_event_participants(participants: list[dict] | None) -> dict:
    """MCP s3_add_event 参与者聚合:同 role 多人升 list,禁止后写覆盖。
    纯函数,供工具与单测共用——禁止测试侧重写此循环。"""
    parts: dict = {}
    if not participants:
        return parts
    for p in participants:
        if not isinstance(p, dict):
            continue
        role = p.get("role", "") or ""
        entity = p.get("entity", "") or ""
        if not role or not entity:
            continue
        if role not in parts:
            parts[role] = entity
        else:
            cur = parts[role]
            if isinstance(cur, list):
                if entity not in cur:
                    cur.append(entity)
            elif cur != entity:
                parts[role] = [cur, entity]
    return parts


def aggregate_event_effects(effects: list | None) -> list[str]:
    """MCP s3_add_event effects 归一化为 fact oid 列表。"""
    effs: list[str] = []
    if not effects:
        return effs
    for e in effects:
        if isinstance(e, str):
            effs.append(e)
        elif isinstance(e, dict):
            fid = e.get("id") or e.get("fact_id")
            if fid:
                effs.append(fid)
    return effs


def aggregate_event_causal_in(causal_in: list[dict] | None) -> list:
    """MCP s3_add_event causal_in 归一化为 (event_id, ctype) 列表。"""
    causal: list = []
    if not causal_in:
        return causal
    for c in causal_in:
        if not isinstance(c, dict):
            continue
        ev_id = c.get("event", "")
        ctype = c.get("ctype", "causes")
        if ev_id:
            causal.append((ev_id, ctype))
    return causal


def _mcp_unset_factory():
    return _MCP_UNSET


def _mcp_unset_field():
    """不向 FastMCP JSON Schema 暴露内部哨兵，同时保留省略参数语义。"""
    return Field(default_factory=_mcp_unset_factory)


def _is_mcp_unset(value: object) -> bool:
    # FastMCP/Pydantic 调用会执行 default_factory；测试或内部直接调函数时，Python
    # 会把签名上的 FieldInfo 原样传入。两条路径都应视为“调用方未提供字段”。
    return value is _MCP_UNSET or (
        isinstance(value, FieldInfo) and value.default_factory is _mcp_unset_factory
    )


def _check_proposition(proposition: str, work: str | None = None) -> dict | None:
    """校验 proposition 为已存在的 fact: oid。
    合法返回 None;不合法返回 error dict(调用方应立即 return 该 dict)。
    """
    if not proposition.startswith("fact:"):
        return {"error": f"proposition 必须是已存在的 fact: oid,收到: {proposition!r}"}
    if _store_for(work).fact(proposition) is None:
        return {"error": f"proposition {proposition!r} 在 store 中不存在,请先用 s3_add_fact 创建"}
    return None


def _normalize_plan_beats(beats: list[Any]) -> tuple[list[dict[str, Any]] | None, str | None]:
    """把 LLM 常用的 beat/action 别名收敛到章节唯一消费字段 text。"""
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(beats):
        if isinstance(raw, str):
            text = raw.strip()
            item: dict[str, Any] = {}
        elif isinstance(raw, dict):
            text = str(raw.get("text") or raw.get("beat") or raw.get("action") or "").strip()
            item = dict(raw)
        else:
            return None, f"beats[{index}] 必须是字符串或对象"
        if not text:
            return None, f"beats[{index}] 缺 text（可使用 beat/action 作为别名）"
        item.pop("beat", None)
        item.pop("action", None)
        item["text"] = text
        normalized.append(item)
    return normalized, None


def _canonical_plan_characters(store, values: list[Any], field: str) -> tuple[list[str] | None, str | None]:
    """角色字段只保存书内稳定 role id，拒绝把投影 JSON 串进角色列表。"""
    known: dict[str, str] = {}
    for character in store.characters() or []:
        cid = str(getattr(character, "id", "") or "").strip()
        name = str(getattr(character, "name", "") or "").strip()
        if not cid:
            continue
        for key in (cid, name, cid.split(":", 1)[-1], f"role:{name}"):
            if key:
                known[key] = cid
    normalized: list[str] = []
    unknown: list[str] = []
    for raw in values:
        if not isinstance(raw, str) or not raw.strip():
            unknown.append(str(raw))
            continue
        value = raw.strip()
        canonical = known.get(value)
        if canonical is None and value.startswith("role:"):
            canonical = known.get(value[5:])
        if canonical is None:
            unknown.append(value)
            continue
        if canonical not in normalized:
            normalized.append(canonical)
    if unknown:
        return None, f"{field} 含不存在或格式错误的角色: {unknown}"
    return normalized, None


def _normalize_plan_deductions(store, deductions: list[Any]) -> tuple[list[dict[str, Any]] | None, str | None]:
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(deductions):
        if not isinstance(raw, dict):
            return None, f"deductions[{index}] 必须是对象"
        character = raw.get("character_id") or raw.get("character") or raw.get("role")
        prose = str(raw.get("prose") or "").strip()
        ids, err = _canonical_plan_characters(store, [character], f"deductions[{index}].character_id")
        if err:
            return None, err
        if not prose:
            return None, f"deductions[{index}] 缺 prose"
        item = dict(raw)
        item.pop("character", None)
        item.pop("role", None)
        item["character_id"] = ids[0]
        item["prose"] = prose
        normalized.append(item)
    return normalized, None


__all__ = ['_default_work', '_store_work', '_store_for', 'requires_approval', 'commit_if_approved', '_Approve', '_ask', '_jsonable', '_mask_value', '_normalize_character_fields', 'aggregate_event_participants', 'aggregate_event_effects', 'aggregate_event_causal_in', '_mcp_unset_factory', '_mcp_unset_field', '_is_mcp_unset', '_check_proposition', '_normalize_plan_beats', '_canonical_plan_characters', '_normalize_plan_deductions']
