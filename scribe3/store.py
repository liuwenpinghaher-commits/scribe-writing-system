"""SurrealStore · 故事本体 v2 的 SurrealDB 持久层(NS=scribe3)。

把纵切片的内存 World 迁到 SurrealDB,接口与 World 鸭子兼容——knowledge.project_frame /
knowledge.project_frame 不改一行即可跑在真库上(证限知范式在持久层照样成立)。

不变量:**改世界状态只经 _execute_write 单一落库点**(开发标准 §0 不变量1)。
oid 映射:本体 id(role:焦三 / fact:治眼)↔ SurrealDB record(character:焦三 / proposition:治眼)。
"""
from __future__ import annotations

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

from scribe3.context_models import (
    ContextFocus, ContextSnapshot, NavigationIntent, StaleContextError,
)
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
_UNSET = object()       # update_chapter_meta 的哨兵:区分"未传 volume"与"传了 None"


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


def list_works(url: str | None = None) -> list[dict]:
    """列所有书。空则自动登记 main=乱世铜炉(现有数据所在 DB)。"""
    db = _reg_conn(url)
    try:
        rows = db.query("SELECT * FROM work")
        if not rows:
            db.query("CREATE work:main CONTENT { slug:'main', title:'乱世铜炉·设定参照', ord:0 }")
            return [{"slug": "main", "title": "乱世铜炉·设定参照"}]
        rows = sorted(rows, key=lambda r: r.get("ord") or 0)
        return [{"slug": r.get("slug"), "title": r.get("title")} for r in rows]
    finally:
        db.close()


def delete_work(slug: str, url: str | None = None) -> None:
    """删一本书:注册表删除 + 丢弃其独立 DB。主书 main 不可删。"""
    if slug == "main":
        raise ValueError("不能删除主书 main")
    if not all(c.isalnum() or c == "_" for c in slug):
        raise ValueError("非法 slug")
    db = _reg_conn(url)
    try:
        db.query("DELETE type::record('work',$s)", {"s": slug})
        db.query(f"REMOVE DATABASE IF EXISTS {slug}")
    finally:
        db.close()


def rename_work(slug: str, title: str, url: str | None = None) -> None:
    db = _reg_conn(url)
    try:
        db.query("UPDATE type::record('work',$s) SET title=$t", {"s": slug, "t": title})
    finally:
        db.close()


def create_work(title: str, slug: str | None = None, url: str | None = None) -> dict:
    """建一本书:注册表登记 + 给它的独立 DB 建 schema。slug=该书 DB 名(ascii)。"""
    import uuid
    slug = slug or ("book_" + uuid.uuid4().hex[:8])
    db = _reg_conn(url)
    try:
        db.query("CREATE type::record('work',$s) SET slug=$s, title=$t, created=time::now()",
                 {"s": slug, "t": title})
    finally:
        db.close()
    st = SurrealStore(url=url, ns="scribe3", db=slug)
    st.apply_schema()
    st.close()
    return {"slug": slug, "title": title}


_TABLES = frozenset(list(ONT2TBL.values()) + ["promise", "motif", "motif_instance",
                                              "promise_touch", "arc_plan", "material",
                                              "relation_touch"])

# 素材库分类白名单(migration 055 DB 级 ASSERT 同源;app 层 422 校验用)。
# emotion_module(方案B任务15,migration 060 DB 级 ASSERT 同步):EM-001情绪模块卡/
# RH-001爽点循环/TR-001触动点三张互引 schema 统一挂此 kind,卡内容(JSON)自带
# id 前缀 EM-/RH-/TR- 自行区分类型,互引用 id 字符串(如 escalation 步骤引用其他卡 id)。
MATERIAL_KINDS = ("research", "reference", "snippet", "inspiration", "note", "emotion_module")

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
    "motif": frozenset({"name", "theme", "echoes", "unfolding"}),
    "material": frozenset({"title", "body", "kind", "tags", "source", "ref_tags",
                           "tokens", "embedding", "about_entities", "pinned",
                           "archived", "recall_count", "last_recalled_at"}),
}


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
    """存量章回填(Phase0-BE1):对缓存为空的现有 chapter 重算 scene_count/scene_meta/
    qc_issues/qc_causal 并写列。返回回填的章数。

    幂等:只回填 scene_count IS NONE 的章(已写过缓存的 save_chapter 章跳过)。
    一次性拉这些章的 prose(仅未回填章,非全书),算完写列即丢——迁移期一次成本,
    之后 outline()/quality() 永不再拉正文。供 apply_schema 后调用或迁移脚本手动跑。
    """
    rows = store._query(
        "SELECT seq, prose FROM chapter:.. WHERE scene_count IS NONE")
    n = 0
    for r in rows:
        seq = r.get("seq")
        if seq is None:
            continue
        prose = r.get("prose") or ""
        cache = store._compute_chapter_caches(seq, prose)
        store._execute_write(
            "UPDATE type::record('chapter', $seq) SET "
            "scene_count=$scn, scene_meta=$scm, qc_issues=$qc, qc_causal=$qcc, qc_breakdown=$qcb",
            {"seq": seq, "scn": cache["scene_count"], "scm": cache["scene_meta"],
             "qc": cache["qc_issues"], "qcc": cache["qc_causal"], "qcb": cache["qc_breakdown"]})
        n += 1
    return n


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


class SurrealStore:
    """SurrealDB 后端的 World。默认连 NS=scribe3 / DB=main(与 scribe2 的 NS=scribe 隔离)。"""

    def __init__(self, url: str | None = None, ns: str = "scribe3", db: str = "main",
                 user: str | None = None, password: str | None = None):
        self.url = url or os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc")
        self.db_name = db   # 本库名(=work);chat_message.work 等冗余字段由此自动填(台账 D-002)
        self._ns = ns
        self._user = user or os.environ.get("SCRIBE3_SURREAL_USER", "root")
        self._password = password or os.environ.get("SCRIBE3_SURREAL_PASS", "root")
        self._connect()

    def _connect(self) -> None:
        self._db = Surreal(self.url)
        self._db.signin({"username": self._user, "password": self._password})
        self._db.use(self._ns, self.db_name)

    def _reconnect(self) -> None:
        try:
            self._db.close()
        except Exception:
            pass
        self._connect()

    def _raw_query(self, surql: str, vars: dict | None = None):
        """S-1 连接韧性单点(2026-07-04 :8001 事故根治):连接类异常 → 重建连接
        (signin/use 是 WS 连接级状态,SDK 懒重连不会重放)→ 重试一次。
        本机 WS 不存在"已提交但响应丢失"的分区窗口(服务端死=写未提交),
        且核心写多为 UPSERT 幂等,故写路径重试一次可接受。
        语法/校验等非连接错误原样抛,绝不重试。"""
        try:
            return self._db.query(surql, vars or {})
        except _CONN_ERRORS as e:
            logging.getLogger("scribe3.store").warning(
                "SurrealDB 连接故障,重连后重试一次(%s): %s",
                type(e).__name__, str(e)[:120])
            self._reconnect()
            return self._db.query(surql, vars or {})

    def close(self) -> None:
        try:
            self._db.close()
        except Exception as e:
            logging.getLogger("scribe3.store").warning("store.close 失败: %s", e)

    # --- schema ---
    def apply_schema(self, migrations_dir: str | None = None) -> None:
        d = Path(migrations_dir or Path(__file__).parent / "migrations")
        self._raw_query("DEFINE TABLE IF NOT EXISTS _migration SCHEMALESS; "
                        "DEFINE FIELD IF NOT EXISTS applied_at ON _migration TYPE datetime;")
        try:
            rows = self._query("SELECT meta::id(id) AS id FROM _migration")
            applied = {f"_migration:{r['id']}" for r in (rows or []) if r and r.get("id")}
        except Exception:
            applied = set()
        # P1-7:迁移全用 IF NOT EXISTS / OVERWRITE(幂等重放本就无害,不会报错),
        # 故运行中的任何异常都是真失败(连接抖动/语法错)——绝不能标记已应用,
        # 否则该迁移被永久跳过、schema 静默漂移。失败者不写 _migration 记录、聚合后向上抛,
        # 保证下次启动可重试;成功者照常标记。
        failures: list[tuple[str, str]] = []
        for f in sorted(d.glob("*.surql")):
            key = f"_migration:{f.stem}"
            if key in applied:
                continue
            try:
                self._raw_query(f.read_text(encoding="utf-8"))
            except Exception as e:
                logging.getLogger("scribe3").warning(
                    "迁移 %s 失败,不标记已应用(下次可重试): %s", f.stem, str(e)[:120])
                failures.append((f.stem, str(e)[:120]))
                continue  # 真失败:跳过 CREATE _migration 记录
            self._raw_query("CREATE type::record('_migration', $name) SET applied_at = time::now()",
                            {"name": f.stem})
        if failures:
            raise RuntimeError(
                "apply_schema 迁移失败清单(未标记已应用): "
                + "; ".join(f"{n}: {e}" for n, e in failures))
        # Task 6:回填存量对话史进默认主编线程(幂等且代价小——只 UPDATE thread_id IS NONE)。
        # fail-soft:失败只告警不阻断启动(线程回填非启动关键路径;下次启动可再试)。
        try:
            self.backfill_thread_ids()
        except Exception:
            logging.getLogger("scribe3").warning(
                "backfill_thread_ids 失败(不阻断启动,下次可重试)", exc_info=True)

    # --- 唯一写入点 ---
    def _execute_write(self, surql: str, vars: dict) -> None:
        """改世界状态的唯一落库点。所有 add_* 经此(开发标准不变量1)。"""
        self._raw_query(surql, vars)

    @contextmanager
    def transaction(self):
        """关键多步写的事务边界。收集块内写,退出时拼为单条多语句提交。
        SurrealDB Python SDK 不支持跨 query() 调用事务,需拼成单条 surql。"""
        old = self._execute_write
        stmts: list[tuple[str, dict]] = []

        def _collect(surql: str, vars: dict) -> None:
            stmts.append((surql, vars))

        self._execute_write = _collect
        try:
            yield
            if stmts:
                self._commit_transaction(stmts, old)
        except Exception:
            try:
                old("CANCEL TRANSACTION", {})
            except Exception:
                pass
            raise
        finally:
            self._execute_write = old

    def _commit_transaction(self, stmts: list[tuple[str, dict]], old):
        """将收集的语句拼成单条多语句 surql 并提交。"""
        import re as _re
        parts = []
        all_vars: dict = {}
        for i, (s, v) in enumerate(stmts):
            s_num = _re.sub(r'\$([a-zA-Z_]\w*)', rf'$\1___{i}', s)
            for key, val in v.items():
                all_vars[f"{key}___{i}"] = val
            parts.append(s_num)
        surql = "BEGIN TRANSACTION; " + "; ".join(parts) + "; COMMIT TRANSACTION;"
        old(surql, all_vars)

    def _query(self, surql: str, vars: dict | None = None) -> list[dict]:
        res = self._raw_query(surql, vars or {})
        # surrealdb-py 2.0:SELECT 直接返回 rows 列表;兼容包一层 {"result":...} 的旧形态
        if isinstance(res, list):
            if res and isinstance(res[0], dict) and "result" in res[0] and "status" in res[0]:
                return res[-1].get("result") or []
            return res
        if isinstance(res, dict) and "result" in res:
            return res["result"] or []
        return res or []

    # --- 写(全经 _execute_write)---
    def add_entity(self, e: Entity) -> Entity:
        _, local = _split(e.id)
        if e.kind == "character":
            self._execute_write(
                "CREATE type::record('character', $local) SET name=$name, aliases=$al, "
                "backstory=$bs, personality_tags=$pt, backstory_secret=$bss",
                {"local": local, "name": e.name, "al": e.traits.get("aliases", []),
                 "bs": e.traits.get("backstory"),
                 "pt": e.traits.get("personality_tags", []),
                 "bss": e.traits.get("backstory_secret", False)})
        elif e.kind == "place":
            self._execute_write("CREATE type::record('place', $local) SET name=$name",
                                {"local": local, "name": e.name})
        return e

    def add_fact(self, f: Fact, ingest_seq: int | None = None) -> Fact:
        _, local = _split(f.id)
        self._execute_write(
            "UPSERT type::record('proposition', $local) SET entity_id=$entity, "
            "attribute=$attr, value=$value, valid_from=$vf, valid_to=$vt, secret=$secret, "
            "leak_markers=$lm"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"local": local, "entity": f.entity_id, "attr": f.attribute, "value": f.value,
             "vf": f.valid_from, "vt": f.valid_to, "secret": f.secret, "lm": f.leak_markers,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        # 写入后建语义索引(与 s3_add_fact 对齐;embed 失败不阻断主写)
        try:
            self.semantic_index(f.id, f.value)
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "add_fact: embedding 失败,命题 %s 将不可语义召回: %s", f.id, _e)
        return f

    def add_knowledge(self, k: KnowledgeEdge, ingest_seq: int | None = None) -> KnowledgeEdge:
        if k.knower_id == "reader":   # reader 帧:单独表,不走 character->knows 边
            # 写 ingest_seq 供 purge_ingest 幂等清理;手动种的边 ingest_seq=NONE 不受 purge 影响
            self._execute_write(
                "CREATE reader_knows SET proposition=$p, since_chapter=$since"
                + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
                {"p": k.proposition_id, "since": k.since_chapter,
                 **({"iseq": ingest_seq} if ingest_seq is not None else {})})
            return k
        # P3-b: 验证 knower 端实体存在,防悬挂边(reader 已在上方提前返回)
        if self.entity(k.knower_id) is None:
            raise ValueError(
                f"add_knowledge: knower '{k.knower_id}' 不存在,拒绝写入悬挂边。"
                f"请先建立角色实体,或使用 'reader' 作为虚拟 knower。"
            )
        ktbl, klocal = _split(k.knower_id)
        ptbl, plocal = _split(k.proposition_id)
        # RELATE 箭头位不接受内联函数,用 RecordID 绑参
        self._execute_write(
            "RELATE $k->knows->$p SET since_chapter=$since, until_chapter=$until, "
            "polarity=$pol, acquired_via=$via, certainty=$cert"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"k": RecordID(ktbl, klocal), "p": RecordID(ptbl, plocal),
             "since": k.since_chapter, "until": k.until_chapter, "pol": k.polarity,
             "via": k.acquired_via, "cert": k.certainty,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        return k

    def supersede_fact(self, entity_id: str, attribute: str, new_value: str,
                       since_chapter: int, secret: bool = False) -> str:
        """显式超越:关闭同一 entity+attribute 的所有开区间先驱,写入新命题。
        仅关闭 valid_to=NONE(还活着)且 valid_from < since_chapter 的行,
        不动多值同属性(调用方显式控制,不自动破坏多值)。
        返回新命题的 oid。"""
        import uuid
        # 1. 关闭所有该 entity+attribute 的开区间先驱
        self._execute_write(
            "UPDATE proposition SET valid_to=$since "
            "WHERE entity_id=$e AND attribute=$a AND valid_to=NONE AND valid_from<$since",
            {"e": entity_id, "a": attribute, "since": since_chapter})
        # 2. 写入新命题
        new_oid = f"fact:{uuid.uuid4().hex[:8]}"
        new_fact = Fact(new_oid, entity_id, attribute, new_value, valid_from=since_chapter, secret=secret)
        self.add_fact(new_fact)
        return new_oid

    def forget_knowledge(self, knower_id: str, proposition_id: str, until_chapter: int) -> None:
        """设置知识边的 until_chapter(令知识在该章起失效)。
        P2-a Fix2: 仅更新开区间边(until_chapter IS NONE),与 supersede_fact 对齐——
        已闭合的边(until_chapter 已设置)不被覆写,防止重复 forget 破坏历史记录。"""
        ktbl, klocal = _split(knower_id)
        ptbl, plocal = _split(proposition_id)
        self._execute_write(
            "UPDATE knows SET until_chapter=$uc "
            "WHERE in=$k AND out=$p AND until_chapter IS NONE",
            {"uc": until_chapter,
             "k": RecordID(ktbl, klocal),
             "p": RecordID(ptbl, plocal)})

    def add_event(self, ev: Event, ingest_seq: int | None = None) -> Event:
        """落事件 + 图边(involves/causes/causal)。
        ingest_seq:由 ingest 抽取路径传入(批D P1-5),供 purge_ingest 幂等清理;
        手动种 / MCP s3_add_event 不传 → ingest_seq=NONE,不受 purge 影响(向后兼容)。"""
        _, local = _split(ev.id)
        ev_rid = RecordID("event", local)
        loc_local = _split(ev.location)[1] if ev.location else None
        self._execute_write(
            "CREATE type::record('event', $local) SET event_type=$t, "
            "story_chapter=$vf, narrative_position=$np, "
            "motivated_by_goal=$g, location=$loc, preconditions=$pre"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"local": local, "t": ev.type, "vf": ev.story_time, "g": ev.motivated_by_goal,
             "np": ev.narrative_position,  # 完整期:可空叙事位;null 回退 story_chapter(向后兼容)
             "loc": RecordID("place", loc_local) if loc_local else None,
             "pre": ev.preconditions,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        # participants → involves 图边
        for slot, ent_oid in ev.participants.items():
            if not ent_oid:
                continue
            ctbl, clocal = _split(ent_oid)
            if ctbl != "character":
                continue
            self._execute_write(
                "RELATE $e->involves->$c SET role=$role",
                {"e": ev_rid, "c": RecordID("character", clocal), "role": slot})
        # effects → causes 图边(供 see_event 给在场者发知识边)
        for fid in ev.effects:
            _, flocal = _split(fid)
            self._execute_write(
                "RELATE $e->causes->$p",
                {"e": ev_rid, "p": RecordID("proposition", flocal)})
        # causal_in → causal 图边
        for src_oid, ctype in ev.causal_in:
            _, slocal = _split(src_oid)
            self._execute_write(
                "RELATE $e->causal->$src SET ctype=$ct",
                {"e": ev_rid, "src": RecordID("event", slocal), "ct": ctype})
        return ev

    def grant_public(self, fact_id: str, chapter: int) -> None:
        """给所有角色发一条 given 知识边(事务内执行)。"""
        _, plocal = _split(fact_id)
        stmts = []
        for c in self.characters():
            ctbl, clocal = _split(c.id)
            stmts.append(
                f"RELATE {ctbl}:`{clocal}`->knows->proposition:`{plocal}` "
                f"SET since_chapter={chapter}, acquired_via='given'")
        if stmts:
            surql = "BEGIN TRANSACTION; " + "; ".join(stmts) + "; COMMIT TRANSACTION;"
            self._raw_query(surql)

    def purge_ingest(self, seq: int) -> None:
        """删除某章 ingest 产出的命题 + knows 边 + reader_knows 边 + char_state(幂等再 ingest 的前置清理)。
        只清 ingest_seq=seq,作者直编/种子(ingest_seq=NONE)不动。

        learned 跨章复用保护:删命题前检查是否有【他章】的 knows/reader_knows 边仍引用该命题
        (ingest_seq != seq)。有则保留命题本身,只删本章的边——防止 B 章复用 A 章命题,
        重 ingest A 时把命题删掉导致 B 的 knows 边悬空。"""
        # 1. 先删本章的 knows / reader_knows 边(无论命题是否保留)
        self._execute_write("DELETE knows WHERE ingest_seq = $seq", {"seq": seq})
        self._execute_write("DELETE reader_knows WHERE ingest_seq = $seq", {"seq": seq})
        # 2. 查本章命题中哪些在他章仍有 knows 边引用(跨章复用命题)
        #    先取本章全部命题 id
        own_props = self._query(
            "SELECT meta::id(id) AS local FROM proposition WHERE ingest_seq = $seq",
            {"seq": seq})
        for row in own_props:
            local = row.get("local")
            if not local:
                continue
            # 检查 knows 边:除本章外是否还有其它章的边指向该命题
            other_knows = self._query(
                "SELECT count() AS n FROM knows "
                "WHERE out = type::record('proposition', $local) AND ingest_seq != $seq",
                {"local": local, "seq": seq})
            other_rk = self._query(
                "SELECT count() AS n FROM reader_knows "
                "WHERE proposition = type::record('proposition', $local) AND ingest_seq != $seq",
                {"local": local, "seq": seq})
            has_other = (
                (other_knows and (other_knows[0].get("n") or 0) > 0) or
                (other_rk and (other_rk[0].get("n") or 0) > 0)
            )
            if not has_other:
                # 无他章引用:安全删除
                self._execute_write(
                    "DELETE type::record('proposition', $local)",
                    {"local": local})
            # 有他章引用:保留命题,仅边已在步骤1删除
        # 3. char_state 无跨章复用问题,直接清
        self._execute_write("DELETE char_state WHERE ingest_seq = $seq", {"seq": seq})
        # 4. P2-a Fix5: 清本章 ingest_unverified 记录——重 ingest 时防止累积重复 pending。
        # 审计 C-3:只清 pending——accepted/ignored 是人的决策,re-ingest 不得抹掉
        # (否则同名再被抽到即"复活"回待办,人反复裁同一个名字)。
        self._execute_write("DELETE ingest_unverified WHERE seq = $seq AND status = 'pending'",
                            {"seq": seq})
        # 审计 C-2:ingest 路径产的 voice_evolution_flag 同步幂等清除(re-ingest 防累积);
        # 手动/无 ingest_seq 的 flag 不动。
        self._execute_write("DELETE voice_evolution_flag WHERE ingest_seq = $seq", {"seq": seq})
        # 5. 母题章实例:随本章 ingest 幂等清除
        self._execute_write("DELETE motif_instance WHERE ingest_seq = $seq", {"seq": seq})
        # 6. 伏笔章触及:随本章 ingest 幂等清除(手动登记 ingest_seq=NONE 不受影响)
        self._execute_write("DELETE promise_touch WHERE ingest_seq = $seq", {"seq": seq})
        # 6b. 方案B任务12:关系触碰(本章角色对之间的有效触碰),随本章 ingest 幂等清除。
        #     relation_touch 无独立 ingest_seq 字段(表结构见 migrations/058),按 chapter 清除。
        #     Minor(收尾清理批):手动登记的关系触碰会被同章重 ingest 冲掉(无 promise_touch
        #     式 ingest_seq 保护),未来开放手动登记入口时需先加字段。
        self._execute_write("DELETE relation_touch WHERE chapter = $seq", {"seq": seq})
        # 7. 事件图(批D P1-5):随本章 ingest 幂等清除本章抽取的事件 + 图边。
        #    先删图边(involves/causes/causal)再删事件本体——否则 RELATE 边悬挂指向已删事件。
        #    只清 ingest_seq=seq:手动种 / MCP s3_add_event(ingest_seq=NONE)的事件不动。
        # 审计 M2:原 causal 一句里子查询出现两次=执行两次;先取 ids 参数化,零子查询。
        ev_ids = self._query("SELECT VALUE id FROM event WHERE ingest_seq = $seq", {"seq": seq})
        if ev_ids:
            self._execute_write("DELETE involves WHERE in IN $ids", {"ids": ev_ids})
            self._execute_write("DELETE causes WHERE in IN $ids", {"ids": ev_ids})
            self._execute_write("DELETE causal WHERE in IN $ids OR out IN $ids", {"ids": ev_ids})
            self._execute_write("DELETE event WHERE ingest_seq = $seq", {"seq": seq})

    def add_unverified_ref(self, name: str, seq: int, role: str) -> None:
        """登记 ingest 抽到的库外角色名→待确认(不建实体、不发边)。
        审计 C-3:同名已被人裁决(ignored/accepted)则不再登记——决策跨 re-ingest 存活。"""
        decided = self._query(
            "SELECT id FROM ingest_unverified WHERE name=$n AND status != 'pending' LIMIT 1",
            {"n": name})
        if decided:
            return
        self._execute_write(
            "CREATE ingest_unverified SET name=$n, seq=$s, role=$r, status='pending'",
            {"n": name, "s": seq, "r": role})

    def set_unverified_status(self, uid: str, status: str) -> None:
        """裁决待确认条目(pending→ignored/accepted;accept 的建实体流程在 accept_unverified)。"""
        self._execute_write(
            "UPDATE type::record('ingest_unverified',$uid) SET status=$st",
            {"uid": uid, "st": status})

    def list_unverified(self, status: str = "pending") -> list[dict]:
        """列待确认条目(pending/accepted/ignored)。"""
        return self._query(
            "SELECT meta::id(id) AS id, name, seq, role, status "
            "FROM ingest_unverified WHERE status=$st", {"st": status})

    def accept_unverified(self, uid: str, complete_fn=None) -> dict:
        """接受待确认引用:若 role:{name} 不存在则建角色,标记该行 accepted,并重放该章 ingest 回填被阻塞的知识。

        Args:
            uid: ingest_unverified 行的 id。
            complete_fn: LLM complete 函数(与 ingest_chapter 同签名 prompt→str)。
                传入时重放该章 ingest——此前因角色不存在而跳过的 learned/did 边现在得以写入。
                不传(None)时跳过 replay(角色仍建立,replayed=False)。

        Returns:
            {created: bool, oid: str, replayed: bool}
            replay 失败时 fail-soft:角色建立 + status=accepted 保留,replayed=False。
        """
        rows = self._query(
            "SELECT name, seq FROM type::record('ingest_unverified', $u)", {"u": uid})
        if not rows:
            return {"created": False, "oid": "", "replayed": False}
        name = rows[0]["name"]
        seq = rows[0].get("seq")
        oid = f"role:{name}"
        created = self.entity(oid) is None
        if created:
            from scribe3.ontology import Entity
            self.add_entity(Entity(oid, "character", name))
        self._execute_write(
            "UPDATE type::record('ingest_unverified', $u) SET status='accepted'", {"u": uid})

        # 重放该章 ingest:现在角色已存在,_resolve_char 不再跳过,被阻塞的知识边得以回填
        replayed = False
        if complete_fn is not None and seq is not None:
            import logging
            try:
                from scribe3.ingest import ingest_chapter
                r = ingest_chapter(self, seq, complete_fn)
                replayed = not r.get("parse_failed", False)
            except Exception as e:
                logging.getLogger("scribe3.store").warning(
                    "accept_unverified uid=%s seq=%s replay 失败(soft): %s", uid, seq, e)

        return {"created": created, "oid": oid, "replayed": replayed}

    def ignore_unverified(self, uid: str) -> None:
        """将待确认行标记为 ignored。"""
        self._execute_write(
            "UPDATE type::record('ingest_unverified', $u) SET status='ignored'", {"u": uid})

    # --- 读 ---
    def entity(self, oid: str) -> Entity | None:
        try:
            table, local = _split(oid)        # 迁移数据的 entity 串可能无标准前缀→容忍
        except (KeyError, ValueError):
            return None
        rows = self._query("SELECT name FROM type::record($tbl,$local)",
                           {"tbl": table, "local": local})
        if not rows:
            return None
        return Entity(oid, TBL2KIND.get(table, table), rows[0].get("name", ""))

    def fact(self, oid: str) -> Fact | None:
        _, local = _split(oid)
        rows = self._query(
            "SELECT entity_id, attribute, value, valid_from, valid_to, secret, leak_markers "
            "FROM type::record('proposition',$local)", {"local": local})
        if not rows:
            return None
        r = rows[0]
        eid = r.get("entity_id") or ""
        return Fact(oid, eid, r["attribute"], r["value"], r["valid_from"],
                    r.get("valid_to"), r.get("secret", False), r.get("leak_markers", []))

    def facts_at(self, chapter: int) -> list[Fact]:
        rows = self._query(
            "SELECT meta::id(id) AS local, entity_id, attribute, value, "
            "valid_from, valid_to, secret, leak_markers, injection_mode, priority FROM proposition "
            "WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch) "
            "AND (archived = NONE OR archived != true)", {"ch": chapter})
        return [Fact(f"fact:{r['local']}", r.get("entity_id") or "",
                     r["attribute"], r["value"],
                     r["valid_from"], r.get("valid_to"), r.get("secret", False),
                     r.get("leak_markers", []),
                     injection_mode=r.get("injection_mode"), priority=r.get("priority"))
                for r in rows]

    def characters(self) -> list[Entity]:
        rows = self._query(
            "SELECT meta::id(id) AS local, name, backstory, backstory_secret, aliases, personality_tags, "
            "importance, appearance, personality_detail, abilities, weaknesses, "
            "first_appearance, surface_goal, deep_need, internal_conflict, fear FROM character "
            "WHERE archived = NONE OR archived != true")
        return [Entity(f"role:{r['local']}", "character", r["name"],
                       traits={"backstory": r.get("backstory"),
                               "backstory_secret": r.get("backstory_secret", False),
                               "aliases": r.get("aliases") or [],
                               "personality_tags": r.get("personality_tags") or [],
                               "importance": r.get("importance"),
                               "appearance": r.get("appearance"),
                               "personality_detail": r.get("personality_detail"),
                               "abilities": r.get("abilities"),
                               "weaknesses": r.get("weaknesses") or [],
                               "first_appearance": r.get("first_appearance"),
                               "surface_goal": r.get("surface_goal"),
                               "deep_need": r.get("deep_need"),
                               "internal_conflict": r.get("internal_conflict"),
                               "fear": r.get("fear")}) for r in rows]

    def all_entities(self) -> list[Entity]:
        """角色 + 地点(前端结构面/实体清单用)。"""
        prows = self._query("SELECT meta::id(id) AS local, name FROM place")
        return self.characters() + [Entity(f"place:{r['local']}", "place", r["name"]) for r in prows]

    # --- 语义 RAG ---
    def semantic_index(self, oid: str, text: str) -> None:
        """给某命题写入 embedding(语义召回用;经 execute_write 单点)。"""
        from scribe3.embed import embed
        _, local = _split(oid)
        self._execute_write("UPDATE type::record('proposition',$local) SET embedding=$v",
                            {"local": local, "v": embed([text])[0]})

    def semantic_recall(self, query: str, k: int = 5) -> list[Fact]:
        """语义召回最相关命题(HNSW <|K,EF|>,按距离升序)。
        D-022:<|K,COSINE|> 显式距离形式经 EXPLAIN 实锤为 KnnTopK+TableScan 暴力扫描,
        <|K,EF数字|> 才走 HNSW 索引(KnnScan);EF=max(40,K) 召回富余,14 组对拍一致。"""
        from scribe3.embed import embed
        qv = embed([query])[0]
        rows = self._query(
            f"SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, "
            f"secret, leak_markers, vector::distance::knn() AS dist "
            f"FROM proposition WHERE embedding <|{int(k)},{max(40, int(k))}|> $qv "
            f"AND (archived = NONE OR archived != true) ORDER BY dist",
            {"qv": qv})
        return [Fact(f"fact:{r['local']}", r.get("entity_id") or "",
                     r["attribute"], r["value"], r["valid_from"],
                     r.get("valid_to"), r.get("secret", False), r.get("leak_markers", [])) for r in rows]

    def hybrid_recall(self, query: str, chapter: int, k: int = 5) -> list[Fact]:
        """混合召回:向量路 + 关键词路 → RRF 融合排名(未来加图遍历路)。
        限知时间门(chapter)过滤未来事实。"""
        vector_results = self.semantic_recall(query, k=min(k * 3, 20))
        keyword_results = _keyword_search_propositions(self, query, chapter, top_k=k * 2)

        vec_ids = [f.id for f in vector_results]
        kw_ids = [f.id for f in keyword_results]

        fused = _reciprocal_rank_fusion(vec_ids, kw_ids, k=60)
        top_ids = [item_id for item_id, _ in fused[:k]]

        all_facts = {f.id: f for f in vector_results + keyword_results}
        return [all_facts[fid] for fid in top_ids if fid in all_facts]

    def chapter_recall(self, query: str, k: int = 5) -> list[dict]:
        """章节语义召回:按标题+正文首段向量匹配相似章。"""
        from scribe3.embed import embed
        qv = embed([query])[0]
        rows = self._query(
            f"SELECT seq, title, vector::distance::knn() AS dist "
            f"FROM chapter WHERE embedding <|{int(k)},{max(40, int(k))}|> $qv ORDER BY dist",
            {"qv": qv})   # D-022:EF 形式走 HNSW,显式 COSINE 是暴力扫描
        return [{"seq": r["seq"], "title": r.get("title", ""), "distance": r["dist"]} for r in rows]

    def graph_recall(self, query: str, chapter: int, k: int = 5) -> list[dict]:
        """Graph RAG:向量召回种子命题 + 沿图边拼知识子图(B枢纽)。
        返回每条种子事实 + {主体, 知情角色, 来源事件, 同场角色}。
        限知时间门(chapter)过滤未来事实。"""
        from scribe3.embed import embed
        qv = embed([query])[0]
        rows = self._query(
            # entity_link:疑似死(P2-15)——migration 026 定义字段+索引但"数据迁移后切换"从未落地,
            #   全仓无写入方,此处 entity_link.name 恒 null,subject 回退 entity_id(下方 or 兜底)。
            #   保留待确认(移除牵动 live 召回查询+idx_prop_entity_link 索引)。
            f"SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, secret, "
            f"  entity_link.name AS subject, "
            f"  <-knows<-character.name AS knowers, "
            f"  <-causes<-event.event_type AS source_events, "
            f"  <-causes<-event->involves->character.name AS co_present, "
            f"  vector::distance::knn() AS dist "
            f"FROM proposition WHERE embedding <|{int(k)},{max(40, int(k))}|> $qv "
            f"  AND valid_from <= $ch AND (archived = NONE OR archived != true) "
            f"ORDER BY dist", {"qv": qv, "ch": chapter})
        out = []
        for r in rows:
            out.append({
                "id": f"fact:{r['local']}",
                "value": r["value"],
                "attribute": r.get("attribute", ""),
                "valid_from": r.get("valid_from", 0),
                "secret": bool(r.get("secret", False)),
                "subject": r.get("subject") or r.get("entity_id") or "",
                "knowers": r.get("knowers") or [],
                "source_events": r.get("source_events") or [],
                "co_present": r.get("co_present") or [],
                "distance": r.get("dist", 0),
            })
        return out

    # --- 母题 motif ---
    def add_motif(self, name: str, theme: str = "", echoes: str = "", unfolding: str = "") -> None:
        self._execute_write(
            "CREATE motif SET name=$n, theme=$t, echoes=$e, unfolding=$u",
            {"n": name, "t": theme, "e": echoes, "u": unfolding})

    def list_motifs(self) -> list[dict]:
        return self._query("SELECT meta::id(id) AS id, name, theme, echoes, unfolding FROM motif")

    def add_motif_instance(self, motif_id: str, chapter: int,
                           evidence: str = "", ingest_seq: int | None = None) -> None:
        self._execute_write(
            "CREATE motif_instance SET motif_id=$m, chapter=$c, evidence=$e, ingest_seq=$i",
            {"m": motif_id, "c": chapter, "e": evidence,
             "i": ingest_seq if ingest_seq is not None else chapter})

    def list_motif_instances(self, chapter: int) -> list[dict]:
        """本章触及的母题:[{motif_id, name, evidence}](name 由 motif 表 join)。"""
        rows = self._query(
            "SELECT motif_id, evidence FROM motif_instance WHERE chapter = $c",
            {"c": chapter})
        names = {m.get("id"): (m.get("name") or "") for m in self.list_motifs()}
        return [{"motif_id": r.get("motif_id"),
                 "name": names.get(r.get("motif_id"), ""),
                 "evidence": r.get("evidence") or ""} for r in rows]

    # --- 主编对话留痕 chat_message(北极星任务1,蓝图 §4-② 沉淀环第1级)---
    def add_chat_message(self, chapter: int, stage: str, role: str, text: str,
                         turn: str = "", trace: dict | None = None, *,
                         thread_id: str | None = None,
                         context_session_id: str | None = None,
                         context_revision: int | None = None,
                         context_hash: str | None = None,
                         focus: dict | None = None,
                         response_id: str | None = None) -> None:
        """追加一条对话留痕;work 用本库名自动填(D-002),ts 由 DB 侧 time::now()。
        turn(P0门审查 P2-6):同一轮 user/assistant 共享的配对 id,防并发会话交错
        污染蒸馏原料(任务8);空串=未知轮(兼容旧行/直写调用方)。

        Task 6:新增关键字参数(全默认 None,向后兼容——旧调用方一字不改仍生效):
        thread_id 挂主编线程(一 work 一连续线程);context_* 是本轮的上下文绑定
        游标(revision/hash/session);focus 是本轮的焦点标签(切焦点不切线程);
        response_id 是本轮 LLM 响应 id。None 一律落 NONE(option 字段,存量行不受影响)。"""
        self._execute_write(
            "CREATE chat_message SET work=$w, chapter=$c, stage=$s, role=$r, text=$t, "
            "turn=$turn, trace=$trace, thread_id=$thread_id, "
            "context_session_id=$ctx_sid, context_revision=$ctx_rev, "
            "context_hash=$ctx_hash, focus=$focus, response_id=$resp_id, "
            "ts=time::now() RETURN NONE",
            {"w": self.db_name, "c": chapter, "s": stage or "", "r": role, "t": text,
             "turn": turn or "", "trace": trace or {}, "thread_id": thread_id,
             "ctx_sid": context_session_id, "ctx_rev": context_revision,
             "ctx_hash": context_hash, "focus": focus, "resp_id": response_id})

    # 线程消息统一取数列(含 Task 6 绑定字段 + meta::id 供前端 keying)。
    _CHAT_MESSAGE_FIELDS = (
        "meta::id(id) AS id, work, chapter, stage, role, text, turn, trace, "
        "thread_id, context_session_id, context_revision, context_hash, focus, "
        "response_id, <string> ts AS ts")

    def list_chat_messages(self, chapter: int | None = None, limit: int = 500) -> list[dict]:
        """按章(缺省全部)拉取对话留痕,ts 升序返回;limit 取**最新** N 条再反转
        (P0门审查 P2-6:此前 ASC LIMIT 取最老 N 条,超量后回看永远读不到新对话);
        limit 夹取 [1,2000] 防 SurrealQL 非法值 500。"""
        n = max(1, min(int(limit), 2000))
        where = "WHERE chapter = $c " if chapter is not None else ""
        rows = self._query(
            f"SELECT {self._CHAT_MESSAGE_FIELDS} "
            f"FROM chat_message {where}ORDER BY ts DESC LIMIT {n}",
            {"c": chapter})
        return list(reversed(rows))

    # == 主编线程(Task 6:一 work 一连续主编线程 + 每轮焦点标签)==
    # 为什么在此:线程是 chat_message 的归属维度,取数/回填都围绕 chat_message。
    # 隔离靠 per-work db(与 chat_message 一致):thread_id 全局唯一,别的 work 读不到。

    _EDITORIAL_THREAD_FIELDS = (
        "thread_id, work, actor_id, parent_thread_id, title, status, "
        "hermes_conversation_id, previous_response_id, summary, "
        "<string> created_at AS created_at, <string> updated_at AS updated_at")

    def _get_editorial_thread(self, thread_id: str) -> dict | None:
        rows = self._query(
            f"SELECT {self._EDITORIAL_THREAD_FIELDS} FROM editorial_thread "
            "WHERE thread_id=$tid LIMIT 1", {"tid": thread_id})
        return rows[0] if rows else None

    def get_or_create_editorial_thread(self, work: str, actor_id: str) -> dict:
        """取或建本 work + actor 的活跃主编线程(一 work 一连续线程,幂等)。

        已有 active 线程(最早创建者,稳定不漂)直接返回;无则建默认线程。
        thread_id 全局唯一(ethread:<work>:<uuid>),隔离仍靠 per-work db。

        actor_id 语义:线程按 (work, actor_id) 定活跃线程——当前单作者场景恒传
        "author"(见调用方 backfill/create_context_session),即"一 work 一 author 线程"。
        将来多 actor(协作/多设备各自成线)时,不同 actor_id 各得一条活跃线程,
        本方法无需改动;届时需上层决定 snapshot 该绑哪个 actor 的线程。"""
        from uuid import uuid4
        rows = self._query(
            f"SELECT {self._EDITORIAL_THREAD_FIELDS} FROM editorial_thread "
            "WHERE work=$w AND actor_id=$a AND status='active' "
            "ORDER BY created_at ASC LIMIT 1", {"w": work, "a": actor_id})
        if rows:
            return rows[0]
        tid = f"ethread:{work}:{uuid4().hex}"
        self._execute_write(
            "CREATE editorial_thread SET thread_id=$tid, work=$w, actor_id=$a, "
            "parent_thread_id=NONE, title=$title, status='active', "
            "hermes_conversation_id=NONE, previous_response_id=NONE, summary='', "
            "updated_at=time::now() RETURN NONE",
            {"tid": tid, "w": work, "a": actor_id, "title": "主编讨论"})
        return self._get_editorial_thread(tid)

    def list_editorial_threads(self, work: str) -> list[dict]:
        """列本 work 的全部主编线程(含分支),按创建时间升序。"""
        return self._query(
            f"SELECT {self._EDITORIAL_THREAD_FIELDS} FROM editorial_thread "
            "WHERE work=$w ORDER BY created_at ASC", {"w": work})

    def list_thread_messages(self, thread_id: str, limit: int = 500) -> list[dict]:
        """按线程拉取对话留痕,ts 升序返回;limit 取最新 N 条再反转(同 list_chat_messages)。
        隔离:只读本 store 的 db,别的 work 的 thread_id 在此库无消息 → 返回 []。"""
        n = max(1, min(int(limit), 2000))
        rows = self._query(
            f"SELECT {self._CHAT_MESSAGE_FIELDS} FROM chat_message "
            f"WHERE thread_id=$tid ORDER BY ts DESC LIMIT {n}", {"tid": thread_id})
        return list(reversed(rows))

    def fork_editorial_thread(self, parent_thread_id: str,
                              title: str | None = None) -> dict:
        """显式分支:以 parent_thread_id 为父建新活跃线程(导航路径绝不调此)。
        actor_id/work 继承父线程;title 缺省沿用父标题。

        子线程消息从空开始——不继承父线程历史(fork 只写 parent_thread_id 建血缘,
        list_thread_messages(child) 初始为空;需要父上下文由上层显式携带)。"""
        from uuid import uuid4
        parent = self._get_editorial_thread(parent_thread_id)
        if parent is None:
            raise ValueError(f"fork_editorial_thread: 父线程 '{parent_thread_id}' 不存在")
        tid = f"ethread:{parent['work']}:{uuid4().hex}"
        self._execute_write(
            "CREATE editorial_thread SET thread_id=$tid, work=$w, actor_id=$a, "
            "parent_thread_id=$parent, title=$title, status='active', "
            "hermes_conversation_id=NONE, previous_response_id=NONE, summary='', "
            "updated_at=time::now() RETURN NONE",
            {"tid": tid, "w": parent["work"], "a": parent["actor_id"],
             "parent": parent_thread_id,
             "title": title or parent.get("title") or "主编讨论"})
        return self._get_editorial_thread(tid)

    def backfill_thread_ids(self, actor_id: str = "author") -> int:
        """把 thread_id 为 NONE 的存量 chat_message 全部归入本 work 默认线程(幂等)。

        升级后旧对话不得从 UI 消失(纸命现网已有真实 chat_message,无 thread_id)。
        默认线程取 get_or_create_editorial_thread(db_name, actor_id="author")——与
        create_context_session 同一 ethread id,前端 snapshot.thread_id 读得到这些旧消息。
        context_revision/focus 留 NONE(存量无从追溯);再跑无变化(NONE 已被清光);
        回填前后 chat_message 总数不变(只 UPDATE 不增删)。返回本次更新条数。

        后续任务事项:pilot/loop 等写入点当前不带 thread_id,会持续产生 thread_id=NONE
        的孤儿消息——backfill 只在启动时兜底归档一次,长期应让所有 add_chat_message
        调用点显式带 thread_id(消除孤儿源头),而非依赖回填清扫。"""
        thread = self.get_or_create_editorial_thread(self.db_name, actor_id)
        tid = thread["thread_id"]
        # 只更新 thread_id 尚未设置(NONE)的行——已归属者不动 → 幂等。
        rows = self._query(
            "SELECT count() AS n FROM chat_message WHERE thread_id IS NONE GROUP ALL")
        n = int(rows[0]["n"]) if rows and rows[0].get("n") is not None else 0
        if n:
            self._execute_write(
                "UPDATE chat_message SET thread_id=$tid "
                "WHERE thread_id IS NONE RETURN NONE", {"tid": tid})
        return n

    # --- Hermes Runs/Approval 审计链 ---
    def upsert_ai_run_trace(self, run_id: str, *, status: str | None = None,
                            session_key: str | None = None,
                            input_text: str | None = None,
                            instructions: str | None = None,
                            tool_calls: list[dict] | None = None,
                            tool_outputs: list[dict] | None = None,
                            approvals: list[dict] | None = None,
                            raw_events: list[dict] | None = None,
                            usage: dict | None = None,
                            error=None,
                            response: dict | None = None) -> None:
        existing = self.get_ai_run_trace(run_id) or {}
        payload = {
            "work": self.db_name,
            "run_id": run_id,
            "status": status or existing.get("status") or "created",
            "session_key": session_key if session_key is not None else existing.get("session_key"),
            "input_text": input_text if input_text is not None else existing.get("input_text"),
            "instructions": instructions if instructions is not None else existing.get("instructions"),
            "tool_calls": tool_calls if tool_calls is not None else (existing.get("tool_calls") or []),
            "tool_outputs": tool_outputs if tool_outputs is not None else (existing.get("tool_outputs") or []),
            "approvals": approvals if approvals is not None else (existing.get("approvals") or []),
            "raw_events": raw_events if raw_events is not None else (existing.get("raw_events") or []),
            "usage": usage if usage is not None else existing.get("usage"),
            "error": error if error is not None else existing.get("error"),
            "response": response if response is not None else existing.get("response"),
        }
        self._execute_write(
            "UPSERT type::record('ai_run_trace', $run) SET work=$work, run_id=$run_id, "
            "status=$status, session_key=$session_key, input_text=$input_text, "
            "instructions=$instructions, tool_calls=$tool_calls, tool_outputs=$tool_outputs, "
            "approvals=$approvals, raw_events=$raw_events, usage=$usage, error=$error, "
            "response=$response, updated_at=time::now() RETURN NONE",
            {"run": run_id, **payload},
        )

    def append_ai_run_trace_event(self, run_id: str, event: dict) -> None:
        trace = self.get_ai_run_trace(run_id) or {}
        tool_calls = list(trace.get("tool_calls") or [])
        tool_outputs = list(trace.get("tool_outputs") or [])
        approvals = list(trace.get("approvals") or [])
        raw_events = list(trace.get("raw_events") or [])
        status = trace.get("status") or "created"
        usage = trace.get("usage")
        error = trace.get("error")

        def _find_call(call_id: str | None = None) -> dict | None:
            if call_id:
                for call in reversed(tool_calls):
                    if call.get("call_id") == call_id:
                        return call
            completed = {out.get("call_id") for out in tool_outputs if out.get("call_id")}
            for call in reversed(tool_calls):
                if call.get("call_id") not in completed:
                    return call
            return tool_calls[-1] if tool_calls else None

        def _find_approval(approval_id: str | None = None,
                           call_id: str | None = None,
                           approval_status: str | None = None) -> dict | None:
            for approval in reversed(approvals):
                if approval_id and approval.get("approval_id") != approval_id:
                    continue
                if call_id and approval.get("call_id") != call_id:
                    continue
                if approval_status and approval.get("status") != approval_status:
                    continue
                return approval
            return None

        kind = event.get("kind") or event.get("type") or ""
        source_type = event.get("source_type") or event.get("type") or kind
        if kind in {"tool.started", "tool.start"}:
            parsed_args = _json_obj(event.get("arguments"))
            tool_calls.append({
                "call_id": event.get("call_id"),
                "name": event.get("name") or event.get("tool_name") or "",
                "arguments": event.get("arguments", ""),
                "parsed_arguments": parsed_args,
                "approval_id": event.get("approval_id"),
                "source_type": source_type,
            })
        elif kind in {"tool.output", "tool.complete"}:
            call_id = event.get("call_id")
            call = _find_call(call_id)
            parsed_output = _json_obj(event.get("output"))
            tool = (
                event.get("name") or event.get("tool_name")
                or (parsed_output or {}).get("tool")
                or (call or {}).get("name")
                or ""
            )
            approval_id = event.get("approval_id") or (call or {}).get("approval_id")
            approval = (
                _find_approval(approval_id=approval_id, approval_status="resolved")
                or _find_approval(approval_id=approval_id)
                or _find_approval(call_id=call_id, approval_status="resolved")
                or _find_approval(call_id=call_id)
            )
            decision = event.get("decision") or (approval or {}).get("decision")
            if approval and not approval_id:
                approval_id = approval.get("approval_id")
            result_status = (parsed_output or {}).get("status") or event.get("status")
            parsed_args = (call or {}).get("parsed_arguments") or _json_obj((call or {}).get("arguments"))
            write_effect = (
                _write_effect_from_tool(tool, parsed_args)
                or (call or {}).get("write_effect")
                or (approval or {}).get("write_effect")
            )
            if not result_status and tool.startswith("s3_"):
                if decision in {"approve", "approved", "once", "session", "always", True}:
                    result_status = "written"
                elif decision in {"deny", "denied", "reject", "rejected", False}:
                    result_status = "declined"
            if call is not None:
                if approval_id:
                    call["approval_id"] = approval_id
                if result_status:
                    call["result_status"] = result_status
                if write_effect:
                    call["write_effect"] = write_effect
            tool_outputs.append({
                "call_id": call_id,
                "tool": tool,
                "output": event.get("output", ""),
                "parsed_output": parsed_output,
                "approval_id": approval_id,
                "decision": decision,
                "result_status": result_status,
                "write_effect": write_effect,
                "source_type": source_type,
            })
        elif kind in {"approval.requested", "approval.request"}:
            call_id = event.get("call_id") or event.get("tool_call_id")
            call = _find_call(call_id)
            if call and not call_id:
                call_id = call.get("call_id")
            tool = event.get("name") or event.get("tool_name") or (call or {}).get("name") or ""
            approval_id = event.get("approval_id")
            write_effect = _write_effect_from_approval_message(event.get("message", ""))
            if call and approval_id:
                call["approval_id"] = approval_id
            if call and write_effect:
                call["write_effect"] = write_effect
            approvals.append({
                "run_id": event.get("run_id") or run_id,
                "approval_id": approval_id,
                "call_id": call_id,
                "tool": tool,
                "message": event.get("message", ""),
                "write_effect": write_effect,
                "status": "requested",
                "source": event.get("source") or "runtime",
                "source_type": source_type,
            })
        elif kind == "approval.resolved":
            approval_id = event.get("approval_id")
            requested = _find_approval(approval_id=approval_id, approval_status="requested")
            call_id = event.get("call_id") or event.get("tool_call_id") or (requested or {}).get("call_id")
            call = _find_call(call_id)
            if call and not call_id:
                call_id = call.get("call_id")
            tool = event.get("name") or event.get("tool_name") or (requested or {}).get("tool") or (call or {}).get("name") or ""
            if call and approval_id:
                call["approval_id"] = approval_id
            write_effect = (requested or {}).get("write_effect") or (call or {}).get("write_effect")
            approvals.append({
                "run_id": event.get("run_id") or run_id,
                "approval_id": approval_id,
                "call_id": call_id,
                "tool": tool,
                "decision": event.get("decision"),
                "write_effect": write_effect,
                "status": "resolved",
                "source": event.get("source") or "runtime",
                "source_type": source_type,
            })
        elif kind == "run.completed":
            status = "completed"
            usage = event.get("usage")
        elif kind == "run.failed":
            status = "failed"
            error = event.get("error") or "run failed"
        else:
            raw_events.append(event)

        self.upsert_ai_run_trace(
            run_id,
            status=status,
            tool_calls=tool_calls,
            tool_outputs=tool_outputs,
            approvals=approvals,
            raw_events=raw_events,
            usage=usage,
            error=error,
        )

    def get_ai_run_trace(self, run_id: str) -> dict | None:
        rows = self._query(
            "SELECT work, run_id, status, session_key, input_text, instructions, "
            "tool_calls, tool_outputs, approvals, raw_events, usage, error, response, "
            "<string> created_at AS created_at, <string> updated_at AS updated_at "
            "FROM type::record('ai_run_trace', $run)",
            {"run": run_id},
        )
        return rows[0] if rows else None

    def list_ai_run_traces(self, limit: int = 100) -> list[dict]:
        n = max(1, min(int(limit), 1000))
        rows = self._query(
            f"SELECT work, run_id, status, session_key, input_text, tool_calls, "
            f"tool_outputs, approvals, usage, error, <string> updated_at AS updated_at "
            f"FROM ai_run_trace ORDER BY updated_at DESC LIMIT {n}",
        )
        return rows

    def usage_summary(self, days: int = 7) -> dict:
        """H-10:近 N 天 LLM token 真实用量聚合(/ai/usage 数据源)。

        数据源是两条审计链已存的 Hermes usage:chat_message.trace.usage(Responses
        写作/讨论)+ ai_run_trace.usage(Runs 写入型任务)。行数有限(留痕表按章),
        取回后在 Python 侧按天聚合——SurrealQL 嵌套字段 group-by 不值得为此冒方言坑。
        天按 ts 前 10 位(UTC 日界),与日帽台账的本地日界可能差几小时,预算展示可容忍。
        """
        n = max(1, min(int(days), 90))
        import datetime as _dt
        cutoff = (_dt.date.today() - _dt.timedelta(days=n - 1)).isoformat()
        zero = lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}  # noqa: E731
        acc: dict[str, dict] = {}

        def _add(day: str, channel: str, u) -> None:
            if not isinstance(u, dict) or not day or day < cutoff:
                return
            d = acc.setdefault(day, {"responses": zero(), "runs": zero()})
            slot = d[channel]
            slot["calls"] += 1
            slot["input_tokens"] += int(u.get("input_tokens") or u.get("prompt_tokens") or 0)
            slot["output_tokens"] += int(u.get("output_tokens") or u.get("completion_tokens") or 0)
            slot["total_tokens"] += int(u.get("total_tokens") or 0)

        for r in self._query(
                "SELECT <string> ts AS ts, trace.usage AS usage FROM chat_message "
                "WHERE trace.usage != NONE ORDER BY ts DESC LIMIT 5000"):
            _add((r.get("ts") or "")[:10], "responses", r.get("usage"))
        for r in self._query(
                "SELECT <string> updated_at AS ts, usage FROM ai_run_trace "
                "WHERE usage != NONE ORDER BY ts DESC LIMIT 2000"):
            _add((r.get("ts") or "")[:10], "runs", r.get("usage"))

        days_out = []
        for day in sorted(acc, reverse=True):
            d = acc[day]
            total = zero()
            for ch in ("responses", "runs"):
                for k in total:
                    total[k] += d[ch][k]
            days_out.append({"day": day, **d, "total": total})
        return {"days": days_out, "since": cutoff}

    # --- 蒸馏幂等标记(P1门审查 P1-1)---
    def get_distill_marker(self, chapter: int) -> dict | None:
        rows = self._query(
            "SELECT chapter, msg_count, last_turn FROM type::record('distill_marker',$c)",
            {"c": chapter})
        return rows[0] if rows else None

    def set_distill_marker(self, chapter: int, msg_count: int, last_turn: str) -> None:
        self._execute_write(
            "UPSERT type::record('distill_marker',$c) SET chapter=$c, msg_count=$n, "
            "last_turn=$t, ts=time::now()",
            {"c": chapter, "n": msg_count, "t": last_turn or ""})

    # --- QD 文体档案 style_profile(北极星任务9)---
    def _upsert_style_profile(self, seq: int, profile: dict) -> None:
        import json
        self._execute_write(
            "UPSERT type::record('style_profile',$s) SET seq=$s, profile=$p, "
            "computed_at=time::now()",
            {"s": seq, "p": json.dumps(profile, ensure_ascii=False)})

    def list_style_profiles(self) -> list[dict]:
        import json
        rows = self._query(
            "SELECT seq, profile FROM style_profile ORDER BY seq ASC")
        out = []
        for r in rows:
            try:
                p = json.loads(r.get("profile") or "{}")
            except Exception:
                p = {}
            out.append({"seq": r.get("seq"), **p})
        return out

    # --- 复盘 lesson(北极星任务8,蓝图 §4-② 沉淀环;与情绪模式向量分表分索引 Q4)---
    def add_lesson(self, chapter: int, kind: str, text: str, condition: str = "",
                   evidence_turns: list | None = None) -> bool:
        """落一条 lesson(带软去重):先在 lesson 专属 HNSW 索引召回近邻,
        余弦相似 ≥ MERGE_SIM 的既有条目 → importance+1 合并不新增(返回 False);
        否则新增(返回 True)。embedding=text+condition(条件参与语义)。"""
        from scribe3.embed import embed
        from scribe3.lesson import MERGE_SIM
        import json as _json
        vec = embed([f"{text} {condition}".strip()])[0]
        near = self._query(
            "SELECT meta::id(id) AS id, chapter, kind, embedding, "
            "vector::distance::knn() AS dist "
            "FROM lesson WHERE embedding <|3,40|> $qv ORDER BY dist", {"qv": vec})
        for n in near:
            # P1门审查 P1-3:合并须同 kind 且 sim≥MERGE_SIM(0.97 收紧)——embedding 对
            # 否定不敏感,反向纠偏("反转别再压章尾")与旧课 0.92 档极易误合并,
            # "correction 最值钱"恰是被吞的那类;0.92-0.97 灰区直接新增,重复由
            # importance 机制无害共存。
            if n.get("kind") != kind:
                continue
            if n.get("dist") is not None and (1 - n["dist"]) >= MERGE_SIM:
                row = self._query(
                    "SELECT invalid_at FROM type::record('lesson',$i)", {"i": n["id"]})
                if row and row[0].get("invalid_at"):
                    continue   # 已失效条目不合并(允许同课重立)
                # P1门审查 P1-1:同章重跑不 bump——ExpeL"跨章重复=偏好积累"语义,
                # 同章编辑期反复蒸馏不算重复偏好。
                if n.get("chapter") != chapter:
                    self._execute_write(
                        "UPDATE type::record('lesson',$i) SET importance += 1",
                        {"i": n["id"]})
                return False
        self._execute_write(
            "CREATE lesson SET chapter=$c, kind=$k, text=$t, condition=$cond, "
            "evidence_turns=$ev, importance=2, uses=0, created_at=time::now(), embedding=$v",
            {"c": chapter, "k": kind, "t": text, "cond": condition or "",
             "ev": _json.dumps(evidence_turns or [], ensure_ascii=False), "v": vec})
        return True

    def list_lessons(self, chapter: int | None = None,
                     include_invalid: bool = False) -> list[dict]:
        where = []
        if chapter is not None:
            where.append("chapter = $c")
        if not include_invalid:
            where.append("invalid_at IS NONE")
        w = ("WHERE " + " AND ".join(where) + " ") if where else ""
        rows = self._query(
            f"SELECT meta::id(id) AS id, chapter, kind, text, condition, importance, uses, "
            f"evidence_turns, invalid_at, <string> created_at AS created_at "
            f"FROM lesson {w}ORDER BY created_at ASC",
            {"c": chapter})
        import json as _json
        for r in rows:   # P1门审查 P2-8:证据指针读侧还原(此前只写不读,溯源链断)
            try:
                r["evidence_turns"] = _json.loads(r.get("evidence_turns") or "[]")
            except Exception:
                r["evidence_turns"] = []
        return rows

    def recall_lessons(self, query: str, k: int = 3, min_sim: float | None = None) -> list[dict]:
        """HNSW 语义召回 lesson,相似度下限过滤(宁缺勿滥:相关但不适用比无关更毒),
        命中即 uses+1(质量闭环);invalid 条目 Python 侧过滤(避开 KNN×WHERE 组合坑,Q4)。"""
        if not (query or "").strip():
            return []
        from scribe3.embed import embed
        if min_sim is None:
            from scribe3.lesson import RECALL_MIN_SIM as min_sim   # 真机标定值(D-017)
        qv = embed([query])[0]
        rows = self._query(
            f"SELECT meta::id(id) AS id, chapter, kind, text, condition, importance, uses, "
            f"invalid_at, vector::distance::knn() AS dist "
            f"FROM lesson WHERE embedding <|{int(max(k * 3, 6))},{max(40, int(k * 3))}|> $qv "
            f"ORDER BY dist", {"qv": qv})
        out: list[dict] = []
        for r in rows:
            if r.get("invalid_at"):
                continue
            sim = 1 - r["dist"] if r.get("dist") is not None else 0.0
            if sim < min_sim:
                continue
            r["sim"] = round(sim, 4)
            r.pop("dist", None)
            r.pop("invalid_at", None)
            out.append(r)
            if len(out) >= k:
                break
        for r in out:
            self._execute_write("UPDATE type::record('lesson',$i) SET uses += 1",
                                {"i": r["id"]})
        return out

    def bump_lesson_importance(self, lesson_id: str, delta: int = 1) -> None:
        self._execute_write(
            "UPDATE type::record('lesson',$i) SET importance += $d",
            {"i": lesson_id, "d": delta})

    def invalidate_lesson(self, lesson_id: str) -> None:
        """失效标记不物理删(Zep 先例):craft_rule 审批溯源链保留。"""
        self._execute_write(
            "UPDATE type::record('lesson',$i) SET invalid_at = time::now()",
            {"i": lesson_id})

    # --- 伏笔章触及 promise_touch ---
    def add_promise_touch(self, promise_id: str, chapter: int,
                          evidence: str = "", ingest_seq: int | None = None) -> None:
        self._execute_write(
            "CREATE promise_touch SET promise_id=$p, chapter=$c, evidence=$e"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"p": promise_id, "c": chapter, "e": evidence or None,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})

    def list_promise_touches(self, promise_id: str) -> list[dict]:
        return self._query(
            "SELECT promise_id, chapter, evidence FROM promise_touch "
            "WHERE promise_id=$p ORDER BY chapter ASC", {"p": promise_id})

    # --- 关系触碰 relation_touch(方案B任务12:连续性 heat/last_touch 状态机——
    #     角色/支线/伏笔已有 last_active/last_refresh_at,唯独"关系"维度无触碰追踪,补此) ---
    def add_relation_touch(self, a: str, b: str, chapter: int, kind: str, note: str = "") -> None:
        """登记一次关系触碰。a/b 是无序对(登记时不必关心先后)。
        kind 语义由调用方约束(ingest 抽取纪律见 ingest.py),store 层不做枚举校验。"""
        self._execute_write(
            "CREATE relation_touch SET a=$a, b=$b, chapter=$c, kind=$k, note=$n",
            {"a": a, "b": b, "c": chapter, "k": kind, "n": note or None})

    def list_relation_touches(self, a: str | None = None, b: str | None = None) -> list[dict]:
        """列关系触碰记录,按章号升序。a/b 无序对:传单侧或双侧均对称匹配(不论登记时先后)。
        两者都不传则返回全部。"""
        if a is not None and b is not None:
            rows = self._query(
                "SELECT a, b, chapter, kind, note FROM relation_touch "
                "WHERE (a=$a AND b=$b) OR (a=$b AND b=$a) ORDER BY chapter ASC",
                {"a": a, "b": b})
        elif a is not None:
            rows = self._query(
                "SELECT a, b, chapter, kind, note FROM relation_touch "
                "WHERE a=$a OR b=$a ORDER BY chapter ASC", {"a": a})
        elif b is not None:
            rows = self._query(
                "SELECT a, b, chapter, kind, note FROM relation_touch "
                "WHERE a=$b OR b=$b ORDER BY chapter ASC", {"b": b})
        else:
            rows = self._query(
                "SELECT a, b, chapter, kind, note FROM relation_touch ORDER BY chapter ASC")
        return [{"a": r.get("a"), "b": r.get("b"), "chapter": r.get("chapter"),
                 "kind": r.get("kind"), "note": r.get("note") or ""} for r in rows]

    # --- 通用 增删改(设定库编辑用)---
    def _update_by(self, table: str, local: str, fields: dict) -> None:
        if table not in _TABLES:
            raise ValueError(f"unknown table: {table}")
        fields = {k: v for k, v in fields.items() if v is not None}
        if not fields:
            return
        allowed = _FIELDS_BY_TABLE.get(table, set())
        bad = set(fields) - allowed
        if bad:
            raise ValueError(f"disallowed fields for {table}: {bad}")
        sets = ", ".join(f"{k}=${k}" for k in fields)
        self._execute_write(f"UPDATE type::record('{table}',$_l) SET {sets}", {"_l": local, **fields})

    def _delete_by(self, table: str, local: str) -> None:
        self._execute_write(f"DELETE type::record('{table}',$_l)", {"_l": local})

    def update_record(self, oid: str, fields: dict) -> None:
        t, l = _split(oid)
        self._update_by(t, l, fields)

    def exists(self, oid: str) -> bool:
        """只读存在性检查(写前 404 校验用)。"""
        try:
            t, l = _split(oid)
        except (KeyError, ValueError):
            return False
        rows = self._query("SELECT id FROM type::record($tbl,$local) LIMIT 1",
                           {"tbl": t, "local": l})
        return bool(rows)

    def update_event_narrative(self, event_oid: str, narrative_position: int | None) -> None:
        """更新已有事件的叙事位(narrative_position)。
        narrative_position=None → 清除叙事位,回退到 story_chapter(向后兼容线性叙事)。
        event_oid 须为 'ev:xxx' 格式。
        """
        _, local = _split(event_oid)
        self._execute_write(
            "UPDATE type::record('event',$local) SET narrative_position=$np",
            {"local": local, "np": narrative_position})

    def record_lifecycle_impact(self, oid: str) -> dict | None:
        """对象删除影响计数。返回 None 表示对象不存在。"""
        if not self.exists(oid):
            return None
        table, local = _split(oid)
        rid = RecordID(table, local)
        counts: dict[str, int] = {}
        label = oid
        if oid.startswith("role:"):
            ent = self.entity(oid)
            label = ent.name if ent else oid
            counts["proposition"] = len(self._query(
                "SELECT id FROM proposition WHERE entity_id=$oid", {"oid": oid}))
            try:
                counts["knowledge_edge"] = len(self._query(
                    "SELECT id FROM knows WHERE in=$rid", {"rid": rid}))
            except Exception:
                counts["knowledge_edge"] = 0
            try:
                counts["event_involvement"] = len(self._query(
                    "SELECT id FROM involves WHERE out=$rid", {"rid": rid}))
            except Exception:
                counts["event_involvement"] = 0
        elif oid.startswith("fact:"):
            fact = self.fact(oid)
            label = f"{fact.entity_id}·{fact.attribute}" if fact else oid
            try:
                counts["knowledge_edge"] = len(self._query(
                    "SELECT id FROM knows WHERE out=$rid", {"rid": rid}))
            except Exception:
                counts["knowledge_edge"] = 0
            counts["reader_knowledge"] = len(self._query(
                "SELECT id FROM reader_knows WHERE proposition=$rid", {"rid": rid}))
            try:
                counts["event_effect"] = len(self._query(
                    "SELECT id FROM causes WHERE out=$rid", {"rid": rid}))
            except Exception:
                counts["event_effect"] = 0
        return {"object": {"id": oid, "label": label}, "counts": counts}

    def _cleanup_record_refs(self, oid: str) -> None:
        table, local = _split(oid)
        rid = RecordID(table, local)
        if oid.startswith("role:"):
            self._execute_write("DELETE knows WHERE in=$rid", {"rid": rid})
            self._execute_write("DELETE involves WHERE out=$rid", {"rid": rid})
        elif oid.startswith("fact:"):
            self._execute_write("DELETE knows WHERE out=$rid", {"rid": rid})
            self._execute_write("DELETE reader_knows WHERE proposition=$rid", {"rid": rid})
            self._execute_write("DELETE causes WHERE out=$rid", {"rid": rid})

    def delete_record(self, oid: str, cleanup_refs: bool = False) -> bool:
        if not self.exists(oid):
            return False
        if cleanup_refs:
            self._cleanup_record_refs(oid)
        t, l = _split(oid)
        self._delete_by(t, l)
        return True

    def update_promise(self, pid: str, fields: dict) -> bool:
        """更新伏笔字段;返回 True 若存在,False 若不存在。

        setup_chapter 或 tier 变更且调用方未显式给 payoff_min/payoff_max 时,
        按(新)tier 重算兑现窗口,防脏窗口落库(edit_prom 端点自动跟随)。"""
        rows = self._query("SELECT id, tier, setup_chapter FROM type::record('promise',$pid) "
                           "LIMIT 1", {"pid": pid})
        if not rows:
            return False
        fields = dict(fields)
        new_setup = fields.get("setup_chapter")
        new_tier = fields.get("tier")
        # tier 校验在窗口分支之外:非法 tier 即使显式给了窗口也不得落库
        if new_tier is not None and new_tier not in _TIER_WINDOW:
            raise ValueError(f"非法伏笔层级 tier='{new_tier}'(合法: {sorted(_TIER_WINDOW)})")
        window_given = (fields.get("payoff_min") is not None
                        or fields.get("payoff_max") is not None)
        clear_pmax = False
        if (new_setup is not None or new_tier is not None) and not window_given:
            tier = new_tier or rows[0].get("tier") or "chapter"
            if tier not in _TIER_WINDOW:
                raise ValueError(f"非法伏笔层级 tier='{tier}'(合法: {sorted(_TIER_WINDOW)})")
            setup = new_setup if new_setup is not None else rows[0].get("setup_chapter")
            if setup is not None:
                lo, hi = _TIER_WINDOW[tier]
                fields["payoff_min"] = setup + lo
                if hi is None:
                    clear_pmax = True  # _update_by 过滤 None 值,book 层需显式清 payoff_max
                else:
                    fields["payoff_max"] = setup + hi
        self._update_by("promise", pid, fields)
        if clear_pmax:
            self._execute_write(
                "UPDATE type::record('promise',$pid) SET payoff_max=NONE", {"pid": pid})
        return True

    def delete_promise(self, promise_id: str) -> bool:
        """删除伏笔;返回 True 若存在并删除,False 若不存在。"""
        rows = self._query("SELECT id FROM type::record('promise',$pid) LIMIT 1", {"pid": promise_id})
        if not rows:
            return False
        self._delete_by("promise", promise_id)
        return True

    def update_motif(self, motif_id: str, fields: dict) -> None:
        self._update_by("motif", motif_id, fields)

    def delete_motif(self, motif_id: str) -> None:
        self._delete_by("motif", motif_id)

    # --- 素材库 material(非正典写作材料)---
    # 与设定库(codex=正典)严格分开:不进知识图谱、不被 ingest、不参与限知/伏笔/QC/时间线。
    _MATERIAL_COLS = ("meta::id(id) AS id, title, body, kind, tags, source, "
                      "ref_tags, tokens, about_entities, pinned, archived, "
                      "recall_count, last_recalled_at, created_at, updated_at")

    def add_material(self, title: str, body: str | None = None, kind: str = "note",
                     tags: list[str] | None = None, source: str | None = None,
                     ref_tags: list[str] | None = None) -> str:
        """新建素材(记忆化:jieba 切 tokens + 生成 embedding),返回裸 id。"""
        if kind not in MATERIAL_KINDS:
            raise ValueError(f"非法素材分类 kind='{kind}'(合法: {list(MATERIAL_KINDS)})")
        toks, vec = self._material_index_fields(title, body)
        rows = self._query(
            "CREATE material CONTENT $c",
            {"c": {"title": title, "body": body, "kind": kind,
                   "tags": list(tags or []), "source": source,
                   "ref_tags": list(ref_tags or []), "tokens": toks, "embedding": vec}})
        rid = (rows[0] if rows else {}).get("id")
        if rid is None:
            raise RuntimeError("add_material: CREATE 未返回 id")
        return str(rid).split(":")[-1] if ":" in str(rid) else str(rid)

    def list_materials(self, kind: str | None = None, archived: bool | None = False) -> list[dict]:
        """素材列表(可选 kind 过滤),按 updated_at DESC。"""
        filters = []
        vars = {}
        if kind is not None:
            filters.append("kind=$k")
            vars["k"] = kind
        if archived is True:
            filters.append("archived = true")
        elif archived is False:
            filters.append("(archived = NONE OR archived != true)")
        where = f" WHERE {' AND '.join(filters)}" if filters else ""
        return self._query(
            f"SELECT {self._MATERIAL_COLS} FROM material{where} ORDER BY updated_at DESC",
            vars)

    def get_material(self, material_id: str) -> dict | None:
        rows = self._query(
            f"SELECT {self._MATERIAL_COLS} FROM type::record('material',$m) LIMIT 1",
            {"m": material_id})
        return rows[0] if rows else None

    def _material_exists(self, material_id: str) -> bool:
        # 不走 exists()(其 _split 只认 ONT2TBL 本体前缀),直接按表查
        rows = self._query("SELECT id FROM type::record('material',$m) LIMIT 1",
                           {"m": material_id})
        return bool(rows)

    def update_material(self, material_id: str, fields: dict) -> bool:
        """局部更新;title/body 变则重算 tokens+embedding。返回是否存在。"""
        if fields.get("kind") is not None and fields["kind"] not in MATERIAL_KINDS:
            raise ValueError(f"非法素材分类 kind='{fields['kind']}'(合法: {list(MATERIAL_KINDS)})")
        if not self._material_exists(material_id):
            return False
        if "title" in fields or "body" in fields:
            cur = self.get_material(material_id) or {}
            toks, vec = self._material_index_fields(
                fields.get("title", cur.get("title")), fields.get("body", cur.get("body")))
            fields = {**fields, "tokens": toks, "embedding": vec}
        self._update_by("material", material_id, fields)
        return True

    def material_lifecycle_impact(self, material_id: str) -> dict | None:
        row = self.get_material(material_id)
        if not row:
            return None
        counts = {
            "material_reference": len(self.material_refs_by_material(material_id)),
        }
        try:
            rid = RecordID("material", material_id)
            counts["graph"] = len(self._query(
                "SELECT id FROM relates WHERE in=$rid OR out=$rid", {"rid": rid}))
        except Exception:
            counts["graph"] = 0
        if row.get("embedding"):
            counts["semantic_index"] = 1
        if row.get("about_entities"):
            counts["about_entities"] = len(row.get("about_entities") or [])
        return {"object": {"id": material_id, "label": row.get("title") or material_id}, "counts": counts}

    def _cleanup_material_refs(self, material_id: str) -> None:
        rid = RecordID("material", material_id)
        self._execute_write("DELETE material_reference WHERE material_id=$m", {"m": material_id})
        try:
            self._execute_write("DELETE relates WHERE in=$rid OR out=$rid", {"rid": rid})
        except Exception:
            pass

    def delete_material(self, material_id: str, cleanup_refs: bool = False) -> bool:
        """删除素材;返回 True 若存在并删除,False 若不存在。"""
        if not self._material_exists(material_id):
            return False
        if cleanup_refs:
            self._cleanup_material_refs(material_id)
        self._delete_by("material", material_id)
        return True

    # --- 素材记忆:向量/溯源/联想边(Phase1)---
    @staticmethod
    def _material_index_fields(title, body):
        """jieba 切词 + embedding(add/update/backfill 共用,DRY)。"""
        import jieba
        from scribe3.embed import embed
        text = f"{title or ''}\n{body or ''}"
        toks = " ".join(w for w in jieba.cut(text) if w.strip())
        return toks, embed([text])[0]

    def _material_embedding(self, material_id: str):
        rows = self._query(
            "SELECT embedding FROM type::record('material',$m) LIMIT 1", {"m": material_id})
        return (rows[0].get("embedding") if rows else None)

    def add_material_reference(self, material_id, chapter, dimension=None,
                               reason=None, via="manual") -> None:
        """记一次参考(溯源)+ 强化(recall_count++/last_recalled_at)。"""
        self._execute_write(
            "CREATE material_reference SET material_id=$m, chapter=$c, "
            "dimension=$d, reason=$r, via=$v",
            {"m": material_id, "c": int(chapter), "d": dimension, "r": reason, "v": via})
        self._execute_write(
            "UPDATE type::record('material',$m) SET recall_count += 1, "
            "last_recalled_at = time::now()", {"m": material_id})

    def material_refs_by_material(self, material_id) -> list[dict]:
        return self._query(
            "SELECT material_id, chapter, dimension, reason, via FROM material_reference "
            "WHERE material_id=$m ORDER BY chapter", {"m": material_id})

    def material_refs_by_chapter(self, chapter) -> list[dict]:
        return self._query(
            "SELECT material_id, chapter, dimension, reason, via FROM material_reference "
            "WHERE chapter=$c", {"c": int(chapter)})

    def build_material_edges(self, material_id, top_k: int = 5, threshold: float = 0.3) -> None:
        """建联想边:relates(语义近邻 top-k,图 RELATE)+ about_entities(提及实体,数组)。
        threshold=相似度下限(1-距离),低于则不建 relates 边。防爆炸:只保 top-k。"""
        emb = self._material_embedding(material_id)
        if not emb:
            return
        rows = self._query(
            f"SELECT meta::id(id) AS id, vector::distance::knn() AS dist FROM material "
            f"WHERE embedding <|{top_k + 1},{max(40, top_k + 1)}|> $qv "
            f"AND meta::id(id) != $self ORDER BY dist LIMIT {top_k}",
            {"qv": emb, "self": material_id})
        for r in rows:
            sim = 1.0 - float(r.get("dist") or 0.0)
            if sim < threshold:
                continue
            self._execute_write(
                "RELATE (type::record('material',$a))->relates->(type::record('material',$b)) "
                "SET weight=$w, reason=$reason",
                {"a": material_id, "b": r["id"], "w": sim, "reason": "语义近邻"})
        try:  # about_entities:素材提及的实体 id(图召回按实体关联),富集失败不阻塞
            from scribe3.brief import detect_mentions
            ents = [{"id": e.id, "name": e.name,
                     "aliases": (getattr(e, "traits", None) or {}).get("aliases") or []}
                    for e in self.all_entities()]
            row = self.get_material(material_id) or {}
            mentioned = list(detect_mentions(f"{row.get('title', '')} {row.get('body') or ''}", ents))
            if mentioned:
                self._execute_write("UPDATE type::record('material',$m) SET about_entities=$e",
                                    {"m": material_id, "e": mentioned})
        except Exception:
            pass

    def material_relates(self, material_id) -> list[dict]:
        """查素材的 relates 联想邻居(表未建/无边→空,首次召回空库时鲁棒)。"""
        try:
            return self._query(
                "SELECT meta::id(out) AS id, weight, reason FROM relates "
                "WHERE in = type::record('material',$m)", {"m": material_id})
        except Exception:
            return []

    def material_recall(self, query: str, chapter: int | None = None, k: int = 5,
                        mentioned_entities=None) -> list[dict]:
        """素材三通道召回(语义 HNSW + 全文 BM25 + 图 relates/about)→ RRF 融合 → 强度加权。
        archived 排除。返回按强度排序的 top-k 素材行(含 material_id/score)。"""
        import jieba
        from scribe3.embed import embed
        from scribe3.material_recall import apply_strength
        if not (query or "").strip():
            return []
        k3, ef = k * 3, max(40, k * 3)
        # 语义路(HNSW,archived 排除)
        try:
            vec_ids = [r["id"] for r in self._query(
                f"SELECT meta::id(id) AS id, vector::distance::knn() AS dist FROM material "
                f"WHERE embedding <|{k3},{ef}|> $qv AND archived != true ORDER BY dist",
                {"qv": embed([query])[0]})]
        except Exception:
            vec_ids = []
        # 全文路(jieba 切 query → BM25 search::score)
        q_toks = " ".join(w for w in jieba.cut(query) if w.strip())
        fts_ids = []
        if q_toks:
            try:
                fts_ids = [r["id"] for r in self._query(
                    "SELECT meta::id(id) AS id, search::score(1) AS s FROM material "
                    "WHERE tokens @1@ $q AND archived != true ORDER BY s DESC LIMIT $lim",
                    {"q": q_toks, "lim": k * 2})]
            except Exception:
                fts_ids = []
        # 图路:语义种子沿 relates 扩展 + about_entities 匹配本章提及实体
        graph_ids: list[str] = []
        for sid in vec_ids[:2]:
            graph_ids.extend(e["id"] for e in self.material_relates(sid))
        if mentioned_entities:
            try:
                graph_ids.extend(r["id"] for r in self._query(
                    "SELECT meta::id(id) AS id FROM material "
                    "WHERE about_entities CONTAINSANY $ents AND archived != true",
                    {"ents": list(mentioned_entities)}))
            except Exception:
                pass
        # RRF 融合三路 → 位次转分 → 强度加权
        fused = _reciprocal_rank_fusion(vec_ids, fts_ids, graph_ids, k=60)
        top_ids = [i for i, _ in fused[:k * 2]]
        if not top_ids:
            return []
        cands = []
        for i, mid in enumerate(top_ids):
            row = self.get_material(mid)
            if not row or row.get("archived"):
                continue   # 图路邻居可能含 archived,Python 层再兜一次
            row["material_id"] = mid
            row["score"] = 1.0 / (i + 1)
            cands.append(row)
        return apply_strength(cands)[:k]

    def material_graph(self, focus: str | None = None, limit: int = 200, hop: int = 1) -> dict:
        """素材记忆网络:节点(素材)+ relates 联想边,供前端 sigma 可视化。"""
        all_nodes = [{"id": m["id"], "title": m.get("title"), "kind": m.get("kind"),
                  "recall_count": m.get("recall_count") or 0, "pinned": bool(m.get("pinned")),
                  "ref_tags": m.get("ref_tags") or []}
                 for m in self.list_materials()]
        truncated = len(all_nodes) > limit
        nodes = all_nodes[:limit]
        keep = {n["id"] for n in nodes}
        edges = []
        degraded_sources = []
        try:
            rows = self._query(
                "SELECT meta::id(in) AS src, meta::id(out) AS dst, weight FROM relates")
            edges = [{"src": r["src"], "dst": r["dst"], "weight": r.get("weight") or 1.0}
                     for r in (rows or []) if r.get("src") in keep and r.get("dst") in keep]
        except Exception as e:
            edges = []
            degraded_sources.append({"source": "relates", "reason": str(e)})
        return {
            "nodes": nodes,
            "edges": edges,
            "edges_degraded": bool(degraded_sources),
            "degraded_sources": degraded_sources,
            "truncated": truncated,
        }

    # --- 题材层 craft 规则(per-work)---
    def add_craft_rule(self, kind: str, pattern: str, note: str = "") -> None:
        self._execute_write(
            "CREATE craft_rule SET kind=$k, pattern=$p, note=$n",
            {"k": kind, "p": pattern, "n": note})

    def list_craft_rules(self) -> list[dict]:
        return self._query("SELECT meta::id(id) AS id, kind, pattern, note FROM craft_rule")

    def delete_craft_rule(self, rid: str) -> None:
        self._execute_write("DELETE type::record('craft_rule',$r)", {"r": rid})

    def purple_patterns(self) -> list[str]:
        """本书升华正则(喂 critique.find_purple_prose 的 extra_patterns)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "purple_regex"]

    def allow_patterns(self) -> list[str]:
        """方案B任务14:本书题材豁免正则(前置 skip 判定——减法,与 purple_patterns/
        extra_patterns 的加法标记彻底分离)。实际消费方:critique.find_purple_prose
        (经 quality_flags/quality_issues 透传)与 critique.find_emotion_telling
        (app.py /post-check 直接传入)——不是"各检测器"都吃这个白名单,新增消费方
        时请在此处补记,避免文档与接线脱节(收尾清理批 B14 审查发现)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "allow_pattern"]

    def allow_words(self) -> list[str]:
        """方案B任务14:本书题材豁免词(喂 critique.find_ai_tics 的 allow_words 白名单)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "allow_word"]

    def seed_craft_rules(self) -> None:
        """首书(乱世铜炉系)种子:scribe2 实战的升华正则8条 + 法器四件套。幂等(已有则跳过)。"""
        if self.list_craft_rules():
            return
        for p in ["天地为炉|万物为铜|在炉里", r"原来.{0,30}(就|早就|从一开始)",
                  r"从.{1,18}那一刻起", r"像.{0,12}[滴颗].{0,8}眼泪", "影子被拉得很长",
                  r"(有些|有的).{0,14}(就再也|再也)", r"他知道[，,].{0,4}(回不去|不一样了)",
                  "走下去|刀山火海"]:
            self.add_craft_rule("purple_regex", p, "乱世铜炉升华句(scribe2实证)")
        self.add_craft_rule(
            "artifact_craft",
            "法器/法术首次出场须四件套:专名+工艺工序+术数+义理(至少齐3项)",
            "范例:灵龙镇煞钉·阳铜黑狗血七七四十九天炼成·三百六十支围太极阵·画井为狱镇魂锁煞")

    # --- 声音进化标记 ---
    def add_voice_flag(self, character: str, seq: int, reason: str,
                       ingest_seq: int | None = None) -> None:
        # seq 是退场方(021 起改名为 trigger_chapter)。只写真源 trigger_chapter。
        # character_id 规范化(批D P1-11 后端跟进):ingest 的 voice_shift 路径传裸名(who),
        # 而 fold_voice_flags/add_char_state 一律用 role: 前缀 id 匹配 → 裸名 flag 永不被 fold
        # (主书历史裸名 flag 致前端 fold 空操作)。此处统一在写入层补 role: 前缀,幂等:
        # 已带前缀(add_char_state 传 role:xxx / ingest arc 经 _resolve_char)不二次加前缀。
        cid = character if ":" in character else f"role:{character}"
        self._execute_write(
            "CREATE voice_evolution_flag SET character=$c, "
            "trigger_chapter=$s, reason=$r, status='open'"
            + (", ingest_seq=$i" if ingest_seq is not None else ""),
            {"c": cid, "s": seq, "r": reason,
             **({"i": ingest_seq} if ingest_seq is not None else {})})

    def list_voice_flags(self, status: str = "open") -> list[dict]:
        return self._query(
            "SELECT meta::id(id) AS id, character, trigger_chapter, reason, status "
            "FROM voice_evolution_flag WHERE status=$st", {"st": status})

    def resolve_voice_flag(self, flag_id: str) -> bool:
        """关闭声音演变 flag:将 status 从 'open' 改为 'done'。返回 True 若存在,False 若不存在。"""
        rows = self._query(
            "SELECT id FROM type::record('voice_evolution_flag',$fid) LIMIT 1", {"fid": flag_id})
        if not rows:
            return False
        self._execute_write(
            "UPDATE type::record('voice_evolution_flag',$fid) SET status='done'",
            {"fid": flag_id})
        return True

    def fold_voice_flags(self, character_id: str, complete_fn) -> dict:
        """半自动声音演变消化:将该角色的开放 voice_evolution_flag 折叠进 voice_profile。

        1. 取该角色 open flags;若无则直接返回 {"folded": 0}。
        2. 取当前 voice_profile(可为 None)。
        3. 构建 prompt → 调 complete_fn → 解析 JSON。
           解析失败(坏 JSON / 缺 style_summary) → fail-soft:不改 profile,返回 {"folded": 0, "degraded": True}。
        4. 成功:set_voice_profile + resolve_voice_flag(每条 flag)。
        5. 返回 {"folded": n, "profile": updated_profile}。

        complete_fn 签名: (prompt: str) -> str(与 ingest_chapter 同签名)。
        """
        from scribe3.critique import build_voice_fold_prompt, parse_voice_profile_from_fold

        # 1. 取该角色 open flags
        all_open = self.list_voice_flags("open")
        char_flags = [f for f in all_open if f.get("character") == character_id]
        if not char_flags:
            return {"folded": 0}

        # 2. 取当前 voice_profile(保留原样用于 fail-soft 回退)
        current_profile = self.get_voice_profile(character_id)

        # 3. 构建 prompt + 调用 LLM + 解析
        try:
            prompt = build_voice_fold_prompt(current_profile, char_flags)
            reply = complete_fn(prompt)
            updated = parse_voice_profile_from_fold(reply)
        except Exception as e:
            logging.getLogger("scribe3.store").warning(
                "fold_voice_flags: complete_fn 或 prompt 失败(soft) character=%s: %s",
                character_id, e)
            return {"folded": 0, "degraded": True}

        if updated is None:
            # 解析失败:fail-soft,不改现有 profile
            return {"folded": 0, "degraded": True}

        # 4. 成功:先更新 profile,再 resolve 每条 flag
        # 若当前 profile 存在,合并现有字段(新值覆盖旧值)
        if current_profile:
            merged = dict(current_profile)
            merged.update(updated)
        else:
            merged = updated

        self.set_voice_profile(character_id, merged)

        for f in char_flags:
            flag_id = f.get("id")
            if flag_id:
                try:
                    self.resolve_voice_flag(flag_id)
                except Exception as e:
                    logging.getLogger("scribe3.store").warning(
                        "fold_voice_flags: resolve_voice_flag(%s) 失败(soft): %s", flag_id, e)

        return {"folded": len(char_flags), "profile": merged}

    # --- 伏笔/promise ---
    def plant_promise(self, text: str, setup_chapter: int, kind: str = "promise",
                      tier: str = "chapter", resolution: str = "") -> None:
        """种下伏笔。resolution(方案B任务21,收尾清理批 B21 落库):悬念存档答案,
        book/arc 长期悬念的强制校验在 REST 层(app.py /promises-new),store 层
        只负责落库,不做 tier 相关的必填校验——保持本函数对既有调用方(不传
        resolution 即空串)向后兼容,语义不变。"""
        if tier not in _TIER_WINDOW:
            raise ValueError(f"非法伏笔层级 tier='{tier}'(合法: {sorted(_TIER_WINDOW)})")
        lo, hi = _TIER_WINDOW[tier]
        pmin = setup_chapter + lo
        pmax = None if hi is None else setup_chapter + hi
        self._execute_write(
            "CREATE promise SET text=$t, setup_chapter=$s, payoff_chapter=NONE, status='open', "
            "kind=$k, tier=$tier, payoff_min=$pmin, payoff_max=$pmax, "
            "resolution=$resolution",
            {"t": text, "s": setup_chapter, "k": kind,
             "tier": tier, "pmin": pmin, "pmax": pmax,
             "resolution": resolution or None})

    def list_promises(self) -> list[dict]:
        rows = self._query("SELECT meta::id(id) AS id, text, setup_chapter, payoff_chapter, "
                           "status, kind, clues, tier, payoff_min, payoff_max, resolution "
                           "FROM promise ORDER BY setup_chapter")
        # 兼容旧库(未跑 045 迁移时 clues 字段为 None):安全回退为 []
        for r in rows:
            if r.get("clues") is None:
                r["clues"] = []
            # 兼容旧行(未跑 052 迁移前创建):tier 回退 chapter,窗口按 setup 补算。
            # book 层 payoff_max 合法为 None,不补;setup_chapter 为 None 时不补。
            if r.get("tier") is None:
                r["tier"] = "chapter"
            if r["tier"] == "chapter" and r.get("setup_chapter") is not None:
                lo, hi = _TIER_WINDOW["chapter"]
                if r.get("payoff_min") is None:
                    r["payoff_min"] = r["setup_chapter"] + lo
                if r.get("payoff_max") is None:
                    r["payoff_max"] = r["setup_chapter"] + hi
        return rows

    def open_promises(self) -> list[dict]:
        return [p for p in self.list_promises() if p["status"] == "open"]

    def promises_with_lifecycle(self, max_chapter: int | None = None) -> list[dict]:
        """list_promises + 派生 refresh_count/last_refresh_at(自 promise_touch)+ window 计算态。"""
        if max_chapter is None:
            max_chapter = self.max_chapter()
        touches = self._query(
            "SELECT promise_id, chapter FROM promise_touch ORDER BY chapter ASC")
        by_pid: dict[str, list[int]] = {}
        for t in touches or []:
            # 审查 P1-3:回看旧章视角(max_chapter=seq)时丢弃未来章 touch——
            # 否则 refresh_count 吃到 seq 之后的刷新,把旧章视角误升 decision。
            if (t.get("chapter") or 0) > max_chapter:
                continue
            by_pid.setdefault(t["promise_id"], []).append(t["chapter"])
        out = []
        for p in self.list_promises():
            chs = by_pid.get(p["id"], [])
            p = dict(p, refresh_count=len(chs), last_refresh_at=(chs[-1] if chs else None))
            p["window"] = promise_window_state(p, max_chapter)
            out.append(p)
        return out

    def advance_promise(self, promise_id: str, payoff_chapter: int) -> None:
        """回收伏笔:标 closed + payoff_chapter。payoff≥setup 校验(Python 侧先行,拒绝脏数据)。"""
        rows = self._query(
            "SELECT setup_chapter FROM type::record('promise',$pid)", {"pid": promise_id})
        if not rows:
            raise ValueError(f"promise '{promise_id}' 不存在")
        setup = rows[0].get("setup_chapter")
        if setup is not None and payoff_chapter < setup:
            raise ValueError(
                f"payoff_chapter({payoff_chapter}) < setup_chapter({setup}):回收不能早于埋设,拒绝写入。"
            )
        self._execute_write("UPDATE type::record('promise',$pid) SET status='closed', "
                            "payoff_chapter=$p", {"pid": promise_id, "p": payoff_chapter})

    def mark_promise_herring(self, promise_id: str) -> bool:
        """将伏笔标记为 red_herring(障眼法)。返回 True 若存在,False 若不存在。"""
        rows = self._query("SELECT id FROM type::record('promise',$pid) LIMIT 1", {"pid": promise_id})
        if not rows:
            return False
        self._execute_write(
            "UPDATE type::record('promise',$pid) SET kind='red_herring'", {"pid": promise_id})
        return True

    def add_promise_clue(self, promise_id: str, note: str, chapter: int) -> None:
        """追加一条草蛇灰线线索到 promise.clues[]{chapter, note}。
        幂等追加——不校验章号范围(由端点层可选校验);按 chapter 排序在 ledger 侧做。
        """
        rows = self._query(
            "SELECT clues FROM type::record('promise',$pid)", {"pid": promise_id})
        if not rows:
            raise ValueError(f"promise '{promise_id}' 不存在")
        existing = rows[0].get("clues") or []
        new_clue = {"chapter": chapter, "note": note}
        updated = existing + [new_clue]
        self._execute_write(
            "UPDATE type::record('promise',$pid) SET clues=$clues",
            {"pid": promise_id, "clues": updated})

    def remove_promise_clue(self, promise_id: str, idx: int) -> None:
        """按下标删除 promise.clues 中的一条线索(0-based)。"""
        rows = self._query(
            "SELECT clues FROM type::record('promise',$pid)", {"pid": promise_id})
        if not rows:
            raise ValueError(f"promise '{promise_id}' 不存在")
        existing = rows[0].get("clues") or []
        if idx < 0 or idx >= len(existing):
            raise IndexError(f"clue 下标 {idx} 超出范围(共 {len(existing)} 条)")
        updated = [c for i, c in enumerate(existing) if i != idx]
        self._execute_write(
            "UPDATE type::record('promise',$pid) SET clues=$clues",
            {"pid": promise_id, "clues": updated})

    def promise_ledger(self, slack: int) -> dict:
        """伏笔台账(单源)。三栏分类 + 每条 setup/payoff/overdue/跨度 + open/close bracket 审计。

        纯聚合,不改库。overdue 复用 _overdue_flag(与 /promises、/quality 同一份判定),
        阈值 slack 由调用方传入(intent.overdue_threshold ?? OVERDUE_SLACK,单源在端点解析)。

        返回:
          {threshold, max_chapter, open[], closed[], red_herring[],
           audit:{balanced, overdue_count, payoff_without_setup[], closed_without_setup[], never_paid}}
        每条 promise 携带 text/setup_chapter/payoff_chapter/status/kind/overdue;
        open/red_herring 额外带 chapters_open(=max-setup),closed 额外带 span(=payoff-setup)。
        """
        mc = self.max_chapter()
        proms = self.list_promises()
        open_col: list[dict] = []
        closed_col: list[dict] = []
        herring_col: list[dict] = []
        payoff_without_setup: list[dict] = []
        closed_without_setup: list[dict] = []

        for p in proms:
            setup = p.get("setup_chapter")
            payoff = p.get("payoff_chapter")
            # clues 按 chapter 排序(草蛇灰线中途线索)
            clues_sorted = sorted(p.get("clues") or [], key=lambda c: c.get("chapter", 0))
            row = {
                "id": p.get("id"),
                "text": p.get("text", ""),
                "kind": p.get("kind"),
                "status": p.get("status"),
                "setup_chapter": setup,
                "payoff_chapter": payoff,
                "overdue": _overdue_flag(p, mc, slack),
                "clues": clues_sorted,
            }
            # audit: 闭无开(deus ex machina 的可检形态)
            if payoff is not None:
                if setup is None or setup <= 0:
                    closed_without_setup.append(
                        {"id": p.get("id"), "text": p.get("text", ""),
                         "setup_chapter": setup, "payoff_chapter": payoff})
                elif payoff < setup:
                    payoff_without_setup.append(
                        {"id": p.get("id"), "text": p.get("text", ""),
                         "setup_chapter": setup, "payoff_chapter": payoff})

            # 三栏分类:red_herring 单列(优先;即便 status=open 也不混入 open 栏)
            if p.get("kind") == "red_herring":
                row["chapters_open"] = (mc - setup) if setup is not None else None
                herring_col.append(row)
            elif p.get("status") == "closed":
                row["span"] = (payoff - setup) if (payoff is not None and setup is not None) else None
                closed_col.append(row)
            else:
                row["chapters_open"] = (mc - setup) if setup is not None else None
                open_col.append(row)

        # open 按紧迫度(chapters_open)降序;closed 按 payoff 升序
        open_col.sort(key=lambda r: -(r.get("chapters_open") or 0))
        closed_col.sort(key=lambda r: (r.get("payoff_chapter") or 0))

        overdue_count = sum(1 for r in open_col if r["overdue"])
        never_paid = len(open_col)  # 契诃夫枪"埋了未响":open 非 red_herring 计数
        balanced = (overdue_count == 0
                    and not payoff_without_setup
                    and not closed_without_setup)
        return {
            "threshold": slack,
            "max_chapter": mc,
            "open": open_col,
            "closed": closed_col,
            "red_herring": herring_col,
            "audit": {
                "balanced": balanced,
                "overdue_count": overdue_count,
                "payoff_without_setup": payoff_without_setup,
                "closed_without_setup": closed_without_setup,
                "never_paid": never_paid,
            },
        }

    # --- 章节正文(manuscript)---
    def _compute_chapter_caches(self, seq: int, prose: str) -> dict:
        """算章级缓存,返回 {scene_count, scene_meta, qc_issues, qc_causal, qc_breakdown}。
        供 save_chapter 落库 + backfill 回填复用。纯计算,不写库。
        - 场景:_split_scenes(prose) → scene_count + [{title, char_count}, ...](序列化为 JSON 串)。
        - QC问题:critique.quality_flags(prose) 五类计数之和(纯文本,无需图);拆分存 qc_breakdown JSON。
        - 因果违规:verify.causal_complete(self, seq) 违规条数(查该章事件图,O(本章事件))。
          注意:这是写时快照——若事件图在不重存本章的情况下变更,qc_causal 会陈旧(可接受降级)。
        """
        import json
        scenes = _split_scenes(prose)
        scene_meta = json.dumps(
            [{"title": s["title"], "char_count": s["chars"]} for s in scenes],
            ensure_ascii=False)
        from scribe3.critique import quality_flags
        qf = quality_flags(prose)
        breakdown = {
            "repetition": len(qf["repetition"]),
            "structural": len(qf["structural"]),
            "purple": len(qf["purple"]),
            "ai_tics": len(qf["ai_tics"]),
            "oversaturation": len(qf["oversaturation"]),
        }
        qc_n = sum(breakdown.values())
        try:
            from scribe3.verify import causal_complete
            # 批D P1-5 假绿止血:本章无落库事件时写 -1 哨兵(无事件数据),
            # 区分'因果完整=0'与'根本没有事件可校验'——防空事件图恒返 0 被读作真绿。
            if not self.events_at(seq):
                qc_causal_n = -1
            else:
                qc_causal_n = len(causal_complete(self, seq))
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "qc_causal 计算失败(降级为 0): %s", _e)
            qc_causal_n = 0
        return {"scene_count": len(scenes), "scene_meta": scene_meta,
                "qc_issues": qc_n, "qc_causal": qc_causal_n,
                "qc_breakdown": json.dumps(breakdown, ensure_ascii=False),
                # 内存透传(不落章表):scorecard 复用同一份 quality_flags,免重算(北极星任务3)
                "_quality_flags": qf}

    def _compute_scorecard(self, seq: int, prose: str, focalizer: str | None,
                           precomputed_flags: dict | None = None) -> dict:
        """章级北极星 scorecard 三分栏(北极星任务3,蓝图 §3-③ 前半)。纯计算不写库。

        constraints(硬,全确定性):leaks(全知章 None=N/A,绝不写 0 假绿)/
          degeneration_blocking / qc_causal(-1 哨兵=无事件数据)/ promise_overdue。
        advisory_scores(软参考,只提示不门禁):ai_grade / qc_breakdown。
        fulfillment(正向达成):任务6 目的合同接入前占位 not_available。
        每个检测器独立 fail-soft:挂了记 degraded 如实上报(不假绿),绝不拖垮存稿。
        不合成总分(宪法条款)。
        """
        constraints: dict = {}
        advisory: dict = {}
        degraded: list[str] = []
        try:
            if focalizer:
                from scribe3.verify import find_leaks
                constraints["leaks"] = len(find_leaks(prose, self, focalizer, seq))
            else:
                constraints["leaks"] = None   # 全知章泄密不可判:N/A ≠ 0
        except Exception:
            degraded.append("leaks")
            constraints["leaks"] = None
        try:
            from scribe3.critique import find_degeneration
            degs = find_degeneration(prose)
            constraints["degeneration_blocking"] = sum(
                1 for d in degs if d.get("severity") == "blocking")
            constraints["degeneration_total"] = len(degs)
        except Exception:
            degraded.append("degeneration")
            constraints["degeneration_blocking"] = None
            constraints["degeneration_total"] = None
        try:
            from scribe3.verify import causal_complete
            constraints["qc_causal"] = (-1 if not self.events_at(seq)
                                        else len(causal_complete(self, seq)))
        except Exception:
            degraded.append("qc_causal")
            constraints["qc_causal"] = None
        try:
            rows = self.promises_with_lifecycle(max_chapter=seq)
            constraints["promise_overdue"] = sum(
                1 for p in rows if (p.get("window") or {}).get("state") == "overdue")
        except Exception:
            degraded.append("promise_overdue")
            constraints["promise_overdue"] = None
        try:
            from scribe3.critique import aggregate_ai_grade, quality_flags
            qf = precomputed_flags if precomputed_flags is not None else quality_flags(prose)
            g = aggregate_ai_grade(qf, prose)
            advisory["ai_grade"] = {"grade": g.get("grade"), "gates_hit": g.get("gates_hit")}
            advisory["qc_breakdown"] = {k: len(qf.get(k) or []) for k in
                                        ("repetition", "structural", "purple",
                                         "ai_tics", "oversaturation")}
        except Exception:
            degraded.append("ai_grade")
            advisory["ai_grade"] = None
            advisory["qc_breakdown"] = None
        # 北极星任务6:目的合同接入后 fulfillment 出真数据(登记了 deltas 的章);
        # 未登记章保持 not_available 占位。carried 链≥2 → alert(连续未达成告警,蓝图 §3-④)。
        _ful_read_failed = False
        try:
            rows = self._query("SELECT deltas FROM type::record('chapter',$s)", {"s": seq})
            from scribe3.purpose import parse_deltas
            ds = parse_deltas(rows[0].get("deltas") if rows else None)
        except Exception:
            degraded.append("fulfillment")
            _ful_read_failed = True   # P1门审查 P2-10:读取失败≠未登记,note 不得误导
            ds = []
        if ds:
            counts = {s: sum(1 for d in ds if d.get("status") == s)
                      for s in ("planned", "achieved", "carried", "waived")}
            chain = max(((seq - d["carried_from"]) for d in ds
                         if d.get("status") == "carried" and d.get("carried_from") is not None),
                        default=1 if counts["carried"] else 0)
            fulfillment = {"status": "active", "total": len(ds), **counts,
                           "carried_chain_max": chain, "alert": chain >= 2}
        elif _ful_read_failed:
            fulfillment = {"status": "unavailable", "deltas": [],
                           "note": "目的数据读取失败(degraded),非未登记——修好后重存本章刷新"}
        else:
            fulfillment = {"status": "not_available", "deltas": [],
                           "note": "本章未登记目的合同(空 delta 章照常可写)"}
        return {"seq": seq, "constraints": constraints, "advisory_scores": advisory,
                "fulfillment": fulfillment, "degraded": degraded}

    def _upsert_scorecard(self, sc: dict) -> None:
        import json
        self._execute_write(
            "UPSERT type::record('chapter_scorecard',$seq) SET seq=$seq, constraints=$c, "
            "advisory=$a, fulfillment=$f, degraded=$d, computed_at=time::now()",
            {"seq": sc["seq"],
             "c": json.dumps(sc["constraints"], ensure_ascii=False),
             "a": json.dumps(sc["advisory_scores"], ensure_ascii=False),
             "f": json.dumps(sc["fulfillment"], ensure_ascii=False),
             "d": json.dumps(sc["degraded"], ensure_ascii=False)})

    def get_chapter_scorecard(self, seq: int) -> dict | None:
        """读章 scorecard;缓存行缺失(旧库章)→ 现算回填(lazy backfill)。
        章不存在或无正文 → None(端点侧 404)。"""
        import json
        rows = self._query(
            "SELECT seq, constraints, advisory, fulfillment, degraded, "
            "<string> computed_at AS computed_at "
            "FROM type::record('chapter_scorecard',$s)", {"s": seq})
        if rows:
            r = rows[0]
            return {"seq": seq,
                    "constraints": json.loads(r.get("constraints") or "{}"),
                    "advisory_scores": json.loads(r.get("advisory") or "{}"),
                    "fulfillment": json.loads(r.get("fulfillment") or "{}"),
                    "degraded": json.loads(r.get("degraded") or "[]"),
                    "computed_at": r.get("computed_at")}
        ch = self.get_chapter(seq)
        if not ch or not (ch.get("prose") or "").strip():
            return None
        sc = self._compute_scorecard(seq, ch["prose"], ch.get("focalizer"))
        try:
            self._upsert_scorecard(sc)
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "scorecard lazy 回填落库失败(返回现算结果): %s", _e)
        return sc

    def save_chapter(self, seq: int, prose: str, title: str = "", focalizer: str | None = None,
                     _today: str | None = None) -> None:
        """落/覆盖某章正文(UPSERT)。附带章向量 + QC缓存(字数,不再全拉正文统计)。
        _today:测试时注入固定日期字符串(YYYY-MM-DD),生产不传。"""
        # 审计 E-1:embedding 是召回辅助不是正文,故障绝不拖死存稿(命门 fail-soft)。
        text_for_embed = f"{title} {prose[:200]}".strip()
        try:
            from scribe3.embed import embed
            vec = embed([text_for_embed])[0]
        except Exception as _ee:
            logging.getLogger("scribe3.store").warning(
                "save_chapter embedding 失败(正文照存,该章暂无语义召回向量): %s", _ee)
            vec = None
        wc = len("".join(prose.split()))
        # 千万字缓存(Phase0-BE1):落库时算好场景切分 + QC 计数,聚合端点不再全表拉正文/重算。
        cache = self._compute_chapter_caches(seq, prose)
        self._execute_write(
            "UPSERT type::record('chapter',$seq) SET seq=$seq, title=$title, "
            "focalizer=$foc, prose=$prose, embedding=$v, qc_word_count=$wc, "
            "scene_count=$scn, scene_meta=$scm, qc_issues=$qc, qc_causal=$qcc, qc_breakdown=$qcb, "
            "archived=false, archived_at=NONE, archive_reason=NONE RETURN NONE",
            {"seq": seq, "title": title, "foc": focalizer, "prose": prose, "v": vec, "wc": wc,
             "scn": cache["scene_count"], "scm": cache["scene_meta"], "qc": cache["qc_issues"],
             "qcc": cache["qc_causal"], "qcb": cache["qc_breakdown"]})
        # 北极星任务3:章级 scorecard 存稿即算(独立缓存表,D-008)——fail-soft,
        # scorecard 是面板不是命门,失败只告警绝不阻断存稿。
        try:
            self._upsert_scorecard(self._compute_scorecard(
                seq, prose, focalizer, precomputed_flags=cache.get("_quality_flags")))
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "chapter_scorecard 计算/落库失败(存稿不受影响): %s", _e)
        # 北极星任务9:QD 文体档案存稿即算(纯确定性,fail-soft)。
        try:
            from scribe3.qd import chapter_style_profile
            self._upsert_style_profile(seq, chapter_style_profile(prose, focalizer))
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "style_profile 计算/落库失败(存稿不受影响): %s", _e)
        # fail-soft:记账失败绝不阻断存稿(统计是锦上添花,存稿是命门)
        try:
            self._record_daily_progress(seq, today=_today)
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "_record_daily_progress 失败(记账跳过,存稿不受影响): %s", _e)

    def add_chapter_version(self, seq: int, prose: str, label: str = "",
                            kind: str = "checkpoint", qc: dict | None = None,
                            stage: str = "final", summary: str = "",
                            stats: dict | None = None) -> str:
        """记一个存档点。返回新版本的裸 id。
        Phase0-BE2:扩 stage('draft'|'final')/ summary / stats(JSON 串绕嵌套 schema)。
        向后兼容:旧调用不传 stage → 默认 'final';stats 不传 → 不写(列为 NONE)。
        """
        import json
        stats_str = json.dumps(stats, ensure_ascii=False) if stats is not None else None
        rows = self._query(
            "CREATE chapter_version SET seq=$seq, prose=$prose, label=$label, "
            "kind=$kind, qc=$qc, stage=$stage, summary=$summary, stats=$stats, "
            "created_at=time::now()",
            {"seq": seq, "prose": prose, "label": label, "kind": kind, "qc": qc or {},
             "stage": stage, "summary": summary, "stats": stats_str})
        # CREATE 返回新记录(含 id,形如 'chapter_version:xxxx');取裸 id 部分。
        rid = rows[0]["id"] if rows else None
        return str(rid).split(":")[-1] if rid else ""

    def list_chapter_versions(self, seq: int) -> list[dict]:
        """某章存档点列表(不含 prose 全文),最新在前。
        stage 缺失(旧版本)降级为 'final'(向后兼容)。"""
        rows = self._query(
            "SELECT meta::id(id) AS id, seq, label, kind, qc, "
            "stage, summary, stats, created_at "
            "FROM chapter_version WHERE seq=$seq ORDER BY created_at DESC",
            {"seq": seq})
        for r in rows:
            if not r.get("stage"):
                r["stage"] = "final"
            r.setdefault("summary", "")
        return rows

    def get_chapter_version(self, vid: str) -> dict | None:
        """单个存档点全文(回看用)。"""
        rows = self._query(
            "SELECT meta::id(id) AS id, seq, prose, label, kind, qc, "
            "stage, summary, stats, created_at "
            "FROM type::record('chapter_version', $vid)", {"vid": vid})
        if not rows:
            return None
        r = rows[0]
        if not r.get("stage"):
            r["stage"] = "final"
        r.setdefault("summary", "")
        return r

    def latest_draft_version(self, seq: int) -> dict | None:
        """该章最新 draft 版(prose+stats),供刷新恢复。无 draft 版返回 None。"""
        rows = self._query(
            "SELECT meta::id(id) AS id, seq, prose, label, summary, stats, created_at "
            "FROM chapter_version WHERE seq=$seq AND stage='draft' "
            "ORDER BY created_at DESC LIMIT 1",
            {"seq": seq})
        if not rows:
            return None
        r = rows[0]
        r["stage"] = "draft"
        r.setdefault("summary", "")
        return r

    def save_chapter_draft(self, seq: int, draft: str) -> None:
        """落/覆盖某章草稿(与定稿 prose 分离;UPSERT 不碰 prose/embedding/qc)。
        刷新恢复读 chapter.draft(最新草稿);留版另走 add_chapter_version(stage='draft')。"""
        self._execute_write(
            "UPSERT type::record('chapter',$seq) SET seq=$seq, draft=$draft RETURN NONE",
            {"seq": seq, "draft": draft})

    def get_chapter(self, seq: int) -> dict | None:
        """单章身份 + 四阶段内容(synopsis/beats/draft/prose)。
        beats 存为 JSON 串,读时解析为 list;缺失降级为 []。"""
        rows = self._query(
            "SELECT seq,title,focalizer,prose,synopsis,beats,draft,"
            "scene_truth,involved_characters,deductions,purpose_text,deltas,"
            "archived,<string> archived_at AS archived_at,archive_reason,"
            "ingest_status,ingest_error "   # 审计 P1-6:反哺结果对前端可见
            "FROM type::record('chapter',$seq)", {"seq": seq})
        if not rows:
            return None
        r = rows[0]
        raw_beats = r.get("beats")
        try:
            r["beats"] = json.loads(raw_beats) if raw_beats else []
        except (ValueError, TypeError):
            r["beats"] = []
        for _k in ("involved_characters", "deductions", "deltas"):
            raw = r.get(_k)
            try:
                r[_k] = json.loads(raw) if raw else []
            except (ValueError, TypeError):
                r[_k] = []
        r["scene_truth"] = r.get("scene_truth") or ""
        r["archived"] = bool(r.get("archived"))
        r["archive_reason"] = r.get("archive_reason") or ""
        return r

    def list_chapters(self) -> list[dict]:
        return self._query(
            "SELECT seq,title FROM chapter:.. "
            "WHERE archived = NONE OR archived != true ORDER BY seq")

    def chapter_seqs_in_range(self, start_seq: int, end_seq: int) -> list[int]:
        """闭区间读取已存章节号;不过滤归档章,供 pilot 判定 record 是否存在。"""
        target = _chapter_range_target(start_seq, end_seq)
        rows = self._query(f"SELECT seq FROM {target} ORDER BY seq")
        return [int(row["seq"]) for row in rows if row.get("seq") is not None]

    def chapters_lite(self) -> list[dict]:
        """遗留处置 2-D(#5):书级面板窄查询——一次拉草料/目的字段,不拉 prose/embedding
        (north_star_book 原逐章 get_chapter 全行,几百章时既慢又占内存)。缺失字段补 None,
        调用方不必区分"无键"与"空值"。"""
        rows = self._query(
            "SELECT seq, title, synopsis, beats, scene_truth, deltas FROM chapter:.. "
            "WHERE archived = NONE OR archived != true ORDER BY seq")
        for r in rows:
            for k in ("title", "synopsis", "beats", "scene_truth", "deltas"):
                r.setdefault(k, None)
        return rows

    # --- 书级聚合小件(北极星任务7)---
    def total_word_count(self) -> int:
        """全书可见字数合计(qc_word_count 存稿缓存求和,不拉正文)。"""
        rows = self._query(
            "SELECT math::sum(qc_word_count) AS w FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL")
        return int((rows[0].get("w") if rows else 0) or 0)

    def causal_debt_total(self) -> int:
        """因果欠账存量:各章 qc_causal 正值求和(-1 哨兵=无事件数据,不计入)。
        蓝图 §3-②:brief 只催收 top-5,超出部分落面板由此字段承载。"""
        rows = self._query(
            "SELECT qc_causal FROM chapter:.. WHERE archived = NONE OR archived != true")
        return sum((r.get("qc_causal") or 0) for r in rows
                   if (r.get("qc_causal") or 0) > 0)

    def recent_proses(self, before_seq: int, k: int = 5) -> list[dict]:
        """before_seq 之前最近 k 章的 {seq, prose}(按 seq 升序)。
        供跨章复读检测与"前文已用措辞→生成时避免"清单复用。"""
        target = _chapter_range_target(end=before_seq, end_inclusive=False)
        rows = self._query(
            f"SELECT seq, prose FROM {target} "
            "WHERE archived = NONE OR archived != true "
            "ORDER BY seq DESC LIMIT $k", {"k": k})
        return list(reversed(rows))

    def motif_terms(self) -> set[str]:
        """刻意母题/专名白名单(≥2字):母题名各部分 + 少量物名/地名/书名。
        跨章复读判定时放行——乱世铜炉式母题本应复现,只揪'动作/句式偷懒重打'。"""
        terms: set[str] = set()
        for m in self.list_motifs():
            name = (m.get("name") or "")
            for ch in "()（）":
                name = name.replace(ch, "|")
            for part in name.split("|"):
                p = part.strip()
                if len(p) >= 2:
                    terms.add(p)
        terms.update({"镇煞钉", "灵龙镇煞钉", "奈何谷", "大元炼真经",
                      "清潭派", "云阳真人", "三百六十", "老槐树"})
        return terms

    def stats(self) -> dict:
        """本书章数 + 字数(读 QC 缓存,不回传全表正文)。"""
        count_rows = self._query(
            "SELECT count() AS chapter_count FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL")
        word_rows = self._query(
            "SELECT math::sum(qc_word_count) AS word_count FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL")
        chapter_count = (count_rows[0].get("chapter_count") if count_rows else 0) or 0
        word_count = (word_rows[0].get("word_count") if word_rows else 0) or 0
        return {"chapter_count": chapter_count, "word_count": word_count}

    # --- 每日码字账 ---
    def _record_daily_progress(self, seq: int, today: str | None = None) -> None:
        """把本次 save_chapter 的净增字数累加进今日 daily_progress 行。
        注意:此方法本身不做 fail-soft 包裹(调用者 save_chapter 负责捕获)。
        delta = 落库后全书总字数 - 上次记账的 words_total(最近一行)。
        record id 格式 daily_progress:<YYYY-MM-DD>,字典序即日期序;
        `date` 是 SurrealDB 保留字,ORDER BY 用 id 替代。
        """
        import time as _time
        today = today or _time.strftime("%Y-%m-%d")
        new_total = self.stats().get("word_count", 0)
        # `date` 是 SurrealDB 保留字,ORDER BY 须用别名;字典序即日期降序
        rows = self._query(
            "SELECT date AS dp_date, words_total FROM daily_progress ORDER BY dp_date DESC LIMIT 1")
        # 用最近一行(任意日)的 words_total 作 prev,delta = 全书净增
        prev_total = rows[0]["words_total"] if rows else 0
        delta = max(0, new_total - prev_total)  # 缩写日记 0,不倒扣;words_total 快照仍如实更新
        # save_count / chapters_touched:疑似死(P2-15)——写入(下方)但无生产读取方
        #   (progress()/_streak 只读 words_written/words_total),仅 test_store 断言写入。
        #   保留写侧供未来 /progress UI("今日存 N 次/触 M 章");疑似死待确认。
        self._execute_write(
            "UPSERT type::record('daily_progress', $d) SET "
            "date=$d, "
            "words_written = (IF words_written THEN words_written + $delta ELSE $delta END), "
            "words_total=$total, "
            "save_count = (IF save_count THEN save_count + 1 ELSE 1 END), "
            "chapters_touched = array::distinct((IF chapters_touched THEN chapters_touched ELSE [] END) + [$seq]), "
            "updated_at=time::now()",
            {"d": today, "delta": delta, "total": new_total, "seq": seq})

    def progress(self, today: str | None = None, window: str | None = None) -> dict:
        """日字数序列 + 累计曲线 + 目标完成度 + 趋势窗口 + 最高产星期几。
        读 daily_progress + intent,纯聚合。
        window: '30' | '90' | 'all'(默认 'all')
        """
        import time as _time
        from datetime import date as _date, timedelta as _td
        today = today or _time.strftime("%Y-%m-%d")
        # `date` 是 SurrealDB 保留字,ORDER BY 须用别名;字典序即日期升序
        rows = self._query(
            "SELECT date AS dp_date, words_written, words_total FROM daily_progress ORDER BY dp_date")
        intent = self.get_intent()
        total_goal = intent.get("total_word_goal")       # None → 前端回退 100000
        daily_goal = intent.get("daily_word_goal")       # None → 不显每日目标
        total_words = self.stats().get("word_count", 0)
        # 把 dp_date 别名统一为 date 键(供 _compute_streaks 纯函数和输出共用)
        all_normalized = [{"date": r["dp_date"], "words_written": r["words_written"],
                           "words_total": r["words_total"]} for r in rows]

        # streak / heatmap 始终用全量数据,不受 window 裁剪影响
        cur_streak, longest_streak = _compute_streaks(all_normalized, today, daily_goal)
        today_words = next((r["words_written"] for r in all_normalized if r["date"] == today), 0)

        # window 裁剪:仅影响 daily 序列(用于图表);heatmap / streak 用全量
        win = str(window).strip() if window else "all"
        if win in ("30", "90"):
            n_days = int(win)
            cutoff = (_date.fromisoformat(today) - _td(days=n_days - 1)).isoformat()
            windowed = [r for r in all_normalized if r["date"] >= cutoff]
        else:
            windowed = all_normalized  # 'all' 或其他值均视为全程

        # weekday_histogram:基于全量数据聚合,返回 7 个槽(周一=0…周日=6)
        # 每槽:{weekday, label, total_words, avg_words, count}
        from collections import defaultdict
        _wd_total: dict[int, int] = defaultdict(int)
        _wd_count: dict[int, int] = defaultdict(int)
        for r in all_normalized:
            try:
                d = _date.fromisoformat(r["date"])
                ww = d.weekday()  # 0=周一,6=周日
                words = r.get("words_written") or 0
                if words > 0:   # 只统计有写字的天
                    _wd_total[ww] += words
                    _wd_count[ww] += 1
            except ValueError:
                pass
        _WD_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday_histogram = []
        for ww in range(7):
            tot = _wd_total.get(ww, 0)
            cnt = _wd_count.get(ww, 0)
            weekday_histogram.append({
                "weekday": ww,
                "label": _WD_LABELS[ww],
                "total_words": tot,
                "avg_words": round(tot / cnt) if cnt > 0 else 0,
                "count": cnt,
            })
        # 最高产星期几:按 avg_words 降序,取第一个有数据的
        best_wd = max(weekday_histogram, key=lambda x: x["avg_words"], default=None)
        best_weekday = best_wd["label"] if best_wd and best_wd["avg_words"] > 0 else None

        # 理想线(ideal):若设了 total_word_goal,按匀速插值
        # 起点=第一条记录日期,终点=总目标字数,每天均摊
        ideal_daily_rate = None
        if total_goal and total_goal > 0 and windowed:
            first_date = _date.fromisoformat(windowed[0]["date"])
            today_date = _date.fromisoformat(today)
            total_days_elapsed = max(1, (today_date - first_date).days + 1)
            ideal_daily_rate = round(total_goal / total_days_elapsed)   # 匀速字数/天
        # 在 daily 序列里附加 ideal_cumulative(匀速理想累计)
        daily_with_ideal = []
        for i, r in enumerate(windowed):
            row_date = _date.fromisoformat(r["date"])
            row = {"date": r["date"], "words": r["words_written"], "cumulative": r["words_total"]}
            if total_goal and windowed:
                first_d = _date.fromisoformat(windowed[0]["date"])
                days_from_start = (row_date - first_d).days + 1
                row["ideal_cumulative"] = min(total_goal, round(total_goal * days_from_start
                                              / max(1, (_date.fromisoformat(today) - first_d).days + 1)))
            daily_with_ideal.append(row)

        return {
            "today": today,
            "window": win,
            "total_words": total_words,
            "total_word_goal": total_goal,
            "daily_word_goal": daily_goal,
            "today_words": today_words,
            "daily": daily_with_ideal,
            "current_streak": cur_streak,
            "longest_streak": longest_streak,
            "heatmap": [{"date": r["date"], "words": r["words_written"]} for r in all_normalized],
            "weekday_histogram": weekday_histogram,
            "best_weekday": best_weekday,
            "ideal_daily_rate": ideal_daily_rate,
        }

    # --- 北极星(作品意图,单例)---
    def get_intent(self) -> dict:
        rows = self._query(
            "SELECT reader_feeling, emotional_arc, red_lines, overdue_threshold, "
            "total_word_goal, daily_word_goal FROM intent:main")
        r = rows[0] if rows else {}
        result = {"reader_feeling": r.get("reader_feeling", ""),
                  "emotional_arc": r.get("emotional_arc", ""),
                  "red_lines": r.get("red_lines", "")}
        if r.get("overdue_threshold") is not None:
            result["overdue_threshold"] = r["overdue_threshold"]
        if r.get("total_word_goal") is not None:
            result["total_word_goal"] = r["total_word_goal"]
        if r.get("daily_word_goal") is not None:
            result["daily_word_goal"] = r["daily_word_goal"]
        return result

    def set_intent(self, fields: dict) -> None:
        # P2-12:MERGE(非 CONTENT 整替)——只写调用方真正传入的字段,未传字段保留库中旧值。
        # 此前 CONTENT 会把未传的 reader_feeling/emotional_arc/red_lines/阈值抹掉
        # (GET 失败后局部保存会毁未传目标)。intent 为 SCHEMAFULL,首建时缺省字段由 schema DEFAULT 补齐。
        content: dict = {}
        for k in ("reader_feeling", "emotional_arc", "red_lines"):
            if k in fields:
                content[k] = fields[k]
        if fields.get("overdue_threshold") is not None:
            content["overdue_threshold"] = fields["overdue_threshold"]
        if fields.get("total_word_goal") is not None:
            content["total_word_goal"] = int(fields["total_word_goal"])
        if fields.get("daily_word_goal") is not None:
            content["daily_word_goal"] = int(fields["daily_word_goal"])
        if not content:
            return
        self._execute_write("UPSERT intent:main MERGE $c", {"c": content})

    def graph(self, chapter: int | None = None, focus: str | None = None,
              limit: int = 300, hop: int = 1) -> dict:
        """知识图谱:角色/命题节点 + knows/关系 边(Atlas 视图)。
        千万字基座(Phase0-BE1):不再无上限全图返回。

        - focus 给定 → 只返回该实体的 ego 子图:focus + hop 跳邻居 + 它们之间的边。
        - focus 为 None → 返回"按 secret(密)优先、再按 valid_from 倒序"排序的 top-limit
          命题节点 + 相关角色 + 这些节点间的边,**硬上限 limit**(节点总数 ≤ limit)。
        - chapter 时间门保留(截至该章;None=全书)。

        向后兼容:无新参数调用(graph()/graph(ch))仍返回 {nodes, edges},结构不变。
        """
        ch = chapter if chapter is not None else 9999
        chars = [{"id": e.id, "type": "character", "label": e.name} for e in self.characters()]
        props = [{"id": f.id, "type": "proposition",
                  "label": ("🔒 私密" if f.secret else (f.value or "")[:18]),
                  "secret": f.secret, "_vf": f.valid_from} for f in self.facts_at(ch)]
        # 全量边(限知门控后),供子图/全图共同筛选
        all_edges = []
        for k in self.knowledge:
            if k.knower_id == "reader" or k.since_chapter > ch:
                continue
            all_edges.append({"src": k.knower_id, "dst": k.proposition_id, "rel": "knows"})
        for r in self.relations_at(ch):
            all_edges.append({"src": f"role:{r['src']}", "dst": f"role:{r['dst']}", "rel": r["relation"]})

        def _strip(nodes):
            for n in nodes:
                n.pop("_vf", None)
            return nodes

        if focus:
            # —— ego 子图:从 focus 起 BFS hop 跳 ——
            keep = {focus}
            frontier = {focus}
            for _ in range(max(1, hop)):
                nxt = set()
                for e in all_edges:
                    if e["src"] in frontier:
                        nxt.add(e["dst"])
                    if e["dst"] in frontier:
                        nxt.add(e["src"])
                new = nxt - keep
                keep |= new
                frontier = new
                if not frontier:
                    break
            nodes = [n for n in (chars + props) if n["id"] in keep]
            edges = [e for e in all_edges if e["src"] in keep and e["dst"] in keep]
            return {"nodes": _strip(nodes), "edges": edges}

        # —— 无 focus:top-limit 重要度子集,硬上限 ——
        # 命题排序:secret 优先(密谋更值得看),再按 valid_from 倒序(近事在前)。
        props_sorted = sorted(
            props, key=lambda p: (0 if p.get("secret") else 1, -(p.get("_vf") or 0)))
        # 角色先占额(图骨架),命题填满到 limit。
        budget = max(0, limit)
        nodes = chars[:budget]
        remaining = budget - len(nodes)
        if remaining > 0:
            nodes += props_sorted[:remaining]
        keep = {n["id"] for n in nodes}
        edges = [e for e in all_edges if e["src"] in keep and e["dst"] in keep]
        return {"nodes": _strip(nodes), "edges": edges}

    def max_chapter(self) -> int:
        """书的最大章号:以 chapter 表实际章节为准(真实范围),并入 event 的 story_chapter 兜底。
        旧实现只数 event 表 → 仅有伏笔/章节而无事件时返回 0,使时间线/体检整体短路为空(真bug)。"""
        ch_rows = self._query("SELECT seq FROM chapter:..")
        seqs = [r["seq"] for r in (ch_rows or []) if r.get("seq") is not None]
        ev_rows = self._query("SELECT story_chapter AS ch FROM event")
        evs = [r["ch"] for r in (ev_rows or []) if r.get("ch") is not None]
        allv = seqs + evs
        return int(max(allv)) if allv else 0

    def events_at(self, chapter: int) -> list[Event]:
        """读取某章全部事件(沿图边取回 participants+effects,补 P03 限知裂口)。
        P3-e1 Fix 3: 读回 location / preconditions(之前写入后不回传,write-into-the-void)。"""
        rows = self._query(
            "SELECT meta::id(id) AS local, event_type, story_chapter, narrative_position, "
            "  motivated_by_goal, location, preconditions, "
            "  (SELECT meta::id(out) AS clocal, role FROM ->involves) AS parts, "
            "  (SELECT meta::id(out) AS plocal FROM ->causes) AS effs, "
            "  (SELECT meta::id(out) AS slocal, ctype FROM ->causal) AS causals "
            "FROM event WHERE story_chapter = $ch", {"ch": chapter})
        out = []
        for r in rows:
            participants = {p["role"]: f"role:{p['clocal']}" for p in (r.get("parts") or [])}
            effects = [f"fact:{e['plocal']}" for e in (r.get("effs") or [])]
            causal_in = [(f"ev:{c['slocal']}", c["ctype"]) for c in (r.get("causals") or [])]
            etype = r.get("event_type") or ""
            story_chapter = r.get("story_chapter") or 0
            # location 存储为 RecordID(place,x) → 回传为 "place:x" 字符串
            raw_loc = r.get("location")
            if raw_loc is not None:
                loc_str = str(raw_loc) if not isinstance(raw_loc, str) else raw_loc
            else:
                loc_str = None
            out.append(Event(f"ev:{r['local']}", etype,
                             participants=participants,
                             location=loc_str,
                             story_time=story_chapter,
                             preconditions=r.get("preconditions") or [],
                             effects=effects,
                             causal_in=causal_in,
                             motivated_by_goal=r.get("motivated_by_goal"),
                             narrative_position=r.get("narrative_position")))
        return out

    def _all_relations(self) -> list[dict]:
        """全量读角色关系(不带限知时间门):含已失效(until_chapter 非 NONE)的历史关系。
        供时间线工艺视图使用——需要画 since→until 全史甘特条,不能用 relations_at 的快照门控。
        与 relations_at 的关键区别:relations_at 只返回"某章仍开着"的关系,会漏失效历史;
        本方法 SELECT 全表,无 WHERE 时间过滤。"""
        return self._query(
            "SELECT meta::id(in) AS src, meta::id(out) AS dst, relation, "
            "since_chapter, until_chapter, note FROM character_relation")

    def _ev_chapter_map(self) -> dict[str, int]:
        """批量查所有事件的 id→story_chapter 映射,供 timeline() 用于 causal_in 章号补全。
        一次 SQL 全表扫,O(N) 内存,避免逐 causal_in 单独查库。"""
        rows = self._query("SELECT meta::id(id) AS local, story_chapter FROM event")
        return {f"ev:{r['local']}": r["story_chapter"] for r in rows if r.get("story_chapter") is not None}

    def _all_events_bulk(self) -> list["Event"]:
        """批量查全表所有事件(含图边 involves/causes/causal),一次往返。
        供 timeline() 事件泳道使用——替代逐章 events_at 循环(N 章→N 次多子查询往返)。
        返回结构与 events_at 完全一致(Event dataclass),调用方按章过滤/分组。"""
        rows = self._query(
            "SELECT meta::id(id) AS local, event_type, story_chapter, narrative_position, "
            "  motivated_by_goal, location, preconditions, "
            "  (SELECT meta::id(out) AS clocal, role FROM ->involves) AS parts, "
            "  (SELECT meta::id(out) AS plocal FROM ->causes) AS effs, "
            "  (SELECT meta::id(out) AS slocal, ctype FROM ->causal) AS causals "
            "FROM event")
        out = []
        for r in rows:
            participants = {p["role"]: f"role:{p['clocal']}" for p in (r.get("parts") or [])}
            effects = [f"fact:{e['plocal']}" for e in (r.get("effs") or [])]
            causal_in = [(f"ev:{c['slocal']}", c["ctype"]) for c in (r.get("causals") or [])]
            etype = r.get("event_type") or ""
            story_chapter = r.get("story_chapter") or 0
            raw_loc = r.get("location")
            loc_str = (str(raw_loc) if not isinstance(raw_loc, str) else raw_loc) if raw_loc is not None else None
            out.append(Event(f"ev:{r['local']}", etype,
                             participants=participants,
                             location=loc_str,
                             story_time=story_chapter,
                             preconditions=r.get("preconditions") or [],
                             effects=effects,
                             causal_in=causal_in,
                             motivated_by_goal=r.get("motivated_by_goal"),
                             narrative_position=r.get("narrative_position")))
        return out

    def _all_char_states_bulk(self) -> list[dict]:
        """批量查全表所有角色弧光记录,一次往返。
        供 timeline() 弧光泳道使用——替代逐角色 list_char_states 循环(N 角色→N 次单查)。
        返回与 list_char_states 字段完全一致,额外保留 character_id 供 Python 侧分组。"""
        return self._query(
            "SELECT meta::id(id) AS id, character_id, chapter, change_type, summary, "
            "before_state, after_state, trigger_event, arc_phase, affects_voice, confidence, "
            "lie_belief "
            "FROM char_state ORDER BY chapter ASC")

    def timeline(self, ch_from: int = 1, ch_to: int | None = None,
                 axis: str = "story", limit: int | None = None) -> list[dict]:
        """聚合 [ch_from, ch_to] 区间内所有"章号锚状态",归并成时间线条目。
        进阶:四类泳道—— events / promise(伏笔) / arc(弧光质变) / relation(关系全史)。
        无写、无限知门控(作者全知工艺视图)。复用既有读方法,不新增 SQL 真源。
        向后兼容:items 中 kind=event 的条目结构与 MVP 一致。
        完整期新增:refs.causal_in 从 [ev_id_str] 升级为 [{id, chapter}],
        供前端 SVG 因果弧线计算两端 x 坐标。

        完整期双轴(spec §3.1 / §3.5):
          axis='story'(默认,向后兼容)—— 事件按 story_chapter(故事编年)横铺。
          axis='narrative'           —— 事件按 narrative_position ?? story_chapter(叙事顺序)横铺;
                                         倒叙/闪回事件(story 早、narrative 晚)落到叙事位。
          排序键用 `narrative_position ?? story_chapter`(Python 侧回退,SurrealDB ORDER BY 不支持 ?? — F-01)。
          每个事件条目恒带 story_chapter / narrative_position,前端可在两者不同时标"闪回"。
          axis 只影响事件泳道的 chapter 投影;伏笔/弧光/关系仅有故事章,两轴一致。"""
        narrative = (axis == "narrative")
        mc = self.max_chapter()
        hi = ch_to if ch_to is not None else mc
        if hi == 0:
            return []
        items: list[dict] = []
        # D-3:伏笔泳道 overdue 走 _overdue_flag 单源(与 /promises、/quality、/promises/ledger 一致);
        # 此前读 p.get("overdue")(list_promises 从不填该键)→ 恒 False,破不变量⑤。
        _intent = self.get_intent()
        _slack = (_intent.get("overdue_threshold")
                  if _intent.get("overdue_threshold") is not None else OVERDUE_SLACK)

        # 预建 ev_id→chapter 映射,供 causal_in 章号补全(一次全表查,不逐条单查)
        # 同时用 _all_events_bulk() 一次性拉取全表事件(含图边),消除逐章 events_at N+1。
        ev_ch_map = self._ev_chapter_map()

        # ── 1. 事件泳道 ──
        # 一次全表查(含 involves/causes/causal 图边),Python 侧按投影坐标过滤到 [ch_from, hi]。
        # 不能只查 [ch_from, hi] 的 story 章:叙事轴下 story_chapter 在区间外
        # 但 narrative_position 落在区间内的闪回事件会被漏掉——全表查再按轴坐标过滤是正确做法。
        for ev in self._all_events_bulk():
            # 投影坐标:叙事轴用 narrative_position ?? story_time;故事轴用 story_time
            np = ev.narrative_position
            plot_ch = (np if np is not None else ev.story_time) if narrative else ev.story_time
            if not (ch_from <= plot_ch <= hi):
                continue
            subj = [v for k, v in ev.participants.items() if k == "SUBJ"]
            obj_ = [v for k, v in ev.participants.items() if k == "OBJ"]
            wit  = [v for k, v in ev.participants.items() if k == "WITNESS"]
            # causal_in 带章号:前端 SVG 弧线需知道两端 x=章号(用 story_chapter,稳定真源)
            causal_in_rich = [
                {"id": c[0], "chapter": ev_ch_map.get(c[0])}
                for c in ev.causal_in
            ]
            items.append({
                "chapter": plot_ch,                    # 当前轴的横铺坐标
                "kind": "event",
                "id": ev.id,
                "label": ev.type,
                "goal": ev.motivated_by_goal,
                "lane_keys": subj + obj_,
                "event_type": ev.type,
                "story_chapter": ev.story_time,        # 故事编年(恒在,前端"故事@N")
                "narrative_position": np,              # 叙事位(可空,前端"叙事@M")
                "refs": {
                    "subj": subj,
                    "obj": obj_,
                    "witness": wit,
                    "effects": ev.effects,
                    "location": ev.location,
                    "causal_in": causal_in_rich,
                },
            })

        # ── 2. 伏笔泳道(setup 埋点 + payoff 收点) ──
        for p in self.list_promises():
            s = p.get("setup_chapter")
            if s is None:
                continue
            if ch_from <= s <= hi:
                items.append({
                    "chapter": s,
                    "kind": "promise_setup",
                    "id": p["id"],
                    "label": p["text"],
                    "lane_keys": ["__promise__"],
                    "refs": {
                        "status": p.get("status"),
                        "promise_kind": p.get("kind"),
                        "payoff_chapter": p.get("payoff_chapter"),
                        "overdue": _overdue_flag(p, mc, _slack),
                    },
                })
            pf = p.get("payoff_chapter")
            if pf and ch_from <= pf <= hi:
                items.append({
                    "chapter": pf,
                    "kind": "promise_payoff",
                    "id": p["id"],
                    "label": p["text"],
                    "lane_keys": ["__promise__"],
                    "refs": {
                        "setup_chapter": s,
                        "promise_kind": p.get("kind"),
                        "status": p.get("status"),
                    },
                })

        # ── 3. 弧光质变泳道(char_state 每条一个◆点) ──
        # 一次全表查所有 char_state,Python 按 character_id 分组——消除逐角色 list_char_states N+1。
        for cs in self._all_char_states_bulk():
            ch = cs.get("chapter")
            if ch is None:
                continue
            if not (ch_from <= ch <= hi):
                continue
            cid = cs.get("character_id")
            if not cid:
                continue
            items.append({
                "chapter": ch,
                "kind": "arc",
                "id": cs["id"],
                "label": cs.get("summary", ""),
                "lane_keys": [cid],
                "refs": {
                    "character": cid,
                    "change_type": cs.get("change_type"),
                    "arc_phase": cs.get("arc_phase"),
                    "affects_voice": cs.get("affects_voice"),
                },
            })

        # ── 4. 关系泳道(全量读,含已失效历史;不用 relations_at 带时间门) ──
        for r in self._all_relations():
            sc = r.get("since_chapter")
            uc = r.get("until_chapter")
            src_key = f"role:{r['src']}"
            dst_key = f"role:{r['dst']}"
            if sc is not None and ch_from <= sc <= hi:
                items.append({
                    "chapter": sc,
                    "kind": "relation_start",
                    "id": f"{r['src']}->{r['dst']}@{sc}",
                    "label": r.get("relation", ""),
                    "lane_keys": [src_key, dst_key],
                    "refs": {
                        "src": src_key,
                        "dst": dst_key,
                        "relation": r.get("relation"),
                        "until_chapter": uc,
                        "note": r.get("note"),
                    },
                })
            if uc is not None and ch_from <= uc <= hi:
                items.append({
                    "chapter": uc,
                    "kind": "relation_end",
                    "id": f"{r['src']}->{r['dst']}@end{uc}",
                    "label": r.get("relation", ""),
                    "lane_keys": [src_key, dst_key],
                    "refs": {
                        "src": src_key,
                        "dst": dst_key,
                        "relation": r.get("relation"),
                        "since_chapter": sc,
                        "note": r.get("note"),
                    },
                })

        items.sort(key=lambda x: (x["chapter"], x["kind"]))
        # 千万字基座(Phase0-BE1):total items 硬上限,防一次返上万条。
        # limit 为 None → 不截断(向后兼容,小书全返);给定则取按章序最早的 limit 条。
        if limit is not None and len(items) > limit:
            items = items[:limit]
        return items

    def orphan_knowledge_edges(self) -> list[dict]:
        """扫描孤儿知识边:knows/reader_knows 中指向不存在命题的悬挂边。
        返回列表 [{type, knower, proposition_ref}];正常情况应为空列表。
        S4 (W3#8): 写作链路完整性校验——ingest purge 后不应留悬挂边。"""
        orphans: list[dict] = []
        # 1. knows 边:按 out 找不存在的命题
        knows_rows = self._query(
            "SELECT meta::id(in) AS knower_local, meta::tb(in) AS knower_tb, "
            "meta::id(out) AS prop_local FROM knows")
        for r in knows_rows:
            prop_local = r.get("prop_local")
            if prop_local is None:
                continue
            exists = self._query(
                "SELECT id FROM type::record('proposition',$p) LIMIT 1", {"p": prop_local})
            if not exists:
                orphans.append({
                    "type": "knows",
                    "knower": f"{r.get('knower_tb', 'character')}:{r.get('knower_local', '')}",
                    "proposition_ref": f"fact:{prop_local}",
                })
        # 2. reader_knows 边:proposition 字段存的是本体 oid 字符串(如 "fact:k3-0")
        rk_rows = self._query("SELECT proposition FROM reader_knows")
        for r in rk_rows:
            prop_ref = r.get("proposition")
            if prop_ref is None:
                continue
            # prop_ref 可能是 "fact:xxx" 字符串或 RecordID 对象
            prop_str = str(prop_ref)
            # 提取 proposition 表的 local id
            if ":" in prop_str:
                _, prop_local = prop_str.split(":", 1)
            else:
                prop_local = prop_str
            exists = self._query(
                "SELECT id FROM type::record('proposition',$p) LIMIT 1", {"p": prop_local})
            if not exists:
                orphans.append({
                    "type": "reader_knows",
                    "knower": "reader",
                    "proposition_ref": prop_str,
                })
        return orphans

    def load_knowledge(self) -> list[KnowledgeEdge]:
        """显式拉全部知识边(knows + reader_knows)。昂贵:2 条查询。调用方应缓存。"""
        rows = self._query(
            "SELECT meta::tb(in) AS itb, meta::id(in) AS iid, meta::tb(out) AS otb, "
            "meta::id(out) AS olocal, since_chapter, until_chapter, polarity, acquired_via, certainty FROM knows")
        edges = [KnowledgeEdge(_join(r["itb"], r["iid"]), _join(r["otb"], r["olocal"]),
                               r.get("polarity", True), r.get("certainty", 1.0), r.get("since_chapter", 0),
                               r.get("until_chapter"), r.get("acquired_via", "given")) for r in rows]
        rr = self._query("SELECT proposition, since_chapter FROM reader_knows")
        edges += [KnowledgeEdge("reader", r["proposition"], True, 1.0,
                                r.get("since_chapter", 0), None, "given") for r in rr]
        return edges

    @property
    def knowledge(self) -> list[KnowledgeEdge]:
        """向后兼容薄封装(委托 load_knowledge)。新代码用 load_knowledge + 显式缓存。"""
        return self.load_knowledge()

    # --- 角色关系图(B枢纽 character_relation)---
    def add_character_relation(self, src_oid: str, dst_oid: str, relation: str,
                               since_chapter: int, note: str | None = None) -> None:
        # R2.1: 验证 src/dst 实体存在,防悬挂边
        if self.entity(src_oid) is None:
            raise ValueError(
                f"add_character_relation: src '{src_oid}' 不存在,拒绝写入悬挂边。请先建立角色实体。"
            )
        if self.entity(dst_oid) is None:
            raise ValueError(
                f"add_character_relation: dst '{dst_oid}' 不存在,拒绝写入悬挂边。请先建立角色实体。"
            )
        _, sl = _split(src_oid)
        _, dl = _split(dst_oid)
        self._execute_write(
            "RELATE $s->character_relation->$d SET relation=$r, since_chapter=$sc, note=$n",
            {"s": RecordID("character", sl), "d": RecordID("character", dl),
             "r": relation, "sc": since_chapter, "n": note})

    def relations_at(self, chapter: int) -> list[dict]:
        """某章已建立的角色关系(限知时间门:since_chapter <= chapter, until_chapter > chapter or NONE)"""
        return self._query(
            "SELECT meta::id(in) AS src, meta::id(out) AS dst, relation, since_chapter, "
            "until_chapter, note FROM character_relation "
            "WHERE since_chapter <= $ch AND (until_chapter IS NONE OR until_chapter > $ch)",
            {"ch": chapter})

    def evolve_relation(self, src_oid: str, dst_oid: str, new_relation: str,
                        since_chapter: int, note: str | None = None) -> None:
        """关系演变:关闭 src→dst 所有开区间关系,写入新关系。
        敌变友/师徒决裂等弧线均通过此方法表达。"""
        _, sl = _split(src_oid)
        _, dl = _split(dst_oid)
        # 1. 关闭所有仍开着的 src→dst 关系(until_chapter IS NONE)
        self._execute_write(
            "UPDATE character_relation SET until_chapter=$uc "
            "WHERE in=$s AND out=$d AND until_chapter IS NONE",
            {"uc": since_chapter,
             "s": RecordID("character", sl),
             "d": RecordID("character", dl)})
        # 2. 写入新关系
        self.add_character_relation(src_oid, dst_oid, new_relation, since_chapter, note)

    def end_relation(self, src_oid: str, dst_oid: str, until_chapter: int) -> None:
        """终止关系:设置 until_chapter,不新建替代关系。"""
        # R2.1: 验证 src/dst 实体存在
        if self.entity(src_oid) is None:
            raise ValueError(
                f"end_relation: src '{src_oid}' 不存在,无法终止不存在角色的关系。"
            )
        if self.entity(dst_oid) is None:
            raise ValueError(
                f"end_relation: dst '{dst_oid}' 不存在,无法终止不存在角色的关系。"
            )
        _, sl = _split(src_oid)
        _, dl = _split(dst_oid)
        self._execute_write(
            "UPDATE character_relation SET until_chapter=$uc "
            "WHERE in=$s AND out=$d AND until_chapter IS NONE",
            {"uc": until_chapter,
             "s": RecordID("character", sl),
             "d": RecordID("character", dl)})

    # --- 世界规则(层1 设定完整性)---
    def add_world_rule(self, name: str, category: str, source: str | None = None,
                       capabilities: list | None = None, cost: str | None = None,
                       limitations: list | None = None, exceptions: list | None = None,
                       scope: str = "global", established_chapter: int | None = None,
                       note: str | None = None) -> str:
        """添加/覆盖世界规则(同名幂等:先删后建)。返回规则名。"""
        self._execute_write("DELETE world_rule WHERE name=$n", {"n": name})
        self._execute_write(
            "CREATE world_rule SET name=$n, category=$cat, source=$src, "
            "capabilities=$caps, cost=$cost, limitations=$lims, exceptions=$excs, "
            "scope=$scp, established_chapter=$ec, note=$note",
            {"n": name, "cat": category, "src": source,
             "caps": capabilities or [], "cost": cost, "lims": limitations or [],
             "excs": exceptions or [], "scp": scope, "ec": established_chapter, "note": note})
        return name

    def list_world_rules(self, category: str | None = None) -> list[dict]:
        """列世界规则(可按类别过滤)。"""
        if category:
            return self._query("SELECT * FROM world_rule WHERE category=$cat", {"cat": category})
        return self._query("SELECT * FROM world_rule")

    def delete_world_rule(self, name: str) -> None:
        self._execute_write("DELETE world_rule WHERE name=$n", {"n": name})

    # --- 势力/组织(层1)---
    def add_faction(self, name: str, ideology: str | None = None,
                    status: str = "active", leader: str | None = None,
                    known_members: list | None = None,
                    public_face: str | None = None,
                    private_operation: str | None = None,
                    first_mention_chapter: int | None = None,
                    private_operation_secret: bool = False) -> str:
        """添加/覆盖势力(同名幂等:先删后建)。返回势力名。"""
        self._execute_write("DELETE faction WHERE name=$n", {"n": name})
        self._execute_write(
            "CREATE faction SET name=$n, ideology=$ideo, status=$st, leader=$ldr, "
            "known_members=$km, public_face=$pf, private_operation=$po, "
            "first_mention_chapter=$fmc, private_operation_secret=$pos",
            {"n": name, "ideo": ideology, "st": status, "ldr": leader,
             "km": known_members or [], "pf": public_face, "po": private_operation,
             "fmc": first_mention_chapter, "pos": private_operation_secret})
        return name

    def list_factions(self) -> list[dict]:
        return self._query("SELECT * FROM faction")

    def delete_faction(self, name: str) -> None:
        self._execute_write("DELETE faction WHERE name=$n", {"n": name})

    # --- 角色弧光时间线(层3 动静结合)---
    def add_char_state(self, character_id: str, chapter: int, change_type: str,
                       summary: str, before_state: dict | None = None,
                       after_state: dict | None = None, trigger_event: str | None = None,
                       arc_phase: str | None = None, affects_voice: bool | None = None,
                       confidence: str = "confirmed",
                       ingest_seq: int | None = None,
                       lie_belief: int | None = None) -> None:
        """记录角色弧光质变点(能力/关系/性格变化)。
        affects_voice=True 时自动创建 voice_evolution_flag(该更新声音了)。
        ingest_seq:由 ingest 自动回写时传入,供 purge_ingest 幂等清理;手动种的不传。
        lie_belief:该章结束时对核心错误信念的信奉度(0-100,migration 054);
        钳制由调用方负责(ingest 抽取路径入库前 clamp 到 [0,100])。"""
        _, local = _split(character_id)
        self._execute_write(
            "CREATE char_state SET character_id=$cid, chapter=$ch, change_type=$ct, "
            "summary=$sum, before_state=$bs, after_state=$as, trigger_event=$te, "
            "arc_phase=$ap, affects_voice=$av, confidence=$conf, lie_belief=$lb"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"cid": character_id, "ch": chapter, "ct": change_type, "sum": summary,
             "bs": before_state, "as": after_state, "te": trigger_event,
             "ap": arc_phase, "av": affects_voice, "conf": confidence, "lb": lie_belief,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        if affects_voice:
            # 审计 C-2:透传 ingest_seq——ingest 路径产的 flag 随 purge 幂等,手动的保留
            self.add_voice_flag(character_id, chapter, summary, ingest_seq=ingest_seq)

    def char_state_at(self, character_id: str, chapter: int) -> dict:
        """返回角色在某章时刻的完整状态快照(合并所有 CharState 到该章)。"""
        rows = self._query(
            "SELECT * FROM char_state WHERE character_id=$cid AND chapter <= $ch "
            "ORDER BY chapter ASC", {"cid": character_id, "ch": chapter})
        if not rows:
            return {"character_id": character_id, "as_of_chapter": chapter,
                    "abilities": {}, "relations": {}, "personality": "", "arc_phases": []}
        abilities = {}
        relations = {}
        personality = ""
        phases = []
        for r in rows:
            after = r.get("after_state") or {}
            if r["change_type"] in ("ability", "composite"):
                abilities.update(after.get("ability_snapshot") or {})
            if r["change_type"] in ("relation", "composite"):
                relations.update(after.get("relation_snapshot") or {})
            if r["change_type"] in ("personality", "composite"):
                personality = after.get("personality_snapshot") or personality
            if r.get("arc_phase"):
                phases.append({"chapter": r["chapter"], "phase": r["arc_phase"],
                               "summary": r.get("summary", "")})
        return {"character_id": character_id, "as_of_chapter": chapter,
                "abilities": abilities, "relations": relations,
                "personality": personality, "arc_phases": phases}

    def list_char_states(self, character_id: str) -> list[dict]:
        """列角色全部弧光记录(含 before/after/trigger,演进史完整展示)。"""
        return self._query(
            "SELECT meta::id(id) AS id, character_id, chapter, change_type, summary, "
            "before_state, after_state, trigger_event, arc_phase, affects_voice, confidence, "
            "lie_belief "
            "FROM char_state WHERE character_id=$cid ORDER BY chapter ASC",
            {"cid": character_id})

    # --- 角色弧光静态锚 + arc_plan 里程碑(migration 054)---
    def set_char_anchors(self, character_id: str, anchors: dict) -> None:
        """写角色弧光锚。局部更新:只写传入的键,未传的字段不动;
        键限 _ANCHOR_KEYS 白名单(SET 片段来自常量元组,注入安全)。"""
        sets, vars_ = [], {}
        for k in _ANCHOR_KEYS:
            if k in anchors:
                sets.append(f"{k}=${k}")
                vars_[k] = anchors[k]
        if not sets:
            return
        _, local = _split(character_id)
        vars_["_l"] = local
        self._execute_write(
            f"UPDATE type::record('character',$_l) SET {', '.join(sets)}", vars_)

    def char_anchors(self, character_id: str) -> dict:
        """读单角色的弧光锚(七键)。角色不存在返回 {}。"""
        _, local = _split(character_id)
        rows = self._query(
            "SELECT ghost, lie, truth, want, need, arc_type, private_agenda "
            "FROM type::record('character',$_l)", {"_l": local})
        return rows[0] if rows else {}

    def add_arc_beat(self, character_id: str, beat_name: str, target_chapter: int,
                     lie_belief_target: int | None = None, trigger_event: str = "") -> None:
        """加一条弧光里程碑(beat):目标章 + 该拍应到达的 lie 信奉度 + 触发事件。"""
        self._execute_write(
            "CREATE arc_plan SET character_id=$c, beat_name=$b, target_chapter=$t, "
            "lie_belief_target=$lb, trigger_event=$te",
            {"c": character_id, "b": beat_name, "t": target_chapter,
             "lb": lie_belief_target, "te": trigger_event or None})

    def list_arc_plan(self, character_id: str) -> list[dict]:
        """角色的弧光里程碑,按 target_chapter 升序。"""
        return self._query(
            "SELECT meta::id(id) AS id, character_id, beat_name, target_chapter, "
            "lie_belief_target, trigger_event FROM arc_plan "
            "WHERE character_id=$c ORDER BY target_chapter ASC", {"c": character_id})

    def delete_arc_beat(self, beat_id: str) -> None:
        self._execute_write("DELETE type::record('arc_plan', $b)", {"b": beat_id})

    def latest_lie_belief(self, character_id: str, upto_chapter: int) -> int | None:
        """到某章为止最新的 lie 信奉度(char_state 里 chapter<=upto 且 lie_belief 非空的最新一条)。"""
        # SurrealDB 3.x:ORDER BY 字段必须出现在投影里,故连带 SELECT chapter
        rows = self._query(
            "SELECT lie_belief, chapter FROM char_state WHERE character_id=$c AND chapter<=$ch "
            "AND lie_belief IS NOT NONE ORDER BY chapter DESC LIMIT 1",
            {"c": character_id, "ch": upto_chapter})
        return rows[0]["lie_belief"] if rows else None

    def reverse_current_state(self, character_id: str) -> dict:
        """方案B任务24(story-import 逆向导入):对该角色 char_states 按 change_type 分组,
        各取 max(chapter) 的最新一条,合成「当前状态快照」——用于反推续写起点的角色当前态,
        与 char_state_at(锁定到某个既定章号)不同,这里没有"续写到第几章"的既定坐标,
        只关心"到目前为止最新是什么"。

        无状态角色(list_char_states 为空)返回 {}(不像 char_state_at 那样给空壳,
        逆向导入只关心"有没有可用状态",没有就是空,调用方据此判断是否需要人工补设定)。

        返回结构:
          - 每个出现过的 change_type 一个键,值为 {"chapter":最新章号,"summary":该条摘要,
            "after_state":该条 after_state}(该视图按 change_type 分组各取最新一条,
            用 latest_by_type 折叠即可——这里只关心"这一类型本身最新是什么",与
            "跨类型 chapter 全局序"无关);
          - 额外派生键(与 char_state_at 同范式,方便直接消费):
            abilities/relations/personality 分别聚合 ability/relation/personality/composite
            类型的 after_state;belief 类型的 lie_belief 提升为顶层 lie_belief 键。
            这些派生键必须照抄 char_state_at 的范式——对 list_char_states 返回的 rows
            (已按 chapter ASC 排序)直接顺序遍历、逐条 update 覆盖——因为 composite 与
            专项类型(如 ability)会写同一个键(如"剑术"),只有按全局 chapter 时间序
            遍历才能保证最终值是时间上最新的值;若先按 change_type 折叠
            (latest_by_type,dict 按首次插入序遍历)再合并,插入序较晚遍历到的旧类型
            会覆盖 chapter 实际更新的另一类型,产出过期值(B24 审查发现的正确性 bug)。
        """
        rows = self.list_char_states(character_id)
        if not rows:
            return {}
        latest_by_type: dict[str, dict] = {}
        for r in rows:
            latest_by_type[r["change_type"]] = r
        snapshot: dict = {}
        for ct, r in latest_by_type.items():
            after = r.get("after_state") or {}
            snapshot[ct] = {"chapter": r["chapter"], "summary": r.get("summary"),
                            "after_state": after or None}
        abilities: dict = {}
        relations: dict = {}
        personality = ""
        lie_belief = None
        for r in rows:
            ct = r["change_type"]
            after = r.get("after_state") or {}
            if ct in ("ability", "composite"):
                abilities.update(after.get("ability_snapshot") or {})
            if ct in ("relation", "composite"):
                relations.update(after.get("relation_snapshot") or {})
            if ct in ("personality", "composite"):
                p = after.get("personality_snapshot")
                if p:
                    personality = p
            if ct == "belief" and r.get("lie_belief") is not None:
                lie_belief = r["lie_belief"]
        if abilities:
            snapshot["abilities"] = abilities
        if relations:
            snapshot["relations"] = relations
        if personality:
            snapshot["personality"] = personality
        if lie_belief is not None:
            snapshot["lie_belief"] = lie_belief
        return snapshot

    # --- 设定完整性检查(层2 主编引导)---
    def setting_completeness(self) -> dict:
        """检查当前书的设定完整度,返回各维度缺项。"""
        chars = self.characters()
        rules = self.list_world_rules()
        factions = self.list_factions()
        places = self._query("SELECT * FROM place")
        facts = self.facts_at(99999)

        char_issues = []
        for c in chars:
            issues = []
            if not c.traits.get("backstory"):
                issues.append("缺前史/背景")
            if not c.traits.get("personality_tags"):
                issues.append("缺性格标签")
            if issues:
                char_issues.append({"name": c.name, "issues": issues})

        missing = []
        if not rules:
            missing.append("世界规则(魔法体系/物理法则/社会制度)")
        if not factions:
            missing.append("势力/组织")
        if not places:
            missing.append("地点/场景")
        if not any(f.secret for f in facts):
            missing.append("私密设定/伏线(角色隐藏底细)")

        return {
            "total_chars": len(chars),
            "total_rules": len(rules),
            "total_factions": len(factions),
            "total_places": len(places),
            "total_facts": len(facts),
            "char_issues": char_issues,
            "missing_dimensions": missing,
            "completeness_score": max(0, 100 - len(missing) * 20 - len(char_issues) * 5),
        }

    # --- VoiceProfile(声音指纹 9节,设计文档 §3.1.2)---
    def set_voice_profile(self, character_id: str, profile: dict) -> None:
        """设置角色声音指纹(9节结构:style_summary/catchphrases/sentence_patterns/
        vocabulary_profile/tone_rules/internal_monologue_style/ooc_signals/
        reference_lines/version)。"""
        _, local = _split(character_id)
        self._execute_write(
            "UPSERT type::record('voice_profile', $local) SET character_id=$cid, "
            "style_summary=$ss, catchphrases=$cp, sentence_patterns=$sp, "
            "vocabulary_profile=$vp, tone_rules=$tr, internal_monologue_style=$im, "
            "ooc_signals=$os, reference_lines=$rl, version=$v",
            {"local": local, "cid": character_id,
             "ss": profile.get("style_summary"), "cp": profile.get("catchphrases"),
             "sp": profile.get("sentence_patterns"), "vp": profile.get("vocabulary_profile"),
             "tr": profile.get("tone_rules"), "im": profile.get("internal_monologue_style"),
             "os": profile.get("ooc_signals"), "rl": profile.get("reference_lines"),
             "v": profile.get("version", 1)})

    def get_voice_profile(self, character_id: str) -> dict | None:
        """获取角色声音指纹(9节)。"""
        _, local = _split(character_id)
        rows = self._query(
            "SELECT * FROM type::record('voice_profile', $local)", {"local": local})
        return rows[0] if rows else None

    def list_voice_profiles(self) -> list[dict]:
        """列出所有角色声音指纹的紧凑视图(用于 prompt 注入)。
        返回 [{character_id, style_summary, catchphrases, tone_rules}]。"""
        rows = self._query(
            "SELECT character_id, style_summary, catchphrases, tone_rules FROM voice_profile")
        return rows if rows else []

    def check_ooc(self, character_id: str, dialogue: str) -> list[dict]:
        """OOC 检测:对照 voice_profile.ooc_signals 规则列表扫描对话。
        返回违规列表 [{signal, line, severity}]。"""
        vp = self.get_voice_profile(character_id)
        if not vp or not vp.get("ooc_signals"):
            return []
        violations = []
        for signal in vp["ooc_signals"]:
            if not isinstance(signal, dict):
                continue
            desc = signal.get("description", "")
            severity = signal.get("severity", "medium")
            method = signal.get("detection_method", "rule")
            if method == "rule":
                if "长句" in desc:
                    sentences = [s for s in dialogue.split("。") if s.strip()]
                    long_count = sum(1 for s in sentences if len(s.strip()) > 25)
                    if long_count > 3:
                        violations.append({"signal": desc, "severity": severity,
                                           "line": f"连续{long_count}句长句(>25字)"})
                elif "感叹号" in desc:
                    if dialogue.count("！") > 2:
                        violations.append({"signal": desc, "severity": severity,
                                           "line": f"感叹号{dialogue.count('！')}次"})
                elif "情感词" in desc or "直接说" in desc or "高兴" in desc or "我爱你" in desc:
                    emo_words = ["很高兴", "我爱你", "感谢", "很开心", "太好了"]
                    found = [w for w in emo_words if w in dialogue]
                    if found:
                        violations.append({"signal": desc, "severity": severity,
                                           "line": f"直接情感词: {found}"})
        return violations

    # --- item(物品/道具,设计文档 §3.1.4)---
    def add_item(self, name: str, category: str | None = None,
                 description: str | None = None, current_owner: str | None = None,
                 symbolic_state: str = "active",
                 special_properties: list | None = None,
                 first_chapter: int | None = None,
                 state_history: list | None = None) -> str:
        """添加/覆盖物品(同名幂等:先删后建)。返回物品名。
        state_history:P1-9——DELETE+CREATE 覆盖会清空状态流转史;端点层 PATCH 语义读回旧
        state_history 经此参数透传保留(缺省 None → [] 供全新物品)。"""
        self._execute_write("DELETE item WHERE name=$n", {"n": name})
        self._execute_write(
            "CREATE item SET name=$n, category=$cat, description=$desc, "
            "current_owner=$co, symbolic_state=$ss, state_history=$sh, "
            "special_properties=$sp, first_chapter=$fc",
            {"n": name, "cat": category, "desc": description, "co": current_owner,
             "ss": symbolic_state, "sh": state_history or [],
             "sp": special_properties or [], "fc": first_chapter})
        return name

    def list_items(self, state: str | None = None) -> list[dict]:
        if state:
            return self._query("SELECT * FROM item WHERE symbolic_state=$st", {"st": state})
        return self._query("SELECT * FROM item")

    def update_item_state(self, name: str, new_state: str, chapter: int,
                          note: str = "") -> None:
        """更新物品符号状态(active/lost/destroyed/unknown),追加 state_history。"""
        self._execute_write(
            "UPDATE item SET symbolic_state=$ns, state_history = "
            "array::append(state_history, {state:$ns, chapter:$ch, note:$note}) "
            "WHERE name=$n",
            {"ns": new_state, "ch": chapter, "note": note, "n": name})

    def delete_item(self, name: str) -> None:
        self._execute_write("DELETE item WHERE name=$n", {"n": name})

    # --- term(专有名词/术语,设计文档 §3.1.4)---
    def add_term(self, name: str, category: str | None = None,
                 definition: str | None = None, aliases: list | None = None,
                 first_mention_chapter: int | None = None) -> str:
        """添加/覆盖术语(同名幂等:先删后建)。返回术语名。"""
        self._execute_write("DELETE term WHERE name=$n", {"n": name})
        self._execute_write(
            "CREATE term SET name=$n, category=$cat, definition=$def, "
            "aliases=$al, first_mention_chapter=$fmc",
            {"n": name, "cat": category, "def": definition,
             "al": aliases or [], "fmc": first_mention_chapter})
        return name

    def list_terms(self) -> list[dict]:
        return self._query("SELECT * FROM term")

    def delete_term(self, name: str) -> None:
        self._execute_write("DELETE term WHERE name=$n", {"n": name})

    # --- resolveEntities(精确名/别名匹配,设计文档 §3.3)---
    def resolve_entities(self, text: str, chapter: int = 9999) -> list[dict]:
        """解析文本中出现的实体引用,返回相关设定候选。
        四路召回:精确名 → 别名 → hint → 向量语义。"""
        candidates = {}

        # 路1:精确名匹配(角色名/物品名/术语名/地点名)
        for c in self.characters():
            if c.name and c.name in text:
                candidates[c.id] = {"id": c.id, "type": "character", "name": c.name,
                                    "score": 1.0, "reason": "exact_name"}
        for item in self.list_items():
            if item.get("name") and item["name"] in text:
                candidates[f"item:{item['name']}"] = {"id": f"item:{item['name']}",
                    "type": "item", "name": item["name"], "score": 1.0, "reason": "exact_name"}
        for term in self.list_terms():
            if term.get("name") and term["name"] in text:
                candidates[f"term:{term['name']}"] = {"id": f"term:{term['name']}",
                    "type": "term", "name": term["name"], "score": 1.0, "reason": "exact_name"}

        # 路2:别名匹配
        for c in self.characters():
            aliases = c.traits.get("aliases") or []
            for alias in aliases:
                if alias and alias in text:
                    if c.id not in candidates:
                        candidates[c.id] = {"id": c.id, "type": "character",
                            "name": c.name, "score": 0.9, "reason": "alias",
                            "matched_alias": alias}
        for term in self.list_terms():
            for alias in (term.get("aliases") or []):
                if alias and alias in text:
                    key = f"term:{term['name']}"
                    if key not in candidates:
                        candidates[key] = {"id": key, "type": "term",
                            "name": term["name"], "score": 0.9, "reason": "alias",
                            "matched_alias": alias}

        # 路3:向量语义(仅当精确+别名 < 15)
        if len(candidates) < 15:
            try:
                for f in self.semantic_recall(text, k=10):
                    if f.id not in candidates:
                        candidates[f.id] = {"id": f.id, "type": "fact",
                            "name": f.attribute, "score": 0.7, "reason": "embedding"}
            except Exception:
                pass

        return sorted(candidates.values(), key=lambda x: -x["score"])

    # --- validate(设定校验,设计文档 §3.4)---
    def validate_setting(self, chapter: int, prose: str) -> list[dict]:
        """设定校验:比对正文与设定圣经,产出冲突线索。
        覆盖:规则违反/OOC/物品状态矛盾/命名不一致(能力矛盾未实现,归检测器扩展)。"""
        hints = []

        # 1. 物品状态校验:destroyed/lost 的物品不应在正文中被使用
        for item in self.list_items():
            state = item.get("symbolic_state", "active")
            if state in ("lost", "destroyed") and item["name"] in prose:
                hints.append({
                    "type": "item_state_inconsistency", "severity": "high",
                    "entity": item["name"], "description": f"物品「{item['name']}」状态为「{state}」但正文出现使用",
                    "evidence": item["name"]})

        # 2. OOC 校验:对每个有 voice_profile 的角色检测对话
        for c in self.characters():
            vp = self.get_voice_profile(c.id)
            if vp and vp.get("ooc_signals"):
                # 简单提取含角色名的句子作为对话
                sentences = [s.strip() for s in prose.split("。") if c.name in s]
                dialogue = "。".join(sentences)
                if dialogue:
                    ooc_violations = self.check_ooc(c.id, dialogue)
                    for v in ooc_violations:
                        hints.append({
                            "type": "personality_ooc", "severity": v["severity"],
                            "entity": c.name, "description": v["signal"],
                            "evidence": v["line"]})

        # 3. 世界规则校验:检查 limitations 是否被违反
        for rule in self.list_world_rules():
            for lim in (rule.get("limitations") or []):
                # 简单检查:limitation 关键词出现在正文中
                if lim and len(lim) > 4 and lim[:4] in prose:
                    hints.append({
                        "type": "rule_violation", "severity": "medium",
                        "entity": rule["name"], "description": f"可能违反规则「{rule['name']}」限制:{lim}",
                        "evidence": lim})

        # 4. 命名一致性:扫正文中疑似专名(人/地/物),未登记的报 hint
        # P2-a Fix3(选①):原 known_names 构建完未用就 return,属死代码——实装扫描逻辑。
        known_names = set()
        for c in self.characters():
            known_names.add(c.name)
            known_names.update(c.traits.get("aliases") or [])
        for term in self.list_terms():
            known_names.add(term["name"])
            known_names.update(term.get("aliases") or [])
        for it in self.list_items():
            known_names.add(it["name"])
        for pl in self._query("SELECT name FROM place"):
            known_names.add(pl.get("name", ""))
        known_names.discard("")
        try:
            import jieba
            # 切词后取长度>=2 的汉字 token,若与 known_names 的某项高度相似但不完全匹配则报 hint
            # 简单策略:正文中出现的已知名称的前缀/后缀变体(疑似别名)被捕获
            tokens = [w for w in jieba.cut(prose) if len(w) >= 2 and all("一" <= c <= "鿿" for c in w)]
            for tok in set(tokens):
                # 若该 token 不在 known_names,且正文含量>1(排除偶发音),则报 unknown_name hint
                if tok not in known_names and prose.count(tok) >= 2:
                    # 避免过度噪声:只在与任一已知名同首字或同尾字时才报(疑似衍生别名)
                    is_derived = any(
                        (kn[0] == tok[0] or kn[-1] == tok[-1])
                        for kn in known_names if len(kn) >= 2
                    )
                    if is_derived:
                        hints.append({
                            "type": "unknown_name", "severity": "low",
                            "entity": tok,
                            "description": f"「{tok}」出现 {prose.count(tok)} 次但未登记为角色/术语/地点/物品",
                            "evidence": tok})
        except Exception:
            pass  # jieba 不可用时静默跳过,不阻塞校验

        return hints

    def validate_event_colocation(self, chapter: int) -> list[dict]:
        """遗留处置批次三:同章同主体多地事件 hint(纯结构查询,report-only)。
        story_time/story_chapter 是章粒度——双地可能有合法移动衔接,故 severity=low
        且 note 明示人工确认;永不进 blocking。"""
        by_subj: dict[str, set] = {}
        for ev in self.events_at(chapter):
            subj = (ev.participants or {}).get("SUBJ")
            if subj and ev.location:
                by_subj.setdefault(str(subj), set()).add(str(ev.location))
        hints: list[dict] = []
        for subj, locs in sorted(by_subj.items()):
            if len(locs) >= 2:
                ls = sorted(locs)
                hints.append({
                    "type": "event_colocation", "severity": "low",
                    "subject": subj, "locations": ls,
                    "note": (f"同章主体 {subj} 的事件分布在 {len(ls)} 个地点"
                             f"({'、'.join(ls)});story_time 为章粒度,可能有移动"
                             f"衔接,请人工确认时间线")})
        return hints

    def lie_belief_jumps(self, threshold: int = 15) -> list[dict]:
        """弧光跳变(工艺引擎 M3 检测半件,pulse arc 维数据源):同一角色相邻两次
        lie_belief 记录位移>threshold → 顿悟太便宜。纯结构查询,report-only。"""
        rows = self._query(
            "SELECT character_id, chapter, lie_belief FROM char_state "
            "WHERE lie_belief != NONE ORDER BY character_id, chapter")
        out: list[dict] = []
        prev: dict = {}
        for r in rows:
            cid = str(r.get("character_id"))
            lb = r.get("lie_belief")
            if lb is None:
                continue
            p = prev.get(cid)
            ch = r.get("chapter")
            if p is not None and ch == p["chapter"]:
                # 审查 P1-4:同章多记录(重复 ingest 残留)不构成"跳变对",取后值为准
                prev[cid] = {"lie_belief": lb, "chapter": ch}
                continue
            if p is not None and abs(lb - p["lie_belief"]) > threshold:
                out.append({"character_id": cid, "chapter": ch,
                            "cur": lb, "prev": p["lie_belief"],
                            "prev_chapter": p["chapter"],
                            "gap": (ch or 0) - (p["chapter"] or 0)})
            prev[cid] = {"lie_belief": lb, "chapter": ch}
        return out

    def latest_version_prose(self, seq: int, kind: str) -> str | None:
        """某章某 kind 最新版本的正文(审计 P2-1:final 版同稿去重的比对源)。"""
        rows = self._query(
            "SELECT prose, created_at FROM chapter_version WHERE seq=$s AND kind=$k "
            "ORDER BY created_at DESC LIMIT 1", {"s": seq, "k": kind})
        return rows[0].get("prose") if rows else None

    def validate_cross_chapter_consistency(self) -> list[dict]:
        """跨章一致性检测(带指纹缓存壳)。审计 P2-13:每次 /post-check 全书扫太贵,
        以 (章数, Σqc_word_count) 为指纹——正文未变直接回缓存;指纹是弱哈希
        (同字数改动漏检),一致性 hint 是 advisory 级,可接受,存稿即失效重扫。"""
        count_rows = self._query("SELECT count() AS n FROM chapter GROUP ALL")
        word_rows = self._query(
            "SELECT math::sum(qc_word_count) AS w FROM chapter GROUP ALL")
        fp = (((count_rows[0].get("n") if count_rows else 0) or 0),
              ((word_rows[0].get("w") if word_rows else 0) or 0))
        cached = getattr(self, "_cc_cache", None)
        if cached and cached[0] == fp:
            return cached[1]
        hints = self._validate_cross_chapter_impl()
        self._cc_cache = (fp, hints)
        return hints

    def _validate_cross_chapter_impl(self) -> list[dict]:
        """跨章一致性检测(全书扫描)。

        返回 hint 列表(与 validate_setting 同结构),包含:
          (a) numeric_inconsistency —— 同一专名实体在不同章绑定不同数字(如「潭家二十七口」vs「潭家三百一十七口」)
          (b) unregistered_name     —— 高频疑似专名(≥3次)但未在 characters/terms/factions/items 中登记

        不修改任何状态,可安全重复调用。向后兼容:不影响原 validate_setting 签名。
        """
        import re

        hints: list[dict] = []

        # ── 收集全书章正文 ──────────────────────────────────────────────────
        chapters = self._query("SELECT seq, prose FROM chapter:.. ORDER BY seq")
        chapters = [c for c in chapters if c.get("prose")]
        if not chapters:
            return hints

        # ── 构建已登记专名集合(同 validate_setting §4 段) ─────────────────
        known_names: set[str] = set()
        for c in self.characters():
            known_names.add(c.name)
            known_names.update(c.traits.get("aliases") or [])
        for term in self.list_terms():
            known_names.add(term["name"])
            known_names.update(term.get("aliases") or [])
        for it in self.list_items():
            known_names.add(it["name"])
        for pl in self._query("SELECT name FROM place"):
            known_names.add(pl.get("name", ""))
        for fc in self.list_factions():
            known_names.add(fc["name"])
            # faction.aliases:疑似死(P2-15)——faction 无 aliases schema/写入路径(add_faction 不写),
            #   此 get 恒空,为前瞻性防御读;isinstance 守卫使其无害,保留守卫待确认。
            known_names.update(fc.get("aliases") or [] if isinstance(fc.get("aliases"), list) else [])
        known_names.discard("")

        # ── (a) 数字声明矛盾检测 ────────────────────────────────────────────
        # 策略:抽取「<专名>…<数字><量词单位>」三元组,
        #       只有【同一专名 + 同一量词单位 + 不同数字】才报 numeric_inconsistency。
        # 量词单位取数字紧跟的1-2字(须在已定义单位集内);否则单位为空串""。
        # 这样 "三十出头"(单位"") 与 "二十年前"(单位"年") 单位不同,不报矛盾。
        _HANZI_DIGITS = "零一二三四五六七八九十百千万亿两"
        _NUM_PAT = rf"[{_HANZI_DIGITS}]+|\d+"
        # 标准量词集合:实物计量单位
        _UNITS: set[str] = {
            "口", "枚", "颗", "人", "名", "位", "座", "条", "件", "个",
            "匹", "张", "把", "支", "根", "块", "面", "载", "年", "日",
            "月", "天", "两", "石", "斤", "尺", "丈", "里", "里",
        }
        # 2字复合量词(精确匹配优先于1字)
        _UNITS2: set[str] = {"年前", "年后", "天前", "天后", "日前", "日后"}

        def _extract_unit(text_after_num: str) -> str:
            """从数字后面的文本提取量词单位(1-2字);不在单位集内则返回空串。"""
            if not text_after_num:
                return ""
            # 优先尝试2字复合量词
            two = text_after_num[:2] if len(text_after_num) >= 2 else ""
            if two in _UNITS2:
                return two
            # 再尝试1字
            one = text_after_num[0] if text_after_num else ""
            if one in _UNITS:
                return one
            return ""

        # entity_nums: {entity_name: [(chapter_seq, number_str, unit_str, snippet), ...]}
        entity_nums: dict[str, list[tuple[int, str, str, str]]] = {}

        for ch in chapters:
            seq = ch["seq"]
            prose = ch["prose"]
            for name in known_names:
                if not name or name not in prose:
                    continue
                for m in re.finditer(re.escape(name), prose):
                    # 取专名右侧30字内的数字
                    window = prose[m.end(): m.end() + 30]
                    num_m = re.search(_NUM_PAT, window)
                    if num_m:
                        num_str = num_m.group()
                        # 过滤纯单字汉字数字「一」「二」等噪声(需≥2字或为阿拉伯数字)
                        if len(num_str) < 2 and not num_str.isdigit():
                            continue
                        # 提取数字后面的量词单位
                        after_num = window[num_m.end():]
                        unit = _extract_unit(after_num)
                        snippet = prose[max(0, m.start() - 2): m.end() + num_m.end() + 4]
                        entity_nums.setdefault(name, []).append((seq, num_str, unit, snippet))

        for name, occurrences in entity_nums.items():
            if len(occurrences) < 2:
                continue
            # 按(量词单位, 数字)聚合:只对同一单位下的不同数字报矛盾
            # unit_seen: {unit_str: {num_str: [(seq, snippet), ...]}}
            unit_seen: dict[str, dict[str, list[tuple[int, str]]]] = {}
            for seq, num_str, unit, snippet in occurrences:
                unit_seen.setdefault(unit, {}).setdefault(num_str, []).append((seq, snippet))

            for unit, num_map in unit_seen.items():
                if len(num_map) < 2:
                    continue  # 同单位下数字都一样,无矛盾
                # 找出现次数最多的两个数字(最典型矛盾对)
                sorted_nums = sorted(num_map.items(), key=lambda x: -len(x[1]))
                num_a, locs_a = sorted_nums[0]
                num_b, locs_b = sorted_nums[1]
                ch_a = locs_a[0][0]
                ch_b = locs_b[0][0]
                snip_a = locs_a[0][1]
                snip_b = locs_b[0][1]
                unit_label = f"(量词:{unit})" if unit else ""
                hints.append({
                    "type": "numeric_inconsistency",
                    "severity": "high",
                    "entity": name,
                    "description": (
                        f"「{name}」数字前后矛盾{unit_label}:"
                        f"第{ch_a}章「{num_a}」vs 第{ch_b}章「{num_b}」"
                    ),
                    "evidence": {
                        f"第{ch_a}章": snip_a,
                        f"第{ch_b}章": snip_b,
                    },
                })

        # ── (b) 未登记高频疑似专名检测(收紧版) ─────────────────────────────
        # 只报【出现≥5次】且【与已知专名共享≥2个连续汉字(含子串)】的词——
        # 疑似命名漂移/别名(如"潭家"已登记但出现"潭家府")。
        # 纯独立新词、常用词、已知专名的纯前/后缀词一律不报。
        # 选择选项A:精准收紧,宁可漏报也不滥报。
        all_prose = "".join(c["prose"] for c in chapters)

        # 提取所有2-4字汉字词组(滑动窗口,排除标点/空格)
        hanzi_only = re.sub(r"[^一-鿿]", " ", all_prose)
        candidate_counts: dict[str, int] = {}
        for length in (2, 3, 4):
            tokens = re.findall(rf"[一-鿿]{{{length}}}", hanzi_only)
            for tok in tokens:
                candidate_counts[tok] = candidate_counts.get(tok, 0) + 1

        # 常见虚词/停用词/助词排除
        _STOPWORDS = {
            "这个", "那个", "什么", "如何", "为何", "因为", "所以", "虽然", "但是",
            "他们", "我们", "你们", "她们", "已经", "可以", "没有", "一个", "一些",
            "这样", "那样", "只是", "还是", "就是", "于是", "不是", "都是", "的是",
            "时候", "地方", "事情", "东西", "问题", "方面", "情况", "之后", "之前",
            "之中", "之间", "之上", "之下", "以上", "以下", "以前", "以后", "一直",
            "一边", "一起", "一般", "一样", "一切", "一定", "一旦", "如此", "这里",
            "那里", "这时", "那时", "其中", "其他", "其实", "不过", "不知", "不得",
            "只有", "只能", "只好", "不禁", "不由", "不觉", "不得不", "不由得",
            "看见", "走过", "想起", "回头", "逃散", "走来", "说道", "点头", "摇头",
            "百姓", "街道", "门楼", "石板", "月光", "夜色", "空院", "往日", "五味",
        }

        reported: set[str] = set()
        for tok, cnt in candidate_counts.items():
            if tok in known_names or tok in _STOPWORDS:
                continue
            if tok in reported:
                continue

            if not known_names:
                # 无已登记专名时:退回原始行为,高频(≥3次)词即报
                if cnt >= 3:
                    hints.append({
                        "type": "unregistered_name",
                        "severity": "low",
                        "entity": tok,
                        "description": (
                            f"「{tok}」全书出现 {cnt} 次但未登记为角色/术语/地点/阵营/物品"
                        ),
                        "evidence": tok,
                    })
                    reported.add(tok)
                continue

            # ── 有已登记专名时:大幅收紧,只报疑似命名漂移 ──────────────────
            # 门槛提高到≥5次
            if cnt < 5:
                continue
            # 排除:tok 是已知专名的直接超集(专名+助词/动词,如"潭家的"、"柳三更走")
            if any(kn in tok for kn in known_names if len(kn) >= 2):
                continue
            # 排除:tok 是已知专名的严格子串(截断词,如"柳三"是"柳三更"的前缀)
            if any(tok in kn for kn in known_names if len(kn) > len(tok)):
                continue
            # 疑似命名漂移:tok 与某已知专名共享≥2个连续汉字但互不包含
            # (如"潭家"已登记,"潭府"出现 → 疑似别名)
            is_derived = any(
                len(kn) >= 2 and any(
                    kn[i:i+2] in tok
                    for i in range(len(kn) - 1)
                )
                for kn in known_names
            )
            if is_derived:
                hints.append({
                    "type": "unregistered_name",
                    "severity": "low",
                    "entity": tok,
                    "description": (
                        f"「{tok}」全书出现 {cnt} 次但未登记为角色/术语/地点/阵营/物品"
                        "(疑似已登记专名的别名/命名漂移)"
                    ),
                    "evidence": tok,
                })
                reported.add(tok)

        return hints

    # --- 大纲/卷章树(手稿支数据层,作者工具 F-01 后端)---

    # == 卷 CRUD ==

    def add_volume(self, title: str, sort_order: int = 0,
                   intro: str | None = None, color: str | None = None) -> str:
        """新建卷,返回裸 id(SurrealDB 自动生成)。"""
        vid = self._query(
            "CREATE volume CONTENT $c",
            {"c": {"title": title, "sort_order": sort_order,
                   "intro": intro, "color": color}}
        )
        # CREATE 返回 [{"id": RecordID(...), ...}]
        row = vid[0] if vid else {}
        rid = row.get("id")
        if rid is None:
            raise RuntimeError("add_volume: CREATE 未返回 id")
        # RecordID → 裸 id 字符串
        return str(rid).split(":")[-1] if ":" in str(rid) else str(rid)

    def list_volumes(self) -> list[dict]:
        """按 sort_order 升序列所有卷。"""
        rows = self._query(
            "SELECT meta::id(id) AS id, title, sort_order, intro, color "
            "FROM volume ORDER BY sort_order")
        return rows

    def update_volume(self, vid: str, fields: dict) -> bool:
        """更新卷字段(title/sort_order/intro/color 白名单)。返回 True 若存在,False 若不存在。"""
        rows = self._query("SELECT id FROM type::record('volume',$vid) LIMIT 1", {"vid": vid})
        if not rows:
            return False
        allowed = {"title", "sort_order", "intro", "color"}
        payload = {k: v for k, v in fields.items() if k in allowed}
        if not payload:
            return True
        sets = ", ".join(f"{k}=$p_{k}" for k in payload)
        params = {f"p_{k}": v for k, v in payload.items()}
        self._execute_write(
            f"UPDATE type::record('volume', $vid) SET {sets}",
            {"vid": vid, **params})
        return True

    def delete_volume(self, vid: str) -> bool:
        """删卷:先把该卷下所有章的 volume 置 NONE(不删章),再删卷记录。返回 True 若存在并删除,False 若不存在。"""
        rows = self._query("SELECT id FROM type::record('volume',$vid) LIMIT 1", {"vid": vid})
        if not rows:
            return False
        self._execute_write(
            "UPDATE chapter SET volume = NONE WHERE volume = type::record('volume', $vid)",
            {"vid": vid})
        self._execute_write(
            "DELETE type::record('volume', $vid)",
            {"vid": vid})
        return True

    def create_chapter(self, title: str = "", volume_id: str | None = None) -> dict:
        """创建一个空章节。

        seq 是故事时间轴主键,永不复用归档章号;volume_id 存在时把新章追加到该卷末尾。
        """
        if volume_id is not None:
            vcheck = self._query(
                "SELECT id FROM type::record('volume',$vid) LIMIT 1",
                {"vid": volume_id})
            if not vcheck:
                raise ValueError(f"create_chapter: volume '{volume_id}' 不存在")
        seq = self.max_chapter() + 1
        if seq < 1:
            seq = 1
        title = (title or "").strip() or f"第{seq}章"
        self.save_chapter(seq, "", title=title, focalizer=None)
        if volume_id is not None:
            rows = self._query(
                "SELECT seq, sort_order FROM chapter:.. "
                "WHERE archived != true AND volume = type::record('volume', $vid)",
                {"vid": volume_id})
            rows.sort(key=lambda r: (r.get("sort_order") if r.get("sort_order") is not None else r["seq"]))
            order = [r["seq"] for r in rows if r["seq"] != seq] + [seq]
            self.reorder_chapters(volume_id, order)
        return {"seq": seq, "title": title, "volume": volume_id}

    def archive_chapter(self, seq: int, reason: str = "") -> bool:
        """软删除章节:隐藏但保留正文、版本和所有引用。"""
        rows = self._query("SELECT seq FROM type::record('chapter', $seq)", {"seq": seq})
        if not rows:
            return False
        self._execute_write(
            "UPDATE type::record('chapter', $seq) SET archived=true, archived_at=time::now(), archive_reason=$reason",
            {"seq": seq, "reason": (reason or "").strip() or None})
        return True

    def restore_chapter(self, seq: int) -> bool:
        """恢复已归档章节。"""
        rows = self._query("SELECT seq FROM type::record('chapter', $seq)", {"seq": seq})
        if not rows:
            return False
        self._execute_write(
            "UPDATE type::record('chapter', $seq) SET archived=false, archived_at=NONE, archive_reason=NONE",
            {"seq": seq})
        return True

    def archived_chapters(self) -> list[dict]:
        """列出归档箱中的章节,只返回目录展示需要的轻量字段。"""
        rows = self._query(
            "SELECT seq, title, archived_at, archive_reason FROM chapter:.. "
            "WHERE archived = true ORDER BY seq")
        out = []
        for row in rows:
            seq = row.get("seq")
            out.append({
                "seq": seq,
                "title": row.get("title") or f"第{seq}章",
                "archived_at": str(row.get("archived_at") or ""),
                "archive_reason": row.get("archive_reason") or "",
            })
        return out

    def _safe_count(self, surql: str, vars: dict) -> int:
        try:
            rows = self._query(surql, vars)
        except Exception:
            return 0
        return int((rows[0].get("n") if rows else 0) or 0)

    def _chapter_impact_token(self, seq: int, references: list[dict]) -> str:
        raw = json.dumps(
            {"db": self.db_name, "type": "chapter", "seq": seq, "references": references},
            ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def chapter_lifecycle_impact(self, seq: int) -> dict | None:
        """章节永久删除前的影响清单。"""
        ch = self.get_chapter(seq)
        if not ch:
            return None
        refs = []
        prose_chars = len((ch.get("prose") or "").strip())
        if prose_chars:
            refs.append({"kind": "正文", "count": prose_chars})
        count_specs = [
            ("版本", "SELECT count() AS n FROM chapter_version WHERE seq=$seq GROUP ALL"),
            ("主编对话", "SELECT count() AS n FROM chat_message WHERE chapter=$seq GROUP ALL"),
            ("素材引用", "SELECT count() AS n FROM material_reference WHERE chapter=$seq GROUP ALL"),
            ("伏笔触及", "SELECT count() AS n FROM promise_touch WHERE chapter=$seq GROUP ALL"),
            ("母题触及", "SELECT count() AS n FROM motif_instance WHERE chapter=$seq GROUP ALL"),
            ("关系触碰", "SELECT count() AS n FROM relation_touch WHERE chapter=$seq GROUP ALL"),
            ("事件", "SELECT count() AS n FROM event WHERE story_chapter=$seq OR ingest_seq=$seq GROUP ALL"),
            ("角色状态", "SELECT count() AS n FROM char_state WHERE chapter=$seq OR ingest_seq=$seq GROUP ALL"),
            ("章级北极星", "SELECT count() AS n FROM chapter_scorecard WHERE seq=$seq GROUP ALL"),
        ]
        for kind, query in count_specs:
            n = self._safe_count(query, {"seq": seq})
            if n:
                refs.append({"kind": kind, "count": n})
        label = ch.get("title") or f"第{seq}章"
        return {
            "object": {"type": "chapter", "id": seq, "label": label},
            "references": refs,
            "recommended_action": "archive",
            "confirm_impact_token": self._chapter_impact_token(seq, refs),
        }

    def delete_chapter_permanent(self, seq: int) -> bool:
        """永久删除章节和明确以该章为 owner 的派生记录。危险操作,端点层必须 token 门禁。"""
        rows = self._query("SELECT seq FROM type::record('chapter', $seq)", {"seq": seq})
        if not rows:
            return False
        try:
            self.purge_ingest(seq)
        except Exception as e:
            logging.getLogger("scribe3.store").warning(
                "delete_chapter_permanent purge_ingest(%s) 失败,继续清章节本体: %s", seq, e)
        ev_ids = self._query(
            "SELECT VALUE id FROM event WHERE story_chapter=$seq OR ingest_seq=$seq",
            {"seq": seq})
        if ev_ids:
            self._execute_write("DELETE involves WHERE in IN $ids", {"ids": ev_ids})
            self._execute_write("DELETE causes WHERE in IN $ids", {"ids": ev_ids})
            self._execute_write("DELETE causal WHERE in IN $ids OR out IN $ids", {"ids": ev_ids})
            self._execute_write("DELETE event WHERE id IN $ids", {"ids": ev_ids})
        for query in [
            "DELETE chapter_version WHERE seq=$seq",
            "DELETE chapter_scorecard WHERE seq=$seq",
            "DELETE chat_message WHERE chapter=$seq",
            "DELETE material_reference WHERE chapter=$seq",
            "DELETE promise_touch WHERE chapter=$seq",
            "DELETE motif_instance WHERE chapter=$seq",
            "DELETE relation_touch WHERE chapter=$seq",
            "DELETE char_state WHERE chapter=$seq OR ingest_seq=$seq",
            "DELETE ingest_unverified WHERE seq=$seq",
            "DELETE voice_evolution_flag WHERE trigger_chapter=$seq OR ingest_seq=$seq",
            "DELETE lesson WHERE chapter=$seq",
            "DELETE distill_marker WHERE chapter=$seq",
        ]:
            try:
                self._execute_write(query, {"seq": seq})
            except Exception:
                pass
        self._execute_write("DELETE type::record('chapter', $seq)", {"seq": seq})
        return True

    # == 大纲聚合 ==

    def outline(self) -> dict:
        """聚合大纲:卷 + 章(梗概/字数/QC/视角/卷/标签 + 场景切分)。
        千万字基座(Phase0-BE1):**绝不 SELECT prose**——场景数/详情、QC 计数全读章级缓存列
        (scene_count / scene_meta / qc_issues / qc_causal,均由 save_chapter 写入)。
        存量章用 backfill_scalability_caches 回填缓存;未回填章缓存为 NONE,降级为 0/空。
        章按 sort_order 升序排列(sort_order 为 NONE 时回退 seq)。
        SurrealDB 不支持 ORDER BY (expr ?? expr) 括号形式,改在 Python 侧排序。
        """
        vols = self.list_volumes()
        rows = self._query(
            "SELECT seq, sort_order, title, synopsis, focalizer, "
            "(IF volume THEN meta::id(volume) ELSE NONE END) AS volume, label, "
            "qc_word_count AS word_count, qc_issues, qc_causal, qc_breakdown, "
            "scene_count, scene_meta "
            "FROM chapter:.. WHERE archived = NONE OR archived != true")
        # Python 侧排序:sort_order 为 None 时回退 seq
        rows.sort(key=lambda r: (r.get("sort_order") if r.get("sort_order") is not None else r["seq"]))
        import json
        chapters = []
        for r in rows:
            raw_meta = r.pop("scene_meta", None)
            try:
                meta = json.loads(raw_meta) if raw_meta else []
            except (ValueError, TypeError):
                meta = []
            # qc_breakdown 缓存为 JSON 串;解析失败/缺失降级为零拆分(字段恒在,向后兼容)。
            raw_bd = r.pop("qc_breakdown", None)
            try:
                breakdown = json.loads(raw_bd) if raw_bd else {}
            except (ValueError, TypeError):
                breakdown = {}
            breakdown = {k: breakdown.get(k, 0) for k in
                         ("repetition", "structural", "purple", "ai_tics", "oversaturation")}
            # scene_count 缓存优先;缺失(存量未回填)回退 scene_meta 长度,再不济 0。
            sc = r.get("scene_count")
            if sc is None:
                sc = len(meta)
            chapters.append({
                **r,
                "scene_count": sc,
                "qc_breakdown": breakdown,
                "scenes": [{"idx": i, "title": m.get("title", ""),
                            "char_count": m.get("char_count", 0)}
                           for i, m in enumerate(meta)],
            })
        unassigned = [c["seq"] for c in chapters if not c.get("volume")]
        return {"volumes": vols, "chapters": chapters, "unassigned_chapters": unassigned}

    # == 混合 Binder 项目树(只读统一投影,作者工具 F-06)==

    def project_tree(self) -> dict:
        """聚合左侧项目树:手稿支(卷→章→场景)+ 素材支(分类→条目)+ 横切视图清单。

        只读统一投影:复用 outline()/characters()/list_*() ,不新造存储。
        每个节点是 TreeNode {id, type, label, ref?, children?, badges?, meta?}。
        只搬「身份 + 角标」,不回正文/详情全字段(详情按 ref 懒加载)。
        """
        # —— 手稿支:复用 outline() ——
        out = self.outline()
        vols = out["volumes"]
        chapters = out["chapters"]
        # 卷 id → 该卷 TreeNode(保持 outline 的章顺序)
        vol_nodes: dict[str | None, dict] = {}

        def _wc_badge(n) -> dict:
            v = n or 0
            label = f"{v/1000:.1f}k" if v >= 1000 else str(v)
            return {"kind": "wc", "value": label}

        def _chapter_node(c: dict) -> dict:
            badges = [_wc_badge(c.get("word_count"))]
            if c.get("focalizer"):
                badges.append({"kind": "pov", "value": c["focalizer"]})
            qc_n = c.get("qc_issues") or 0
            if qc_n:
                badges.append({"kind": "qc", "value": qc_n, "tone": "warn"})
            scenes = c.get("scenes") or []
            node = {
                "id": f"ch:{c['seq']}", "type": "chapter",
                "label": f"{c['seq']} {c.get('title') or ''}".strip(),
                "ref": c["seq"],
                "meta": {"focalizer": c.get("focalizer"), "label": c.get("label")},
                "badges": badges,
            }
            if len(scenes) > 1:
                node["children"] = [
                    {"id": f"ch:{c['seq']}#scene:{s['idx']}", "type": "scene",
                     "label": s.get("title") or f"场景 {s['idx']}",
                     "ref": {"seq": c["seq"], "idx": s["idx"]},
                     "badges": [_wc_badge(s.get("char_count"))]}
                    for s in scenes
                ]
            return node

        # 预建卷节点(按 outline 卷顺序),外加未分卷兜底组
        for v in vols:
            vol_nodes[v["id"]] = {
                "id": f"vol:{v['id']}", "type": "volume",
                "label": v.get("title") or "未命名卷", "ref": v["id"],
                "children": [], "badges": [],
            }
        for c in chapters:
            vid = c.get("volume")
            if vid not in vol_nodes:
                # 未分卷兜底组(vid=None)
                vol_nodes.setdefault(None, {
                    "id": "vol:null", "type": "volume", "label": "未分卷",
                    "ref": None, "children": [], "badges": [],
                })
            vol_nodes[vid if vid in vol_nodes else None]["children"].append(_chapter_node(c))
        # 卷角标:章数 + 卷总字数
        vol_order = [v["id"] for v in vols] + ([None] if None in vol_nodes else [])
        manuscript_children = []
        for vid in vol_order:
            node = vol_nodes.get(vid)
            if node is None:
                continue
            ch_count = len(node["children"])
            node["badges"] = [{"kind": "count", "value": ch_count}]
            manuscript_children.append(node)

        manuscript = {
            "id": "manuscript_root", "type": "manuscript_root", "label": "手稿",
            "children": manuscript_children,
        }

        # —— 素材支:各分类 → 条目 ——
        def _cat(cat_type: str, label: str, items: list[dict],
                 leaf_type: str, name_key: str = "name",
                 ref_key: str = "name", meta_fn=None, badge_fn=None) -> dict:
            children = []
            for it in items:
                leaf = {
                    "id": f"{leaf_type}:{it.get(ref_key)}", "type": leaf_type,
                    "label": str(it.get(name_key) or it.get(ref_key) or "—"),
                    "ref": it.get(ref_key),
                }
                if meta_fn:
                    leaf["meta"] = meta_fn(it)
                if badge_fn:
                    b = badge_fn(it)
                    if b:
                        leaf["badges"] = b
                children.append(leaf)
            return {
                "id": f"cat:{cat_type}", "type": "codex_category", "label": label,
                "ref": cat_type, "badges": [{"kind": "count", "value": len(children)}],
                "children": children,
            }

        chars = self.characters()
        char_items = [{"name": c.name, "id": c.id, "local": c.id.split(":", 1)[-1],
                       "importance": c.traits.get("importance"),
                       "secret": bool(c.traits.get("backstory_secret"))}
                      for c in chars]

        def _char_meta(c):
            return {"importance": c.get("importance"), "id": c.get("id")}

        def _char_badge(c):
            return [{"kind": "secret", "tone": "faint"}] if c.get("secret") else None

        codex_children = [
            _cat("character", "角色", char_items, "character", ref_key="local",
                 meta_fn=_char_meta, badge_fn=_char_badge),
            _cat("faction", "势力", self.list_factions(), "faction"),
            _cat("item", "物件", self.list_items(), "item"),
            _cat("term", "术语", self.list_terms(), "term"),
            _cat("world_rule", "世界规则", self.list_world_rules(), "world_rule"),
            _cat("promise", "伏笔", self.list_promises(), "promise",
                 name_key="text", ref_key="id"),
            _cat("motif", "母题", self.list_motifs(), "motif", ref_key="id"),
        ]
        codex = {
            "id": "codex_root", "type": "codex_root", "label": "设定库",
            "children": codex_children,
        }

        # —— 素材库支(非正典材料,与设定库正典严格分开):kind 分类 → 素材条目 ——
        all_materials = self.list_materials()
        mat_kind_labels = [("research", "研究"), ("reference", "参考"),
                           ("snippet", "片段"), ("inspiration", "灵感"), ("note", "笔记"),
                           ("emotion_module", "情绪卡")]
        mat_children = []
        for k, label in mat_kind_labels:
            items = [m for m in all_materials if m.get("kind") == k]
            leaves = [{"id": f"material:{m['id']}", "type": "material",
                       "label": str(m.get("title") or "—"), "ref": m["id"],
                       "meta": {"kind": k}}
                      for m in items]
            mat_children.append({
                "id": f"matcat:{k}", "type": "material_category", "label": label,
                "ref": k, "badges": [{"kind": "count", "value": len(leaves)}],
                "children": leaves,
            })
        materials = {
            "id": "material_root", "type": "material_root", "label": "素材库",
            "children": mat_children,
        }

        # —— 横切视图(静态清单)——
        views = [
            {"id": "view:overview", "type": "view", "label": "概览"},
            {"id": "view:atlas", "type": "view", "label": "图谱"},
            {"id": "view:timeline", "type": "view", "label": "时间线"},
            {"id": "view:insight", "type": "view", "label": "仪表盘"},
            {"id": "view:progress", "type": "view", "label": "进度"},
        ]

        return {"manuscript": manuscript, "codex": codex,
                "materials": materials, "views": views}

    # == 章重排(只改 sort_order,绝不动 seq)==

    def reorder_chapters(self, volume_id: str | None, order: list[int]) -> int:
        """把 order 列表中各章的 sort_order 设为卷基址+i,并更新 volume 字段。
        seq 永远不动(故事时间轴主键)。
        P2-a Fix4: 卷基址由 *1000 改为 *100000——相当于二级排序键 (volume.sort_order, chapter_index),
        单卷支持至多 100000 章而不发生跨卷撞号;未分卷基址 = 0。
        R2.5: 若 volume_id 指定的卷不存在,抛 ValueError(防幽灵卷)。
        """
        base = 0
        if volume_id:
            vrows = self._query(
                "SELECT sort_order FROM type::record('volume', $vid)",
                {"vid": volume_id})
            if not vrows:
                raise ValueError(
                    f"reorder_chapters: volume '{volume_id}' 不存在,拒绝写入幽灵卷归属。"
                )
            base = vrows[0]["sort_order"] * 100000
        for i, seq in enumerate(order):
            if volume_id:
                # record<volume> 须用 type::record() 在 SurrealQL 里构造,不能传字符串
                self._execute_write(
                    "UPDATE type::record('chapter', $seq) SET sort_order=$o, "
                    "volume=type::record('volume', $vid)",
                    {"seq": seq, "o": base + i, "vid": volume_id})
            else:
                self._execute_write(
                    "UPDATE type::record('chapter', $seq) SET sort_order=$o, volume=NONE",
                    {"seq": seq, "o": base + i})
        return len(order)

    # == 章元数据 PATCH(不碰正文/embedding/qc)==

    def update_chapter_meta(self, seq: int, fields: dict) -> bool:
        """只改梗概/卷/标签/标题(白名单),不碰 prose/embedding/qc_*。
        返回 True 若章存在,False 若章不存在(404 判定由调用方处理)。
        """
        # 先确认章存在
        exists = self._query(
            "SELECT seq FROM type::record('chapter', $seq)", {"seq": seq})
        if not exists:
            return False
        allowed = {"synopsis", "volume", "label", "title", "beats",
                   "scene_truth", "involved_characters", "deductions",
                   "purpose_text", "deltas"}   # 北极星任务6:目的合同两字段
        # volume 需单独处理(record link 不能传字符串参数)
        volume_id = _UNSET  # 哨兵:区分"未传 volume"与"传了 None(清空)"
        plain: dict = {}
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k == "volume":
                volume_id = v   # None = 清空, str = 新卷裸 id
            elif k in ("beats", "involved_characters", "deductions", "deltas"):
                # list 字段存为 JSON 串(绕 SCHEMAFULL 嵌套校验,同 scene_meta);读时还原。
                import json
                plain[k] = json.dumps(v if v is not None else [], ensure_ascii=False)
            else:
                plain[k] = v
        # 构建 SET 子句:先处理普通字段,再追加 volume(若有)
        set_parts: list[str] = [f"{k}=$p_{k}" for k in plain]
        params: dict = {f"p_{k}": v for k, v in plain.items()}
        params["seq"] = seq
        if volume_id is not _UNSET:
            if volume_id is None:
                set_parts.append("volume=NONE")
            else:
                # R2.5: 校验目标卷存在,防幽灵卷
                vcheck = self._query(
                    "SELECT id FROM type::record('volume',$vid) LIMIT 1", {"vid": volume_id})
                if not vcheck:
                    raise ValueError(
                        f"update_chapter_meta: volume '{volume_id}' 不存在,拒绝写入幽灵卷归属。"
                    )
                set_parts.append("volume=type::record('volume', $p_volume)")
                params["p_volume"] = volume_id
        if not set_parts:
            return True
        self._execute_write(
            f"UPDATE type::record('chapter', $seq) SET {', '.join(set_parts)}",
            params)
        return True

    # == 统一上下文会话(Task 3:context_session / context_snapshot 的 CAS 原子存储)==
    #
    # 为什么不用 transaction() contextmanager:CAS 是"读-判-写"三步,必须在同一条
    # 多语句 SurrealQL 事务里完成(LET/IF/THROW),collect 式的 transaction() 只能拼
    # 纯写语句,表达不了条件分支——故直接手拼 BEGIN/COMMIT 走 _raw_query
    # (与 grant_public 同款写法)。

    # 快照统一取数列(<string> captured_at:datetime 序列化为 ISO 串,与 model_dump
    # mode="json" 的返回形状对齐)。如实说明:写路径(create/advance 的返回值)里的
    # captured_at 是 Python 墙钟,库内实际存的是 time::now()(READONLY),二者有
    # 微秒级差——captured_at 不参与 context_hash,指纹不受影响;读路径以库内值为准。
    _CONTEXT_SNAPSHOT_FIELDS = (
        "session_id, work, revision, previous_revision, navigation_id, thread_id, "
        "entry, directory_path, focus, detail_route, chapter, phase, focalizer, "
        "reason, context_hash, <string> captured_at AS captured_at")

    def _context_tx(self, surql: str, vars: dict) -> None:
        """执行多语句 CAS 事务并逐语句核对状态。

        为什么不走 _raw_query:surrealdb-py 的 query() 只检查【第一条】语句的
        status(2026-07-10 实测),事务里的 THROW / 唯一索引冲突全被静默吞掉——
        而 CAS 的失配/冲突信号正是靠这些错误传递,必须 query_raw 自查全部语句。
        连接类异常沿用 _raw_query 的"重连重试一次"策略:advance 场景下若首次
        已提交、响应丢失,重试的事务会先撞 stale THROW(IF 判定在 CREATE 之前)
        ——由上层"stale → 先按 navigation 读回 → 读不回才是真 stale"机制转为
        幂等读回;create 场景重试非幂等,见 create_context_session 说明。"""
        try:
            resp = self._db.query_raw(surql, vars)
        except _CONN_ERRORS as e:
            logging.getLogger("scribe3.store").warning(
                "SurrealDB 连接故障,重连后重试一次(%s): %s",
                type(e).__name__, str(e)[:120])
            self._reconnect()
            resp = self._db.query_raw(surql, vars)
        if resp.get("error"):
            raise RuntimeError(f"context 事务 RPC 错误: {resp['error']}")
        errs = [str(st.get("result")) for st in (resp.get("result") or [])
                if isinstance(st, dict) and st.get("status") == "ERR"]
        if errs:
            # 过滤连带失败的样板消息("was not executed due to"/"Cannot COMMIT"),
            # 留下第一现场(THROW 文本 / 索引冲突),供上层按消息分流
            real = [m for m in errs
                    if "not executed due to" not in m and "Cannot COMMIT" not in m]
            raise RuntimeError("; ".join(real or errs))

    @staticmethod
    def _classify_context_tx_error(msg: str) -> str:
        """把 CAS 事务错误文案分流为语义类别(单独成函数以便文本注入单测)。

        类别:stale(自家 THROW 的 revision 失配)/ session_missing / session_ended
        / unique_conflict(快照唯一索引)/ commit_conflict(SurrealDB 提交层
        读写冲突,乐观事务固有,语义同 CAS 失配请重试)/ unknown(原样上抛)。"""
        if "stale_revision:" in msg:
            return "stale"
        if "context_session_missing" in msg:
            return "session_missing"
        if "context_session_ended" in msg:
            return "session_ended"
        if "already contains" in msg or "context_snapshot_navigation" in msg \
                or "context_snapshot_session_revision" in msg:
            return "unique_conflict"
        if "read or write conflict" in msg or "write conflict" in msg \
                or "transaction can be retried" in msg:
            return "commit_conflict"
        return "unknown"

    def _warn_context_replay_mismatch(self, replay: dict, it: NavigationIntent) -> None:
        """M-1:同 navigation_id 视为重放,新 payload 被忽略(以先落库者为准)。
        payload 不一致说明前端错误复用了 navigation_id——留 warning 便于排查,
        但仍按幂等重放返回,不打断用户。"""
        focus_id = (replay.get("focus") or {}).get("id")
        if replay.get("detail_route") != it.detail_route or focus_id != it.focus.id:
            logging.getLogger("scribe3.store").warning(
                "advance_context: navigation_id=%s 重放 payload 与已落库快照不一致"
                "(route %s→%s / focus %s→%s),忽略新 payload 按重放返回",
                it.navigation_id, replay.get("detail_route"), it.detail_route,
                focus_id, it.focus.id)

    def _find_context_snapshot_by_navigation(
            self, session_id: str, navigation_id: str) -> dict | None:
        """按 (session_id, navigation_id) 读回快照——幂等重放的读路径,
        预查与唯一键冲突兜底都走这里。"""
        rows = self._query(
            f"SELECT {self._CONTEXT_SNAPSHOT_FIELDS} FROM context_snapshot "
            "WHERE session_id=$sid AND navigation_id=$nav LIMIT 1",
            {"sid": session_id, "nav": navigation_id})
        return rows[0] if rows else None

    def create_context_session(self, work: str, actor_id: str, device_id: str) -> dict:
        """开一个上下文会话并落 revision=0 的初始快照,返回初始快照 dict。

        session 与初始快照在同一条事务里创建:不存在"有 session 无快照"的中间态,
        get_context_snapshot 对新会话永远有得读。

        Task 6 兑现:thread_id 取自本 work 的正式主编线程(get_or_create_editorial_thread,
        幂等)——create_context_session / backfill_thread_ids / list_thread_messages 三处
        共用同一 ethread id,前端 snapshot.thread_id 与 /chat/threads、backfill 归档端到端一致
        (此前占位 thread:{work}_default 与 ethread 命名空间断裂,旧对话在 UI 上凭空消失)。

        如实说明:本方法非幂等——_context_tx 的连接重试若落在"首次已提交、
        响应丢失"的窗口,重放会以同 id CREATE 撞库报错(本机 WS 该窗口极小,
        与 store 既有论断一致,可接受;调用方收到错误重新 create 即可)。"""
        from datetime import datetime, timezone
        from uuid import uuid4
        sid = uuid4().hex
        snap_id = uuid4().hex
        thread_id = self.get_or_create_editorial_thread(work, actor_id)["thread_id"]
        snap = ContextSnapshot(
            session_id=sid, work=work, revision=0, thread_id=thread_id,
            entry="manuscript", directory_path=(),
            focus=ContextFocus(type="entry", id="entry:manuscript", label=""),
            detail_route="entry:manuscript", chapter=None, phase=None,
            focalizer=None, previous_revision=None, navigation_id="init",
            captured_at=datetime.now(timezone.utc), context_hash="",
        ).with_hash()   # hash 在 Python 侧算好落库,库里存最终值
        payload = snap.model_dump(mode="json")
        self._context_tx(
            "BEGIN TRANSACTION; "
            "CREATE type::record('context_session', $sid) SET work=$work, "
            "actor_id=$actor, device_id=$device, thread_id=$thread, status='active', "
            "revision=0, current_snapshot_id=$snap_id, updated_at=time::now(); "
            "CREATE type::record('context_snapshot', $snap_id) SET session_id=$sid, "
            "work=$work, revision=0, previous_revision=NONE, navigation_id='init', "
            "thread_id=$thread, entry=$entry, directory_path=$path, focus=$focus, "
            "detail_route=$route, chapter=NONE, phase=NONE, focalizer=NONE, "
            "reason='restore', context_hash=$hash; "
            "COMMIT TRANSACTION;",
            {"sid": sid, "work": work, "actor": actor_id, "device": device_id,
             "thread": thread_id, "snap_id": snap_id, "entry": payload["entry"],
             "path": payload["directory_path"], "focus": payload["focus"],
             "route": payload["detail_route"], "hash": payload["context_hash"]})
        # reason 不在 ContextSnapshot 模型里(它是导航属性),但落库并随 dict 返回
        return payload | {"reason": "restore"}

    def advance_context(self, session_id: str, intent: dict) -> dict:
        """CAS 推进上下文:仅当 session 处于 active 且 revision == expected_revision
        时创建新快照并推进游标;失配抛 StaleContextError(带 latest),绝不自动覆盖。

        幂等合同:同 navigation_id 一律视为重放——新 payload 被【忽略】,以先落库的
        快照为准(payload 不一致仅 log warning)。重放路径有三层:
        ① 预查命中 → 直接返回;注意预查先于 ended 守卫——已 ended 的会话重放
          已有 navigation_id 仍幂等返回旧快照而非拒绝(只有"推进出新快照"才被拒);
        ② 并发重放对方已提交时,后到者的事务撞的是 stale THROW(IF 判定在 CREATE
          之前,轮不到唯一索引)——故 stale/冲突分支都先按 navigation 读回,命中
          即幂等成功,读不回才是真 stale(实测修正:唯一索引只是极端兜底);
        ③ UNIQUE(session_id, navigation_id) 索引兜底剩余竞态,冲突同样转读回。"""
        from datetime import datetime, timezone
        from uuid import uuid4
        it = NavigationIntent.model_validate(intent)
        # 1. 幂等预查:该导航已落库 → 直接返回(顺序重放的快路径)
        existing = self._find_context_snapshot_by_navigation(session_id, it.navigation_id)
        if existing is not None:
            self._warn_context_replay_mismatch(existing, it)
            return existing
        # 2. 读会话拿 work/thread_id(不在这里判 revision——判定必须进事务)
        sess = self._query(
            "SELECT work, thread_id FROM type::record('context_session', $sid)",
            {"sid": session_id})
        if not sess:
            raise ValueError(f"advance_context: context_session '{session_id}' 不存在")
        new_rev = it.expected_revision + 1
        snap_id = uuid4().hex
        snap = ContextSnapshot(
            session_id=session_id, work=sess[0]["work"], revision=new_rev,
            thread_id=sess[0]["thread_id"], entry=it.entry,
            directory_path=tuple(it.directory_path), focus=it.focus,
            detail_route=it.detail_route, chapter=it.chapter, phase=it.phase,
            focalizer=it.focalizer, previous_revision=it.expected_revision,
            navigation_id=it.navigation_id,
            captured_at=datetime.now(timezone.utc), context_hash="",
        ).with_hash()
        payload = snap.model_dump(mode="json")
        # 3. 单事务 CAS:读-判-写在同一条多语句 SurrealQL 里完成
        try:
            self._context_tx(
                "BEGIN TRANSACTION; "
                "LET $cur = (SELECT revision, status "
                "FROM type::record('context_session', $sid)); "
                "IF array::len($cur) == 0 { THROW 'context_session_missing' }; "
                # I-2:ended 守卫——已结束的会话拒绝推进(end 方法由后续任务建)
                "IF $cur[0].status != 'active' { THROW 'context_session_ended' }; "
                "IF $cur[0].revision != $expected "
                "{ THROW 'stale_revision:' + <string>$cur[0].revision }; "
                "CREATE type::record('context_snapshot', $snap_id) SET session_id=$sid, "
                "work=$work, revision=$rev, previous_revision=$prev, navigation_id=$nav, "
                "thread_id=$thread, entry=$entry, directory_path=$path, focus=$focus, "
                "detail_route=$route, chapter=$chapter, phase=$phase, "
                "focalizer=$focalizer, reason=$reason, context_hash=$hash; "
                "UPDATE type::record('context_session', $sid) SET revision=$rev, "
                "current_snapshot_id=$snap_id, updated_at=time::now(); "
                "COMMIT TRANSACTION;",
                {"sid": session_id, "expected": it.expected_revision,
                 "snap_id": snap_id, "work": payload["work"], "rev": new_rev,
                 "prev": it.expected_revision, "nav": it.navigation_id,
                 "thread": payload["thread_id"], "entry": payload["entry"],
                 "path": payload["directory_path"], "focus": payload["focus"],
                 "route": payload["detail_route"], "chapter": it.chapter,
                 "phase": it.phase, "focalizer": it.focalizer,
                 "reason": it.reason, "hash": payload["context_hash"]})
        except _CONN_ERRORS:
            raise   # 连接类异常已在 _context_tx 重试过一次,再失败原样上抛
        except Exception as e:
            msg = str(e)
            kind = self._classify_context_tx_error(msg)
            if kind in ("stale", "unique_conflict", "commit_conflict"):
                # I-1:三类都可能是同 navigation 的并发重放——对方已提交时,
                # 后到者的事务在 IF 处撞 stale THROW(轮不到唯一索引),直接抛
                # 就是给重放请求喂假 409。先按 navigation 读回,命中即幂等成功。
                replay = self._find_context_snapshot_by_navigation(
                    session_id, it.navigation_id)
                if replay is not None:
                    self._warn_context_replay_mismatch(replay, it)
                    return replay
                # 读不回才是真 CAS 失配(含提交层读写冲突/revision 唯一键被抢):
                # actual 优先取 THROW 携带的值,否则回读会话
                m = re.search(r"stale_revision:(\d+)", msg)
                if m:
                    actual = int(m.group(1))
                else:
                    cur = self._query(
                        "SELECT revision FROM type::record('context_session', $sid)",
                        {"sid": session_id})
                    actual = cur[0]["revision"] if cur else -1
                # latest 带上服务端最新快照,前端可直接对齐免再读
                raise StaleContextError(
                    it.expected_revision, actual,
                    latest=self.get_context_snapshot(session_id)) from e
            if kind == "session_missing":
                raise ValueError(
                    f"advance_context: context_session '{session_id}' 不存在") from e
            if kind == "session_ended":
                raise ValueError(
                    f"advance_context: context_session '{session_id}' 已结束"
                    "(status != 'active'),拒绝推进") from e
            raise
        return payload | {"reason": it.reason}

    def get_context_snapshot(self, session_id: str, revision: int | None = None) -> dict | None:
        """读快照:revision=None 返回 current(经 current_snapshot_id,悬空时兜底
        取最大 revision);指定 revision 返回该历史版;找不到返回 None。"""
        if revision is not None:
            rows = self._query(
                f"SELECT {self._CONTEXT_SNAPSHOT_FIELDS} FROM context_snapshot "
                "WHERE session_id=$sid AND revision=$rev LIMIT 1",
                {"sid": session_id, "rev": int(revision)})
            return rows[0] if rows else None
        sess = self._query(
            "SELECT current_snapshot_id FROM type::record('context_session', $sid)",
            {"sid": session_id})
        if not sess:
            return None
        snap_id = sess[0].get("current_snapshot_id")
        if snap_id:
            rows = self._query(
                f"SELECT {self._CONTEXT_SNAPSHOT_FIELDS} "
                "FROM type::record('context_snapshot', $snap)",
                {"snap": snap_id})
            if rows:
                return rows[0]
        # 兜底:current_snapshot_id 缺失/悬空时取最大 revision
        # (3.x ORDER BY 必须引用选择列——revision 在选择列里,合规)
        rows = self._query(
            f"SELECT {self._CONTEXT_SNAPSHOT_FIELDS} FROM context_snapshot "
            "WHERE session_id=$sid ORDER BY revision DESC LIMIT 1",
            {"sid": session_id})
        return rows[0] if rows else None
