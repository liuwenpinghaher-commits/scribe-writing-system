"""SurrealStore · 故事本体 v2 的 SurrealDB 持久层(NS=scribe3)。

把纵切片的内存 World 迁到 SurrealDB,接口与 World 鸭子兼容——knowledge.project_frame /
knowledge.project_frame 不改一行即可跑在真库上(证限知范式在持久层照样成立)。

不变量:**改世界状态只经 _execute_write 单一落库点**(开发标准 §0 不变量1)。
oid 映射:本体 id(role:焦三 / fact:治眼)↔ SurrealDB record(character:焦三 / proposition:治眼)。

架构入口: docs/CURRENT_ARCHITECTURE.md · 拆分路线: docs/ARCHITECTURE_SPLIT_ROADMAP.md

# ----- 文件分区地图(Phase0 基线;搬迁时按此切 store/* mixin)-----
# 0. 模块级工具: oid 映射 · 连接 · work 注册表(list/create/archive/...)
# 1. SurrealStore 连接/schema/_execute_write/基础查询
# 2. 实体与命题: add_entity · add_fact · supersede · knowledge edges
# 3. 事件与因果: add_event · events_at · causal 辅助
# 4. 检索: semantic/hybrid recall · memory trace · materials
# 5. 章节与正文: chapter meta · prose · ingest 相关写
# 6. 伏笔: plant/advance/clue · overdue
# 7. Codex 扩展: faction/item/term/world_rule/relations/voice
# 8. 意图/北极星: get_intent · set_intent
# 9. 会话与 AI 轨迹: chat messages · runs · editorial threads
# 公开类名 SurrealStore 在拆分后须保持稳定(门面+mixin)。
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import hashlib
import json
import logging
import os
import re
from contextlib import contextmanager
from pathlib import Path

import websockets.exceptions as _ws_exc
from surrealdb import RecordID, Surreal
from surrealdb.errors import ConnectionUnavailableError

from scribe3.codex_schema import ENTITY_RELATION_TYPES as _ENTITY_RELATION_TYPES
from scribe3.codex_schema import all_storage_keys as _codex_all_storage_keys
from scribe3.context_models import (
    ContextFocus, ContextSnapshot, NavigationIntent, StaleContextError,
)
from scribe3.memory_lifecycle import known_at as _known_at
from scribe3.memory_lifecycle import resolve_temporal_view as _resolve_view
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge

# 连接类异常(触发重连重试的白名单;语法/校验类错误不在内,绝不重试)。
# OSError 覆盖 ConnectionError/TimeoutError/socket 层错;EOFError 见于半关闭流。
_CONN_ERRORS = (_ws_exc.WebSocketException, ConnectionUnavailableError, OSError, EOFError)

# 本体 id 前缀 ↔ SurrealDB 表名
ONT2TBL = {"role": "character", "place": "place", "fact": "proposition", "ev": "event"}
TBL2ONT = {"character": "role", "place": "place", "proposition": "fact", "event": "ev"}
TBL2KIND = {"character": "character", "place": "place"}

_OPEN_CHAPTER = 9999    # graph()/无界查询的"到当前为止"哨兵
_ALL_CHAPTERS = 99999   # _editor_system 取全部已确立事实
# 质量缓存的算法版本。每次改变 quality_flags/因果判定口径时递增；旧章不会被
# 静默当作当前结果，而是由质量面板明确提示作者刷新派生缓存。
# 2：产品 QC 合计扩维（god_view/degeneration/filler/rule_of_three）；见 qc_product_keys
QUALITY_CACHE_REVISION = 2
# 通用"未传参"哨兵:区分"调用方显式传了 None/False"与"根本没传"。
# 用处:update_chapter_meta(未传 volume vs 传了 None)、add_faction(未传字段不进 MERGE 内容,
# 否则会用默认值覆盖库中已有值,违背部分更新语义)。
_UNSET = object()


def _chapter_range_target(start: int | None = None, end: int | None = None,
                          *, end_inclusive: bool = True) -> str:
    """构造数值型 chapter record id 范围目标。

    SurrealDB 3.1.5 不接受 ``chapter:$start..=$end`` 这类边界参数绑定,
    因此只在严格验证为正整数后拼接十进制字面量。
    """
    for name, value in (("start", start), ("end", end)):
        if value is not None and type(value) is not int:
            raise TypeError(f"{name} must be an int")
        if value is not None and value < 1:
            raise ValueError(f"{name} must be >= 1")
    if start is not None and end is not None and start > end:
        raise ValueError("start must be <= end")
    if start is None and end is None:
        return "chapter:.."
    if start is None:
        return f"chapter:..{'=' if end_inclusive else ''}{end}"
    if end is None:
        return f"chapter:{start}.."
    return f"chapter:{start}..{'=' if end_inclusive else ''}{end}"


def _split(oid: str) -> tuple[str, str]:
    prefix, local = oid.split(":", 1)
    return ONT2TBL[prefix], local


def _join(table: str, local: str) -> str:
    return f"{TBL2ONT[table]}:{local}"


def _emit_cache_invalidation(table: str, work: str | None, store=None) -> None:
    """Task 16-B:向上下文性能层发一个表级失效事件(正典写入 / 记忆 supersede /
    素材 archive·pin 的写点调用)。best-effort:context_cache 缺席或任何异常都静默——
    缓存卫生绝不阻断 store 写主链路(写正确性优先)。

    store 若传入：双写 cache_watch（S-2 Changefeed 旁路，跨进程失效）。
    """
    try:
        from scribe3 import context_cache
        context_cache.emit_invalidation(table, work=work, store=store)
    except Exception:
        pass


def _json_obj(value) -> dict | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _oid_effect(oid: str | None) -> dict | None:
    if not oid or ":" not in oid:
        return None
    prefix = oid.split(":", 1)[0]
    typ = {"role": "character", "fact": "fact", "ev": "event"}.get(prefix, prefix)
    return {"type": typ, "id": oid}


def _write_effect_from_tool(tool: str | None, args: dict | None) -> dict | None:
    if not tool or not tool.startswith("s3_") or not isinstance(args, dict):
        return None
    objects: list[dict] = []
    if tool in {"s3_add_character", "s3_add_fact", "s3_add_event"}:
        obj = _oid_effect(args.get("oid"))
        if obj:
            objects.append(obj)
    elif tool == "s3_patch_character":
        cid = args.get("character_id") or ""
        if cid and ":" not in str(cid):
            cid = f"role:{cid}"
        obj = _oid_effect(cid)
        if obj:
            objects.append(obj)
    elif tool == "s3_set_intent":
        objects.append({"type": "intent", "id": "intent:main"})
    elif tool == "s3_record_knowledge":
        proposition = args.get("proposition") or args.get("proposition_id")
        obj = _oid_effect(proposition)
        if obj:
            objects.append(obj)
    elif tool in {"s3_add_item", "s3_add_term", "s3_add_world_rule", "s3_add_faction"}:
        name = args.get("name")
        if name:
            objects.append({"type": tool.removeprefix("s3_add_"), "name": name})
    elif tool == "s3_plant_promise":
        pid = args.get("pid") or args.get("id")
        if pid:
            objects.append({"type": "promise", "id": pid})
    elif tool == "s3_add_clue":
        pid = args.get("pid") or args.get("promise_id")
        if pid:
            objects.append({"type": "promise_clue", "promise_id": pid})
    if not objects:
        return None
    return {"objects": objects}


def _write_effect_from_approval_message(message: str | None) -> dict | None:
    if not message:
        return None
    objects: list[dict] = []
    fact = re.search(r"fact:([^\s:·，,]+)", message)
    if fact:
        objects.append({"type": "fact", "id": f"fact:{fact.group(1)}"})
    role = re.search(r"role:([^\s=·，,]+)", message)
    if role:
        objects.append({"type": "character", "id": f"role:{role.group(1)}"})
    return {"objects": objects} if objects else None


def _url() -> str:
    return os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc")


# ===== 多书注册表(一书一 DB:NS=scribe3 / db=<slug>;注册表在 db=_reg)=====
def _reg_conn(url: str | None = None):
    db = Surreal(url or _url())
    _u = os.environ.get("SCRIBE3_SURREAL_USER", "root")
    _p = os.environ.get("SCRIBE3_SURREAL_PASS", "root")
    db.signin({"username": _u, "password": _p})
    db.use("scribe3", "_reg")
    db.query("DEFINE TABLE IF NOT EXISTS work SCHEMALESS")
    return db


# 活跃(未废弃)作品过滤条件:archived 字段缺省 NONE,显式 OR 掉 NONE 情形——
# SurrealQL 对缺失字段的 `!=` 比较不保证按预期短路,故两种"未废弃"形态都要枚举。
_ACTIVE_FILTER = "archived = NONE OR archived != true"


def _guard_mutable_slug(slug: str) -> None:
    """main 保护 + slug 合法性——archive_work / delete_work 共用两道校验。"""
    if slug == "main":
        raise ValueError("不能删除主书 main")
    if not all(c.isalnum() or c in "_-" for c in slug):
        raise ValueError("非法 slug")


def _work_public_row(r: dict) -> dict:
    """Registry row → API/list shape (includes L1 owner_user_id when present)."""
    return {
        "slug": r.get("slug"),
        "title": r.get("title"),
        "owner_user_id": r.get("owner_user_id"),
    }


def _apply_owner_filter(rows: list[dict]) -> list[dict]:
    """L1: when request context has a user, only return that owner's works."""
    try:
        from scribe3.auth.context import current_owner_filter
        from scribe3.auth.ownership import filter_works_for_user

        filt = current_owner_filter.get()
    except Exception:
        return rows
    if filt is None:
        return rows
    return filter_works_for_user(rows, filt)


def list_works(url: str | None = None) -> list[dict]:
    """列所有未废弃的书。注册表全空则自动登记 main=乱世铜炉(现有数据所在 DB)。

    L1: 若请求上下文设置了 current_owner_filter,仅返回该用户拥有的书
    (无 owner_user_id 的历史书归 SCRIBE3_LEGACY_OWNER,见 ownership.effective_owner)。
    """
    db = _reg_conn(url)
    try:
        rows = db.query(f"SELECT * FROM work WHERE {_ACTIVE_FILTER}")
        if not rows:
            return []
        rows = sorted(rows, key=lambda r: r.get("ord") or 0)
        return _apply_owner_filter([_work_public_row(r) for r in rows])
    finally:
        db.close()


def _archive_retention_days() -> int:
    """废弃箱建议保留天数(仅元数据提示,不自动 purge)。环境变量可覆盖,默认 30。"""
    import os
    try:
        return max(0, int(get_flag("SCRIBE3_ARCHIVE_RETENTION_DAYS")))
    except (TypeError, ValueError):
        return 30


def _days_since_archived(archived_at) -> int | None:
    """计算废弃天数;解析失败返回 None。"""
    if not archived_at:
        return None
    from datetime import datetime, timezone
    raw = str(archived_at).strip()
    if not raw:
        return None
    try:
        # Surreal 常给 ISO;容错尾缀 Z
        iso = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, int((now - dt).total_seconds() // 86400))
    except Exception:
        return None


def archived_works(url: str | None = None) -> list[dict]:
    """废弃箱列表:已废弃的作品,按废弃时间倒序。

    附带保留期元数据(不自动删除):
    - days_in_trash: 已废弃天数
    - retention_days: 建议保留天数(SCRIBE3_ARCHIVE_RETENTION_DAYS,默认 30)
    - purge_recommended: 超过建议保留期 → True(仅 UI 提示)
    """
    db = _reg_conn(url)
    try:
        rows = db.query("SELECT * FROM work WHERE archived = true")
        rows = sorted(rows, key=lambda r: r.get("archived_at") or "", reverse=True)
        retain = _archive_retention_days()
        out = []
        for r in rows:
            at = r.get("archived_at")
            days = _days_since_archived(at)
            out.append({
                "slug": r.get("slug"),
                "title": r.get("title"),
                "owner_user_id": r.get("owner_user_id"),
                "archived_at": at,
                "days_in_trash": days,
                "retention_days": retain,
                "purge_recommended": bool(days is not None and retain > 0 and days >= retain),
            })
        return _apply_owner_filter(out)
    finally:
        db.close()


def archive_work(slug: str, url: str | None = None) -> None:
    """废弃一本书(软删):注册表标记 archived=true,独立 DB 一字不动。主书 main 不可废弃。

    - 不存在 → ValueError(勿静默假成功)
    - 已废弃 → 幂等成功(不改 archived_at)
    """
    _guard_mutable_slug(slug)
    db = _reg_conn(url)
    try:
        rows = db.query("SELECT * FROM type::record('work',$s)", {"s": slug})
        if not rows:
            raise ValueError(f"作品不存在: {slug}")
        if rows[0].get("archived") is True:
            return  # 幂等
        db.query("UPDATE type::record('work',$s) SET archived=true, archived_at=time::now()",
                 {"s": slug})
    finally:
        db.close()


def restore_work(slug: str, url: str | None = None) -> None:
    """从废弃箱恢复:若已有同名活跃作品,先抛错提示改名(废弃箱里的书本就不占名)。

    - 不存在 → ValueError
    - 未废弃(活跃) → 幂等成功
    """
    db = _reg_conn(url)
    try:
        rows = db.query("SELECT * FROM type::record('work',$s)", {"s": slug})
        if not rows:
            raise ValueError(f"作品不存在: {slug}")
        if rows[0].get("archived") is not True:
            return  # 已在活跃区,幂等
        title = (rows[0].get("title") if rows else None) or ""
        stripped = title.strip()
        if stripped:
            active = db.query(f"SELECT * FROM work WHERE ({_ACTIVE_FILTER}) AND slug != $s",
                               {"s": slug})
            if any((r.get("title") or "").strip() == stripped for r in active):
                raise ValueError(f"已有同名作品「{stripped}」,请先改名")
        db.query("UPDATE type::record('work',$s) SET archived=false, archived_at=NONE",
                 {"s": slug})
    finally:
        db.close()


def delete_work(slug: str, url: str | None = None) -> None:
    """永久删除一本书:注册表删除 + REMOVE DATABASE,不可逆。语义收窄——只允许
    删除已废弃(archived=true)的书,强制走"先废弃再永久删除"两道门。主书 main 不可删。"""
    _guard_mutable_slug(slug)
    db = _reg_conn(url)
    try:
        rows = db.query("SELECT * FROM type::record('work',$s)", {"s": slug})
        if not rows or rows[0].get("archived") is not True:
            raise ValueError("请先移入废弃箱再永久删除")
        db.query("DELETE type::record('work',$s)", {"s": slug})
        db.query(f"REMOVE DATABASE IF EXISTS {slug}")
    finally:
        db.close()


def _guard_title(title: str) -> str:
    """作品名不得为空/纯空白——create_work/rename_work 共用。
    空名会让 purge 的强确认门失效(库中 '' 与 confirm_title '' strip 后相等即放行),
    故从源头断绝;purge 端点另有独立空名守卫兜底历史脏数据(双保险)。"""
    stripped = (title or "").strip()
    if not stripped:
        raise ValueError("作品名不能为空")
    return stripped


def rename_work(slug: str, title: str, url: str | None = None) -> None:
    stripped = _guard_title(title)
    db = _reg_conn(url)
    try:
        active = db.query(f"SELECT * FROM work WHERE ({_ACTIVE_FILTER}) AND slug != $s",
                           {"s": slug})
        if any((r.get("title") or "").strip() == stripped for r in active):
            raise ValueError(f"已有同名作品:{title}")
        db.query("UPDATE type::record('work',$s) SET title=$t", {"s": slug, "t": title})
    finally:
        db.close()


def set_work_owner(slug: str, owner_user_id: str, url: str | None = None) -> dict:
    """管理台：转让作品归属。"""
    owner = (owner_user_id or "").strip()
    if not owner:
        raise ValueError("owner_user_id required")
    if not all(c.isalnum() or c in "_-" for c in slug):
        raise ValueError("非法 slug")
    db = _reg_conn(url)
    try:
        rows = db.query("SELECT * FROM type::record('work',$s)", {"s": slug})
        if not rows:
            raise ValueError(f"作品不存在: {slug}")
        db.query(
            "UPDATE type::record('work',$s) SET owner_user_id=$o",
            {"s": slug, "o": owner},
        )
        r = rows[0]
        return {
            "slug": r.get("slug") or slug,
            "title": r.get("title"),
            "owner_user_id": owner,
            "archived": bool(r.get("archived")),
        }
    finally:
        db.close()


def list_works_admin(
    *,
    owner: str | None = None,
    archived: str | None = None,  # active|archived|all
    q: str | None = None,
    url: str | None = None,
) -> list[dict]:
    """管理台：不按当前用户过滤，可看全库 works。"""
    db = _reg_conn(url)
    try:
        rows = db.query("SELECT * FROM work") or []
        out = []
        for r in rows:
            is_arch = r.get("archived") is True
            mode = (archived or "all").strip().lower()
            if mode == "active" and is_arch:
                continue
            if mode == "archived" and not is_arch:
                continue
            owner_id = r.get("owner_user_id")
            from scribe3.auth.ownership import effective_owner
            eff = effective_owner({
                "owner_user_id": owner_id,
                "slug": r.get("slug"),
            })
            if owner and owner.strip() and eff != owner.strip():
                continue
            title = (r.get("title") or "")
            slug = (r.get("slug") or "")
            if q and q.strip():
                qq = q.strip().lower()
                if qq not in title.lower() and qq not in slug.lower() and qq not in (eff or "").lower():
                    continue
            at = r.get("archived_at")
            out.append({
                "slug": slug,
                "title": title,
                "owner_user_id": owner_id,
                "effective_owner": eff,
                "archived": is_arch,
                "archived_at": at,
                "ord": r.get("ord"),
            })
        out.sort(key=lambda x: (x.get("archived") or False, x.get("ord") or 0, x.get("slug") or ""))
        return out
    finally:
        db.close()


def create_work(title: str, slug: str | None = None, url: str | None = None,
                owner_user_id: str | None = None) -> dict:
    """建一本书:注册表登记 + 给它的独立 DB 建 schema。slug=该书 DB 名(ascii)。
    活跃作品(未废弃)中重名(strip 后比对)直接拒绝——废弃箱里的书不占名。空名亦拒收。

    L1: owner_user_id 默认取请求上下文 current_user_id(会话用户)。
    """
    import uuid
    stripped = _guard_title(title)
    slug = slug or ("book_" + uuid.uuid4().hex[:8])
    owner = owner_user_id
    if owner is None:
        try:
            from scribe3.auth.context import current_user_id
            owner = current_user_id.get()
        except Exception:
            owner = None
    db = _reg_conn(url)
    try:
        active = db.query(f"SELECT * FROM work WHERE {_ACTIVE_FILTER}")
        if any((r.get("title") or "").strip() == stripped for r in active):
            raise ValueError(f"已有同名作品:{title}")
        if owner:
            db.query(
                "CREATE type::record('work',$s) SET slug=$s, title=$t, "
                "owner_user_id=$o, created=time::now()",
                {"s": slug, "t": title, "o": owner},
            )
        else:
            db.query(
                "CREATE type::record('work',$s) SET slug=$s, title=$t, created=time::now()",
                {"s": slug, "t": title},
            )
    finally:
        db.close()
    # 延迟导入:core_preamble 被 store 包加载时 SurrealStore 尚未挂到本模块命名空间
    from scribe3.store.surreal import SurrealStore
    st = SurrealStore(url=url, ns="scribe3", db=slug)
    st.apply_schema()
    st.close()
    return {"slug": slug, "title": title, "owner_user_id": owner}


_TABLES = frozenset(list(ONT2TBL.values()) + ["promise", "motif", "motif_instance",
                                              "promise_touch", "arc_plan", "material",
                                              "relation_touch"])

# 素材库分类白名单(migration 055 DB 级 ASSERT 同源;app 层 422 校验用)。
# emotion_module(方案B任务15,migration 060 DB 级 ASSERT 同步):EM-001情绪模块卡/
# RH-001爽点循环/TR-001触动点三张互引 schema 统一挂此 kind,卡内容(JSON)自带
# id 前缀 EM-/RH-/TR- 自行区分类型,互引用 id 字符串(如 escalation 步骤引用其他卡 id)。
MATERIAL_KINDS = ("research", "reference", "snippet", "inspiration", "note", "emotion_module")

# 素材创建来源(只在 create 写入;import/session_clip 作者直写,manual/chief 经手建或主编)
MATERIAL_ORIGINS = ("manual", "import", "session_clip", "chief")

# 经验性记忆类型(Task 8 migration 078):正典事实不属此列——canonical 永远来自领域表。
MEMORY_KINDS = ("working", "episodic", "procedural", "reference", "uncertainty")
MEMORY_RELATIONS = ("supports", "contradicts", "derived_from", "same_topic", "caused_by", "corrects")

# 角色弧光静态锚(Weiland 五要素 + 弧型 + 私密目标),migration 054 落 character 表
_ANCHOR_KEYS = ("ghost", "lie", "truth", "want", "need", "arc_type", "private_agenda")
_FIELDS_BY_TABLE: dict[str, frozenset] = {
    "character": frozenset({"name", "aliases", "backstory", "backstory_secret", "importance",
        "appearance", "personality_detail", "abilities", "weaknesses",
        "surface_goal", "deep_need", "internal_conflict", "fear",
        "first_appearance", "personality_tags", "archived"}),
    "place": frozenset({"name"}),
    "proposition": frozenset({"entity_id", "attribute", "value", "valid_from",
                              "valid_to", "secret", "leak_markers", "ingest_seq",
                              "archived"}),
    "event": frozenset({"event_type", "story_chapter",
                        "motivated_by_goal", "location", "preconditions"}),
    "promise": frozenset({"text", "setup_chapter", "payoff_chapter", "status", "kind", "clues",
                          "tier", "payoff_min", "payoff_max", "resolution"}),
    "motif": frozenset({"name", "theme", "echoes", "unfolding",
                        "echo_terms", "phase", "tier", "scope"}),
    "material": frozenset({"title", "body", "kind", "tags", "source", "ref_tags",
                           "summary", "origin", "tokens", "embedding", "about_entities",
                           "pinned", "archived", "recall_count", "last_recalled_at"}),
}



def _memory_known_at(known_from, known_to, chapter: int) -> bool:
    """检索管线的【读者/发现时间·剧透门】(I-4 限知红线,纯函数)。
    known_from/known_to 记"这条记忆在第几章被知道/失去";None=无约束(fail-open)。
    当章 chapter 能知道的条件:known_from<=chapter 且 (known_to 为空或 known_to>chapter)。
    杜绝"第 20 章才被知道的记忆倒灌进第 5 章"。

    ⚠ I-2 口径守卫:此门用于检索管线(memory_bm25/vector/graph),【恒开、不接受 focalizer】——
      任何检索都不倒灌未来揭示,这是写作 prompt 的剧透保护。同一对 known_from/to 在
      memory_lifecycle.resolve_temporal_view / visible 里还承载另一种用途——【可选的角色限知视角】
      (仅在传 focalizer 时叠加,focalizer=None 是上帝视角不叠门)。两处边界数值口径完全一致,
      差别只在"门是否恒开";切勿把 resolve_temporal_view(默认全知)误当检索剧透门用。
    Task 10:边界口径下沉到 memory_lifecycle.known_at 作单一真相源(避免时态语义两处漂移),
      行为逐位等价。"""
    return _known_at(known_from, known_to, chapter)


def _reciprocal_rank_fusion(*ranked_lists, k: int = 60):
    """RRF 融合多路排序列表:得分 = Σ 1/(k + rank_in_path)。纯函数。"""
    scores: dict[str, float] = {}
    for lst in ranked_lists:
        for rank, item_id in enumerate(lst, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


def _keyword_search_propositions(store, query: str, chapter: int, top_k: int = 10):
    """中文分词 → 关键词匹配 proposition.value → 返回 Fact 列表(按命中数排序)"""
    import jieba
    keywords = [w for w in jieba.cut(query) if len(w.strip()) >= 2]
    if not keywords:
        return []
    rows = store._query(
        "SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, "
        "secret, leak_markers FROM proposition "
        "WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch) "
        "AND (archived = NONE OR archived != true)", {"ch": chapter})
    scored = []
    for r in rows:
        val = r.get("value", "")
        hits = sum(1 for kw in keywords if kw in val)
        if hits:
            scored.append((hits, r))
    scored.sort(key=lambda x: -x[0])
    top = scored[:top_k]
    return [Fact(f"fact:{r['local']}", r.get("entity_id") or "", r["attribute"], r["value"],
                 r["valid_from"], r.get("valid_to"), r.get("secret", False),
                 r.get("leak_markers", [])) for _, r in top]


# 伏笔超期默认宽限(章)。单源常量:app.py / health.py 均从此处导入,timeline 直用,
# 杜绝多处各写一份魔数导致口径漂移(仅对无窗口 legacy 旧行生效;窗口/tier 行不参与)。
OVERDUE_SLACK = 3


def _overdue_flag(p: dict, max_chapter: int, slack: int) -> bool:
    """伏笔超期单源判定。/promises、/quality、/promises/ledger、timeline、体检 cron 五处共用,
    杜绝口径漂移。

    与 promise_window_state 同口径(next_ch = max_chapter+1):
    - 有窗口(payoff_max 非 None)→ overdue = max_chapter + 1 > payoff_max,slack 不参与;
    - payoff_max 为 None 且 tier=='book' → 书级伏笔永不超期;
    - 无窗口旧行(未经 052 迁移/list_promises 补算的裸 dict)→ legacy:setup + slack < max_chapter。
    setup_chapter 缺失时不判超期(交由 audit 的 closed_without_setup 报数据异常)。
    """
    setup = p.get("setup_chapter")
    if p.get("status") != "open" or p.get("kind") == "red_herring" or setup is None:
        return False
    pmax = p.get("payoff_max")
    if pmax is not None:
        return max_chapter + 1 > pmax
    if p.get("tier") == "book":
        return False
    return setup + slack < max_chapter


_TIER_WINDOW = {"chapter": (1, 3), "arc": (5, 15), "book": (1, None)}


def promise_window_state(p: dict, max_chapter: int) -> dict:
    """伏笔窗口计算态。next_ch = max_chapter+1(即将写的下一章)。
    state ∈ inactive / pre_window / in_window / over_half / overdue。
    salience_gap = 距上次露面(埋设或触及)的章数,供'先刷新再兑现'门槛用。"""
    setup = p.get("setup_chapter")
    if p.get("status") != "open" or p.get("kind") == "red_herring" or setup is None:
        return {"state": "inactive", "salience_gap": None}
    next_ch = max_chapter + 1
    pmin = p.get("payoff_min")
    if pmin is None:  # 旧行回退:按 tier 查窗口下沿(is None 判定,payoff_min=0 是显式值)
        lo, _hi = _TIER_WINDOW.get(p.get("tier") or "chapter", _TIER_WINDOW["chapter"])
        pmin = setup + lo
    pmax = p.get("payoff_max")
    last_seen = max(setup, p.get("last_refresh_at") or setup)
    gap = max_chapter - last_seen
    if next_ch < pmin:
        # payoff_min = 首个可兑现章:next_ch == pmin 时窗口已开(in_window)
        state = "pre_window"
    elif pmax is None:
        state = "in_window"
    elif next_ch > pmax:
        state = "overdue"
    elif next_ch > pmin + (pmax - pmin) / 2:
        state = "over_half"
    else:
        state = "in_window"
    return {"state": state, "salience_gap": gap}


def _compute_streaks(rows: list[dict], today: str, daily_goal: int | None) -> tuple[int, int]:
    """纯函数:从 daily_progress 行列表计算 (current_streak, longest_streak)。
    rows 须按 date 升序排列(store.progress 已保证)。
    达标判定:设了 daily_goal 则 words_written >= daily_goal;否则 words_written > 0。
    current_streak:从 today 往回数连续达标天数;today 未写入时从前一天起算(容忍今天才开始写)。
    longest_streak:扫全部记录的最长连续达标自然日段。
    """
    from datetime import date as _date, timedelta as _td
    threshold = daily_goal if daily_goal is not None else 1
    met: set[_date] = {
        _date.fromisoformat(r["date"])
        for r in rows
        if (r.get("words_written") or 0) >= threshold
    }
    if not met:
        return 0, 0

    # current_streak:从 today(或 today-1)往回连续计数
    try:
        pivot = _date.fromisoformat(today)
    except ValueError:
        pivot = _date.today()
    # 若 today 未达标/未写,从 yesterday 起算(容忍当日还没写)
    if pivot not in met:
        pivot = pivot - _td(days=1)
    cur = 0
    d = pivot
    while d in met:
        cur += 1
        d -= _td(days=1)

    # longest_streak:扫全部 met 集合
    longest = 0
    streak = 0
    sorted_met = sorted(met)
    for i, d in enumerate(sorted_met):
        if i == 0 or d - sorted_met[i - 1] != _td(days=1):
            streak = 1
        else:
            streak += 1
        if streak > longest:
            longest = streak

    return cur, longest


def _split_scenes(prose: str) -> list[dict]:
    """纯函数:按 SceneBreak 约定(* * * / --- 独行)把章正文切成场景段列表。
    返回 [{"title": 前24字首句, "chars": 去空白字数}, ...]。
    无分隔符 → 单段(整章视为一个场景)。
    与前端 SceneBreak.js 的 inputRule 正则保持一致。
    """
    import re
    # 匹配独占一行的 * * * / --- 形式(兼容半角空格变体)
    _SCENE_SEP = re.compile(r'(?m)^\s*(?:\*\s?\*\s?\*|---)\s*$')
    segments = _SCENE_SEP.split(prose)
    result = []
    for seg in segments:
        text = seg.strip()
        if not text:
            continue
        # 首句:取第一个句号/换行前最多 24 字
        first_line = text.split('\n')[0].strip()
        title = first_line[:24]
        chars = len(''.join(text.split()))
        result.append({"title": title, "chars": chars})
    # 若全为空(prose 为空字符串),返回空列表
    return result


def backfill_scalability_caches(store) -> int:
    """回填缺失或旧版的章级派生缓存，返回实际重算章数。

    缓存版本戳确保检测规则或事件图口径升级后不会继续展示旧结果；只在显式
    回填/作者刷新时读取待更新章的正文，常规 outline()/quality() 仍然不读正文。
    """
    return len(store.refresh_quality_caches())


def backfill_material_memory(store) -> int:
    """存量素材记忆化回填:补 tokens+embedding + 建联想边。幂等(只补缺 tokens 者)。返回补齐条数。"""
    rows = store._query("SELECT meta::id(id) AS id, title, body, tokens FROM material")
    n = 0
    for r in (rows or []):
        if r.get("tokens"):
            continue  # 已补,幂等跳过
        try:
            toks, vec = store._material_index_fields(r.get("title"), r.get("body"))
            store._execute_write(
                "UPDATE type::record('material',$m) SET tokens=$t, embedding=$v",
                {"m": r["id"], "t": toks, "v": vec})
            store.build_material_edges(r["id"])
            n += 1
        except Exception:
            pass  # fail-soft 逐条
    return n


def _proposition_tokens_from_text(text: str) -> str:
    """与 semantic_index 同口径：jieba 空格串，最长 2000。"""
    raw = (text or "").strip()
    if not raw:
        return ""
    try:
        import jieba
        return " ".join(w for w in jieba.cut(raw) if len(w.strip()) >= 1)[:2000]
    except Exception:
        return raw[:2000]


def backfill_proposition_tokens(store, *, limit: int = 500, dry_run: bool = False) -> dict:
    """A1: 存量命题补 tokens（不重算 embedding，省内存）。幂等。

    返回 {scanned, updated, skipped, dry_run, errors, limit}。
    """
    lim = max(1, min(int(limit or 500), 5000))
    rows = store._query(
        f"SELECT meta::id(id) AS local, attribute, value, tokens "
        f"FROM proposition LIMIT {lim};"
    ) or []
    scanned = updated = skipped = errors = 0
    for r in rows:
        if not isinstance(r, dict) or not r.get("local"):
            continue
        scanned += 1
        if str(r.get("tokens") or "").strip():
            skipped += 1
            continue
        text = f"{r.get('attribute') or ''} {r.get('value') or ''}".strip()
        toks = _proposition_tokens_from_text(text)
        if not toks:
            skipped += 1
            continue
        if dry_run:
            updated += 1
            continue
        try:
            store._execute_write(
                "UPDATE type::record('proposition', $local) SET tokens=$tok;",
                {"local": r["local"], "tok": toks},
            )
            updated += 1
        except Exception:
            errors += 1
    return {
        "scanned": scanned,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "dry_run": bool(dry_run),
        "limit": lim,
    }


# ===========================================================================
# 统一上下文与记忆系统 · Task 14:记忆溯源 trace 的映射 + 服务端权威屏蔽
#
# 边界(诚实):trace 基础设施(schema / 落库 / 屏蔽 / API / UI)就绪,但当前
#   【无生产检索调用方】把 RetrievalResult 灌进 trace——检索接进写作 prompt 是
#   Task 16 envelope 灰度才做。build_memory_trace 是就绪的映射接口,真实 trace
#   数据待 Task 16 检索生产接线后由检索发生处调用它 + save_memory_trace 落库。
#   在此之前 memory_trace 表基本为空,GET trace API 多返 404(前端显"未检索到证据")。
# ===========================================================================

# trace 里私密证据的屏蔽占位:前端 UI 只显此语义,绝不显 value(限知红线)。
_TRACE_SECRET_MASK = "秘密事实已屏蔽"


def _mask_trace_item(item, secret_ids=None):
    """单条证据屏蔽:secret 为真时抹掉 text/value,只留 masked 标记(不可逆)。

    C1 对齐(宪法级):秘密判定 = provenance/item 自标 secret 【OR】 source_id ∈ store 权威
    secret 集(secret_ids)。retriever 漏标(item.secret=False)但 source_id 是 store 权威
    秘密时,一律屏蔽——裁决权归 store,不归 retriever(参照 context_assembler._secret_fact_ids)。
    权威判定为真时回写 secret=True,使兜底重掩(GET 无 secret_ids 时)与 DB at-rest 都一致。"""
    if not isinstance(item, dict):
        return item
    is_secret = bool(item.get("secret"))
    if not is_secret and secret_ids and item.get("source_id") in secret_ids:
        is_secret = True
    if not is_secret:
        return item
    masked = dict(item)
    masked["secret"] = True        # 回写权威判定(retriever 漏标时补齐),DB/GET 皆一致
    masked["masked"] = True
    masked["text"] = ""
    masked.pop("value", None)      # 任何私密明文字段一并清除
    return masked


# ===========================================================================
# 统一上下文与记忆系统 · Task 16-A:ai_run_trace 落库前统一 redactor
#
# 为什么:ai_run_trace 的 tool_calls/tool_outputs/raw_events/response 承载【不可信】
#   工具 I/O 与原始 Hermes 事件——HTTP 工具调用可能夹带 Authorization/Bearer/api_key
#   认证头,秘密事实的真值也可能被工具原样回抛。trace 是可导出/可回放的审计物,
#   落库前必须过一遍统一 redactor(与 memory_trace 的 mask_memory_trace 同纪律:
#   屏蔽只发生在服务端,DB at-rest 永不持有认证头/秘密明文)。
# 边界:只抹 tool/runtime 自由字段;不动作者自撰的 input_text/instructions(那是 run
#   自身的 prompt,抹秘密 value 会破坏作者真实意图);不动 session_key(是按 work 派生的
#   Runs 关联键,非泄漏进 trace 的凭据,语义由现有 _run_session_key 拥有,本任务不碰)。
# ===========================================================================

# 认证类字段名(dict 键命中即整值屏蔽)与令牌形态(字符串内正则替换)。
_RUN_AUTH_KEY_RE = re.compile(
    r"authorization|proxy-authorization|api[_-]?key|apikey|x-api-key|"
    r"access[_-]?token|bearer|cookie|set-cookie|passwo?rd|"
    r"x-hermes-session-key|session[_-]?key", re.I)
_RUN_AUTH_MASK = "已屏蔽·认证"
# 字符串内令牌/凭据的抹除规则。顺序讲究:①/② 先把带头名的整条凭据(方案词+令牌/整值)
# 一并吞掉,再由 ③④⑤ 兜底裸令牌。C-1 教训:若头规则的 \S+ 只吞方案词("Bearer"),
# 会把方案词消费掉致后续 bearer 规则匹配不到、真凭据留明文——故 ① 显式吞「方案词 + 凭据」。
_RUN_AUTH_VALUE_SUBS = (
    # ① Authorization / Proxy-Authorization: [Bearer|Basic|Digest|Token] <凭据> —— 方案词+凭据一起抹
    (re.compile(r"(?i)\b(proxy-authorization|authorization)\b\s*[:=]\s*"
                r"(?:(?:bearer|basic|digest|token)\s+)?\S+"),
     r"\1: " + _RUN_AUTH_MASK),
    # ② Cookie / Set-Cookie: <值到行尾>(cookie 常多段;I-2:字符串内嵌形式此前漏抹)
    (re.compile(r"(?i)\b(set-cookie|cookie)\b\s*[:=]\s*[^\r\n]+"),
     r"\1: " + _RUN_AUTH_MASK),
    # ③ 裸 Bearer/Basic 令牌(无 Authorization 前缀的内嵌形式)
    (re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._+/=\-]+"), _RUN_AUTH_MASK),
    # ④ api_key / access_token / token / password = ... 形式
    (re.compile(r"(?i)\b(api[_-]?key|apikey|access[_-]?token|token|passwo?rd)\b\s*[:=]\s*\S+"),
     r"\1=" + _RUN_AUTH_MASK),
    # ⑤ 高熵密钥令牌裸形态:sk-ant-...(带连字符,C-1:旧 sk-[A-Za-z0-9]{8,} 匹配不到)/ sk-... /
    #    GitHub ghp_ 等 / JWT eyJ....（M-1:无标签高熵串固有局限,此处覆盖常见带前缀形态)
    (re.compile(r"\bsk-[A-Za-z0-9]{2,}(?:-[A-Za-z0-9]+)*\b"), _RUN_AUTH_MASK),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{8,}\b"), _RUN_AUTH_MASK),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{4,}\b"),
     _RUN_AUTH_MASK),
)

# I-1:单字秘密真值(中文单字名讳/真名极常见)只在【有界上下文】屏蔽——名讳引导词后 /
# 引号书名号包裹内——而非全文裸单字替换(那会误伤正文里同字的普通用法)。
_SECRET_NAME_CUE = (
    r"真名|名讳|本名|表字|名字|名号|名叫|叫做|唤作|名为|名曰|其名|就是|正是|叫|唤|讳|号|名")


def _mask_short_secret(s: str, c: str) -> str:
    """把单字秘密真值 c 在有界上下文里替换为屏蔽占位(保留上下文,只抹该字)。fail-soft。"""
    esc = re.escape(c)
    # ① 名讳引导词(可带 是/为/叫/作/曰)+ 可选开引号 + 该字(+ 可选闭引号)
    s = re.sub(
        r"((?:" + _SECRET_NAME_CUE + r")(?:是|为|叫|作|曰)?[\s：:]*[「『“\"'（(]?)"
        + esc + r"([」』”\"'）)]?)",
        r"\1" + _TRACE_SECRET_MASK + r"\2", s)
    # ② 显式引号/书名号包裹的单字
    s = re.sub(r"([「『“])" + esc + r"([」』”])",
               r"\1" + _TRACE_SECRET_MASK + r"\2", s)
    return s


def _redact_run_trace_secrets(obj, secret_values=None):
    """递归抹认证头/令牌 + 已知秘密事实真值。幂等(已屏蔽串不再命中)、fail-soft。

    - dict:键命中 _RUN_AUTH_KEY_RE → 整值置屏蔽占位;否则递归其值;
    - list/tuple:逐项递归;
    - str:先过令牌形态正则,再抹已知秘密 value(len≥2 全文子串替换;单字走有界屏蔽);
    - 其它标量:原样返回。"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and _RUN_AUTH_KEY_RE.search(k):
                out[k] = _RUN_AUTH_MASK
            else:
                out[k] = _redact_run_trace_secrets(v, secret_values)
        return out
    if isinstance(obj, (list, tuple)):
        return [_redact_run_trace_secrets(x, secret_values) for x in obj]
    if isinstance(obj, str):
        s = obj
        for pat, repl in _RUN_AUTH_VALUE_SUBS:
            s = pat.sub(repl, s)
        for sv in (secret_values or ()):
            if not sv:
                continue
            if len(sv) >= 2:
                if sv in s:
                    s = s.replace(sv, _TRACE_SECRET_MASK)
            else:
                s = _mask_short_secret(s, sv)   # 单字:有界屏蔽,不裸替换
        return s
    return obj


def mask_memory_trace(trace, secret_ids=None):
    """服务端权威屏蔽(单一真相源):selected/rejected 里私密证据的 value 绝不出服务端。

    幂等:重复屏蔽不误伤非私密证据、不复原私密。落库前(save)与出参前(GET API)
    都过一遍——参照 Task 7"前端不可信"教训,屏蔽只发生在服务端。
    secret_ids(可选):store 权威 secret fact id 集;传入时叠加"source_id ∈ 集即屏蔽"的
    C1 判定,补齐 retriever 漏标弱路径(save_memory_trace 落库前必传,见 _secret_fact_ids)。"""
    if not isinstance(trace, dict):
        return trace
    t = dict(trace)
    t["selected"] = [_mask_trace_item(x, secret_ids) for x in (trace.get("selected") or [])]
    t["rejected"] = [_mask_trace_item(x, secret_ids) for x in (trace.get("rejected") or [])]
    return t


def _trace_candidate_secret(cand) -> bool:
    """候选是否携私密:canonical 事实的 provenance 项带 secret=True 即私密。"""
    for p in (getattr(cand, "provenance", None) or []):
        if isinstance(p, dict) and p.get("secret"):
            return True
    return False


def _trace_candidate_reason(cand) -> str:
    """选入理由(可解释):正典恒选 / pin 常驻 / 否则按相关性排名选入。"""
    if getattr(cand, "source_kind", "") == "canonical":
        return "canonical"
    if getattr(cand, "pinned", False):
        return "pinned"
    return "relevance_rank"


def _trace_candidate_item(cand, reason: str) -> dict:
    """MemoryCandidate → trace 证据 dict(source id / 时态 / 信心 / 理由 + secret 标记)。
    secret 为真时 text 置空(此处即抹,不依赖后续 mask)。"""
    secret = _trace_candidate_secret(cand)
    obs = getattr(cand, "observed_at", None)
    return {
        "source_id": getattr(cand, "source_id", ""),
        "source_kind": getattr(cand, "source_kind", ""),
        "reason": reason,
        "confidence": getattr(cand, "confidence", 1.0),
        "importance": getattr(cand, "importance", 2),
        # 时态:canonical 恒真无时间戳(None);经验记忆带 observed_at(ISO)
        "observed_at": obs.isoformat() if hasattr(obs, "isoformat") else obs,
        "channels": sorted(getattr(cand, "channels", set()) or set()),
        "final_score": getattr(cand, "final_score", 0.0),
        "secret": secret,
        "text": "" if secret else (getattr(cand, "text", "") or ""),
    }


def build_memory_trace(*, trace_id, work, thread_id, context_session_id,
                       snapshot_revision, result, query="", snapshot_hash="",
                       envelope_hash="", channels=None, block_tokens=None,
                       latency_ms=None, response_id=None, run_id=None,
                       store=None) -> dict:
    """RetrievalResult(Task 8)→ memory_trace dict(Task 14 溯源)。

    生产接线(Task 16)在检索发生处调用:把当次 RetrievalResult 的 selected/rejected
    映射成可审计证据(带 reason + 时态 + 信心),secret 由 provenance 判定并屏蔽,
    再交 save_memory_trace 落库。selected 的 reason 由 _trace_candidate_reason 派生,
    rejected 的 reason 直接透传 RejectedCandidate.reason(如 conflicts_with_canonical)。

    store(可选):传入时叠加 C1 权威 secret 判定(source_id ∈ 权威 secret 集即屏蔽),
    补齐 retriever 漏标弱路径——Task 16 接线务必传 store,否则 provenance 漏标即秘密明文
    残留。即便此处未传,save_memory_trace(有 self=store)仍会在落库前权威兜底(at-rest 保证)。"""
    selected = [_trace_candidate_item(c, _trace_candidate_reason(c))
                for c in getattr(result, "selected", [])]
    rejected = [_trace_candidate_item(r.candidate, r.reason)
                for r in getattr(result, "rejected", [])]
    secret_ids = None
    if store is not None:
        from scribe3.context_assembler import _secret_fact_ids
        # U-011(作者要 fail-loud):删"失败退None"——None=退回更弱的 provenance 判定=秘密
        # 可能漏抹(fail-open)。_secret_fact_ids 失败直接抛,不静默降级。
        secret_ids = _secret_fact_ids(store)
    return mask_memory_trace({
        "trace_id": trace_id,
        "work": work,
        "thread_id": thread_id,
        "context_session_id": context_session_id,
        "snapshot_revision": int(snapshot_revision),
        "snapshot_hash": snapshot_hash or "",
        "envelope_hash": envelope_hash or "",
        "query": query or "",
        "channels": channels or {},
        "selected": selected,
        "rejected": rejected,
        "block_tokens": block_tokens or {},
        "latency_ms": latency_ms or {"total": 0},
        "response_id": response_id,
        "run_id": run_id,
    }, secret_ids=secret_ids)

__all__ = [n for n in list(globals()) if not (n.startswith("__") and n.endswith("__"))]
