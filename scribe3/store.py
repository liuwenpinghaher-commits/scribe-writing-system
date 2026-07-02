"""SurrealStore · 故事本体 v2 的 SurrealDB 持久层(NS=scribe3)。

把纵切片的内存 World 迁到 SurrealDB,接口与 World 鸭子兼容——knowledge.project_frame /
knowledge.project_frame 不改一行即可跑在真库上(证限知范式在持久层照样成立)。

不变量:**改世界状态只经 _execute_write 单一落库点**(开发标准 §0 不变量1)。
oid 映射:本体 id(role:焦三 / fact:治眼)↔ SurrealDB record(character:焦三 / proposition:治眼)。
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path

from surrealdb import RecordID, Surreal

from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge

# 本体 id 前缀 ↔ SurrealDB 表名
ONT2TBL = {"role": "character", "place": "place", "fact": "proposition", "ev": "event"}
TBL2ONT = {"character": "role", "place": "place", "proposition": "fact", "event": "ev"}
TBL2KIND = {"character": "character", "place": "place"}

_OPEN_CHAPTER = 9999    # graph()/无界查询的"到当前为止"哨兵
_ALL_CHAPTERS = 99999   # _editor_system 取全部已确立事实
_UNSET = object()       # update_chapter_meta 的哨兵:区分"未传 volume"与"传了 None"


def _split(oid: str) -> tuple[str, str]:
    prefix, local = oid.split(":", 1)
    return ONT2TBL[prefix], local


def _join(table: str, local: str) -> str:
    return f"{TBL2ONT[table]}:{local}"


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


_TABLES = frozenset(list(ONT2TBL.values()) + ["promise", "motif", "motif_instance"])
_FIELDS_BY_TABLE: dict[str, frozenset] = {
    "character": frozenset({"name", "aliases", "backstory", "backstory_secret", "importance",
        "appearance", "personality_detail", "abilities", "weaknesses",
        "surface_goal", "deep_need", "internal_conflict", "fear",
        "first_appearance", "personality_tags"}),
    "place": frozenset({"name"}),
    "proposition": frozenset({"entity_id", "attribute", "value", "valid_from",
                              "valid_to", "secret", "leak_markers", "ingest_seq"}),
    "event": frozenset({"event_type", "story_chapter",
                        "motivated_by_goal", "location", "preconditions"}),
    "promise": frozenset({"text", "setup_chapter", "payoff_chapter", "status", "kind", "clues"}),
    "motif": frozenset({"name", "theme", "echoes", "unfolding"}),
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
        "WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch)", {"ch": chapter})
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


def _overdue_flag(p: dict, max_chapter: int, slack: int) -> bool:
    """伏笔超期单源判定。open 且非 red_herring 且 setup+slack < max_chapter → 超期。

    /promises、/quality、/promises/ledger 三处共用此函数,杜绝阈值口径漂移。
    setup_chapter 缺失时不判超期(交由 audit 的 closed_without_setup 报数据异常)。
    """
    setup = p.get("setup_chapter")
    return bool(p.get("status") == "open"
                and p.get("kind") != "red_herring"
                and setup is not None
                and setup + slack < max_chapter)


_TIER_WINDOW = {"chapter": (1, 3), "arc": (5, 15), "book": (1, None)}


def promise_window_state(p: dict, max_chapter: int) -> dict:
    """伏笔窗口计算态。next_ch = max_chapter+1(即将写的下一章)。
    state ∈ inactive / pre_window / in_window / over_half / overdue。
    salience_gap = 距上次露面(埋设或触及)的章数,供'先刷新再兑现'门槛用。"""
    setup = p.get("setup_chapter")
    if p.get("status") != "open" or p.get("kind") == "red_herring" or setup is None:
        return {"state": "inactive", "salience_gap": None}
    next_ch = max_chapter + 1
    pmin = p.get("payoff_min") or setup + 1
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
        "SELECT seq, prose FROM chapter WHERE scene_count IS NONE")
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


class SurrealStore:
    """SurrealDB 后端的 World。默认连 NS=scribe3 / DB=main(与 scribe2 的 NS=scribe 隔离)。"""

    def __init__(self, url: str | None = None, ns: str = "scribe3", db: str = "main",
                 user: str | None = None, password: str | None = None):
        self.url = url or os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc")
        user = user or os.environ.get("SCRIBE3_SURREAL_USER", "root")
        password = password or os.environ.get("SCRIBE3_SURREAL_PASS", "root")
        self._db = Surreal(self.url)
        self._db.signin({"username": user, "password": password})
        self._db.use(ns, db)

    def close(self) -> None:
        try:
            self._db.close()
        except Exception as e:
            logging.getLogger("scribe3.store").warning("store.close 失败: %s", e)

    # --- schema ---
    def apply_schema(self, migrations_dir: str | None = None) -> None:
        d = Path(migrations_dir or Path(__file__).parent / "migrations")
        self._db.query("DEFINE TABLE IF NOT EXISTS _migration SCHEMALESS; "
                       "DEFINE FIELD IF NOT EXISTS applied_at ON _migration TYPE datetime;")
        try:
            rows = self._query("SELECT meta::id(id) AS id FROM _migration")
            applied = {f"_migration:{r['id']}" for r in (rows or []) if r and r.get("id")}
        except Exception:
            applied = set()
        for f in sorted(d.glob("*.surql")):
            key = f"_migration:{f.stem}"
            if key in applied:
                continue
            try:
                self._db.query(f.read_text(encoding="utf-8"))
            except Exception as e:
                logging.getLogger("scribe3").warning("迁移 %s 失败(可能已应用): %s", f.stem, str(e)[:80])
            self._db.query("CREATE type::record('_migration', $name) SET applied_at = time::now()",
                           {"name": f.stem})

    # --- 唯一写入点 ---
    def _execute_write(self, surql: str, vars: dict) -> None:
        """改世界状态的唯一落库点。所有 add_* 经此(开发标准不变量1)。"""
        self._db.query(surql, vars)

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
        res = self._db.query(surql, vars or {})
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

    def add_event(self, ev: Event) -> Event:
        _, local = _split(ev.id)
        ev_rid = RecordID("event", local)
        loc_local = _split(ev.location)[1] if ev.location else None
        self._execute_write(
            "CREATE type::record('event', $local) SET event_type=$t, "
            "story_chapter=$vf, narrative_position=$np, "
            "motivated_by_goal=$g, location=$loc, preconditions=$pre",
            {"local": local, "t": ev.type, "vf": ev.story_time, "g": ev.motivated_by_goal,
             "np": ev.narrative_position,  # 完整期:可空叙事位;null 回退 story_chapter(向后兼容)
             "loc": RecordID("place", loc_local) if loc_local else None,
             "pre": ev.preconditions})
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
            self._db.query(surql)

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
        # 4. P2-a Fix5: 清本章 ingest_unverified 记录——重 ingest 时防止累积重复 pending
        self._execute_write("DELETE ingest_unverified WHERE seq = $seq", {"seq": seq})
        # 5. 母题章实例:随本章 ingest 幂等清除
        self._execute_write("DELETE motif_instance WHERE ingest_seq = $seq", {"seq": seq})

    def add_unverified_ref(self, name: str, seq: int, role: str) -> None:
        """登记 ingest 抽到的库外角色名→待确认(不建实体、不发边)。"""
        self._execute_write(
            "CREATE ingest_unverified SET name=$n, seq=$s, role=$r, status='pending'",
            {"n": name, "s": seq, "r": role})

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
            "valid_from, valid_to, secret, leak_markers FROM proposition "
            "WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch)", {"ch": chapter})
        return [Fact(f"fact:{r['local']}", r.get("entity_id") or "",
                     r["attribute"], r["value"],
                     r["valid_from"], r.get("valid_to"), r.get("secret", False),
                     r.get("leak_markers", [])) for r in rows]

    def characters(self) -> list[Entity]:
        rows = self._query(
            "SELECT meta::id(id) AS local, name, backstory, backstory_secret, aliases, personality_tags, "
            "importance, appearance, personality_detail, abilities, weaknesses, "
            "first_appearance, surface_goal, deep_need, internal_conflict, fear FROM character")
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
        """语义召回最相关命题(HNSW <|K,COSINE|>,按距离升序)。"""
        from scribe3.embed import embed
        qv = embed([query])[0]
        rows = self._query(
            f"SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, "
            f"secret, leak_markers, vector::distance::knn() AS dist "
            f"FROM proposition WHERE embedding <|{int(k)},COSINE|> $qv ORDER BY dist", {"qv": qv})
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
            f"FROM chapter WHERE embedding <|{int(k)},COSINE|> $qv ORDER BY dist", {"qv": qv})
        return [{"seq": r["seq"], "title": r.get("title", ""), "distance": r["dist"]} for r in rows]

    def graph_recall(self, query: str, chapter: int, k: int = 5) -> list[dict]:
        """Graph RAG:向量召回种子命题 + 沿图边拼知识子图(B枢纽)。
        返回每条种子事实 + {主体, 知情角色, 来源事件, 同场角色}。
        限知时间门(chapter)过滤未来事实。"""
        from scribe3.embed import embed
        qv = embed([query])[0]
        rows = self._query(
            f"SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, secret, "
            f"  entity_link.name AS subject, "
            f"  <-knows<-character.name AS knowers, "
            f"  <-causes<-event.event_type AS source_events, "
            f"  <-causes<-event->involves->character.name AS co_present, "
            f"  vector::distance::knn() AS dist "
            f"FROM proposition WHERE embedding <|{int(k)},COSINE|> $qv "
            f"  AND valid_from <= $ch ORDER BY dist", {"qv": qv, "ch": chapter})
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

    def delete_record(self, oid: str) -> None:
        t, l = _split(oid)
        self._delete_by(t, l)

    def update_promise(self, pid: str, fields: dict) -> bool:
        """更新伏笔字段;返回 True 若存在,False 若不存在。"""
        rows = self._query("SELECT id FROM type::record('promise',$pid) LIMIT 1", {"pid": pid})
        if not rows:
            return False
        self._update_by("promise", pid, fields)
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
    def add_voice_flag(self, character: str, seq: int, reason: str) -> None:
        # seq 是退场方(021 起改名为 trigger_chapter)。只写真源 trigger_chapter。
        self._execute_write(
            "CREATE voice_evolution_flag SET character=$c, "
            "trigger_chapter=$s, reason=$r, status='open'",
            {"c": character, "s": seq, "r": reason})

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
                      tier: str = "chapter") -> None:
        lo, hi = _TIER_WINDOW.get(tier, _TIER_WINDOW["chapter"])
        pmin = setup_chapter + lo
        pmax = None if hi is None else setup_chapter + hi
        self._execute_write(
            "CREATE promise SET text=$t, setup_chapter=$s, payoff_chapter=NONE, status='open', "
            "kind=$k, tier=$tier, payoff_min=$pmin, payoff_max=$pmax, resolution=NONE",
            {"t": text, "s": setup_chapter, "k": kind,
             "tier": tier, "pmin": pmin, "pmax": pmax})

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
            qc_causal_n = len(causal_complete(self, seq))
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "qc_causal 计算失败(降级为 0): %s", _e)
            qc_causal_n = 0
        return {"scene_count": len(scenes), "scene_meta": scene_meta,
                "qc_issues": qc_n, "qc_causal": qc_causal_n,
                "qc_breakdown": json.dumps(breakdown, ensure_ascii=False)}

    def save_chapter(self, seq: int, prose: str, title: str = "", focalizer: str | None = None,
                     _today: str | None = None) -> None:
        """落/覆盖某章正文(UPSERT)。附带章向量 + QC缓存(字数,不再全拉正文统计)。
        _today:测试时注入固定日期字符串(YYYY-MM-DD),生产不传。"""
        text_for_embed = f"{title} {prose[:200]}".strip()
        from scribe3.embed import embed
        vec = embed([text_for_embed])[0]
        wc = len("".join(prose.split()))
        # 千万字缓存(Phase0-BE1):落库时算好场景切分 + QC 计数,聚合端点不再全表拉正文/重算。
        cache = self._compute_chapter_caches(seq, prose)
        self._execute_write(
            "UPSERT type::record('chapter',$seq) SET seq=$seq, title=$title, "
            "focalizer=$foc, prose=$prose, embedding=$v, qc_word_count=$wc, "
            "scene_count=$scn, scene_meta=$scm, qc_issues=$qc, qc_causal=$qcc, qc_breakdown=$qcb",
            {"seq": seq, "title": title, "foc": focalizer, "prose": prose, "v": vec, "wc": wc,
             "scn": cache["scene_count"], "scm": cache["scene_meta"], "qc": cache["qc_issues"],
             "qcc": cache["qc_causal"], "qcb": cache["qc_breakdown"]})
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
            "UPSERT type::record('chapter',$seq) SET seq=$seq, draft=$draft",
            {"seq": seq, "draft": draft})

    def get_chapter(self, seq: int) -> dict | None:
        """单章身份 + 四阶段内容(synopsis/beats/draft/prose)。
        beats 存为 JSON 串,读时解析为 list;缺失降级为 []。"""
        rows = self._query(
            "SELECT seq,title,focalizer,prose,synopsis,beats,draft,"
            "scene_truth,involved_characters,deductions "
            "FROM type::record('chapter',$seq)", {"seq": seq})
        if not rows:
            return None
        r = rows[0]
        import json
        raw_beats = r.get("beats")
        try:
            r["beats"] = json.loads(raw_beats) if raw_beats else []
        except (ValueError, TypeError):
            r["beats"] = []
        for _k in ("involved_characters", "deductions"):
            raw = r.get(_k)
            try:
                r[_k] = json.loads(raw) if raw else []
            except (ValueError, TypeError):
                r[_k] = []
        r["scene_truth"] = r.get("scene_truth") or ""
        return r

    def list_chapters(self) -> list[dict]:
        return self._query("SELECT seq,title FROM chapter ORDER BY seq")

    def recent_proses(self, before_seq: int, k: int = 5) -> list[dict]:
        """before_seq 之前最近 k 章的 {seq, prose}(按 seq 升序)。
        供跨章复读检测与"前文已用措辞→生成时避免"清单复用。"""
        rows = self._query(
            "SELECT seq, prose FROM chapter WHERE seq < $s ORDER BY seq DESC LIMIT $k",
            {"s": before_seq, "k": k})
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
        rows = self._query(
            "SELECT count() AS chapter_count, math::sum(qc_word_count) AS word_count "
            "FROM chapter GROUP ALL")
        r = rows[0] if rows else {"chapter_count": 0, "word_count": 0}
        return {"chapter_count": r.get("chapter_count", 0), "word_count": r.get("word_count", 0)}

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
        content: dict = {
            "reader_feeling": fields.get("reader_feeling", ""),
            "emotional_arc": fields.get("emotional_arc", ""),
            "red_lines": fields.get("red_lines", ""),
        }
        if fields.get("overdue_threshold") is not None:
            content["overdue_threshold"] = fields["overdue_threshold"]
        if fields.get("total_word_goal") is not None:
            content["total_word_goal"] = int(fields["total_word_goal"])
        if fields.get("daily_word_goal") is not None:
            content["daily_word_goal"] = int(fields["daily_word_goal"])
        self._execute_write("UPSERT intent:main CONTENT $c", {"c": content})

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
        ch_rows = self._query("SELECT seq FROM chapter")
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
            "before_state, after_state, trigger_event, arc_phase, affects_voice, confidence "
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
        hi = ch_to if ch_to is not None else self.max_chapter()
        if hi == 0:
            return []
        items: list[dict] = []

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
                        "overdue": p.get("overdue", False),
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
                       ingest_seq: int | None = None) -> None:
        """记录角色弧光质变点(能力/关系/性格变化)。
        affects_voice=True 时自动创建 voice_evolution_flag(该更新声音了)。
        ingest_seq:由 ingest 自动回写时传入,供 purge_ingest 幂等清理;手动种的不传。"""
        _, local = _split(character_id)
        self._execute_write(
            "CREATE char_state SET character_id=$cid, chapter=$ch, change_type=$ct, "
            "summary=$sum, before_state=$bs, after_state=$as, trigger_event=$te, "
            "arc_phase=$ap, affects_voice=$av, confidence=$conf"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"cid": character_id, "ch": chapter, "ct": change_type, "sum": summary,
             "bs": before_state, "as": after_state, "te": trigger_event,
             "ap": arc_phase, "av": affects_voice, "conf": confidence,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        if affects_voice:
            self.add_voice_flag(character_id, chapter, summary)

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
            "before_state, after_state, trigger_event, arc_phase, affects_voice, confidence "
            "FROM char_state WHERE character_id=$cid ORDER BY chapter ASC",
            {"cid": character_id})

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
                 first_chapter: int | None = None) -> str:
        """添加/覆盖物品(同名幂等:先删后建)。返回物品名。"""
        self._execute_write("DELETE item WHERE name=$n", {"n": name})
        self._execute_write(
            "CREATE item SET name=$n, category=$cat, description=$desc, "
            "current_owner=$co, symbolic_state=$ss, state_history=[], "
            "special_properties=$sp, first_chapter=$fc",
            {"n": name, "cat": category, "desc": description, "co": current_owner,
             "ss": symbolic_state, "sp": special_properties or [], "fc": first_chapter})
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
        覆盖:能力矛盾/规则违反/OOC/物品状态矛盾/命名不一致。"""
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

    def validate_cross_chapter_consistency(self) -> list[dict]:
        """跨章一致性检测(全书扫描)。

        返回 hint 列表(与 validate_setting 同结构),包含:
          (a) numeric_inconsistency —— 同一专名实体在不同章绑定不同数字(如「潭家二十七口」vs「潭家三百一十七口」)
          (b) unregistered_name     —— 高频疑似专名(≥3次)但未在 characters/terms/factions/items 中登记

        不修改任何状态,可安全重复调用。向后兼容:不影响原 validate_setting 签名。
        """
        import re

        hints: list[dict] = []

        # ── 收集全书章正文 ──────────────────────────────────────────────────
        chapters = self._query("SELECT seq, prose FROM chapter ORDER BY seq")
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
            "FROM chapter")
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
            "id": "codex_root", "type": "codex_root", "label": "素材",
            "children": codex_children,
        }

        # —— 横切视图(静态清单)——
        views = [
            {"id": "view:overview", "type": "view", "label": "概览"},
            {"id": "view:atlas", "type": "view", "label": "图谱"},
            {"id": "view:timeline", "type": "view", "label": "时间线"},
            {"id": "view:insight", "type": "view", "label": "仪表盘"},
            {"id": "view:progress", "type": "view", "label": "进度"},
        ]

        return {"manuscript": manuscript, "codex": codex, "views": views}

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
                   "scene_truth", "involved_characters", "deductions"}
        # volume 需单独处理(record link 不能传字符串参数)
        volume_id = _UNSET  # 哨兵:区分"未传 volume"与"传了 None(清空)"
        plain: dict = {}
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k == "volume":
                volume_id = v   # None = 清空, str = 新卷裸 id
            elif k in ("beats", "involved_characters", "deductions"):
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
