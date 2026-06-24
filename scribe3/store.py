"""SurrealStore · 故事本体 v2 的 SurrealDB 持久层(NS=scribe3)。

把纵切片的内存 World 迁到 SurrealDB,接口与 World 鸭子兼容——knowledge.project_frame /
render.build_render_prompt 不改一行即可跑在真库上(证明限知范式在持久层照样成立)。

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


_TABLES = frozenset(ONT2TBL.values())


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
        "SELECT meta::id(id) AS local, entity, attribute, value, valid_from, valid_to, "
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
    return [Fact(f"fact:{r['local']}", r["entity"], r["attribute"], r["value"],
                 r["valid_from"], r.get("valid_to"), r.get("secret", False),
                 r.get("leak_markers", [])) for _, r in top]


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
            applied = {r["id"] for r in (rows or []) if r and r.get("id")}
        except Exception:
            applied = set()
        for f in sorted(d.glob("*.surql")):
            key = f"_migration:`{f.stem}`"
            if key in applied:
                continue
            self._db.query(f.read_text(encoding="utf-8"))
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
                "CREATE type::record('character', $local) SET name=$name, aliases=$al, backstory=$bs",
                {"local": local, "name": e.name, "al": e.traits.get("aliases", []),
                 "bs": e.traits.get("backstory")})
        elif e.kind == "place":
            self._execute_write("CREATE type::record('place', $local) SET name=$name",
                                {"local": local, "name": e.name})
        return e

    def add_fact(self, f: Fact, ingest_seq: int | None = None) -> Fact:
        _, local = _split(f.id)
        self._execute_write(
            "UPSERT type::record('proposition', $local) SET entity=$entity, entity_id=$entity, "
            "attribute=$attr, value=$value, valid_from=$vf, valid_to=$vt, secret=$secret, "
            "leak_markers=$lm"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"local": local, "entity": f.entity_id, "attr": f.attribute, "value": f.value,
             "vf": f.valid_from, "vt": f.valid_to, "secret": f.secret, "lm": f.leak_markers,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        return f

    def add_knowledge(self, k: KnowledgeEdge, ingest_seq: int | None = None) -> KnowledgeEdge:
        if k.knower_id == "reader":   # reader 帧:单独表,不走 character->knows 边
            self._execute_write(
                "CREATE reader_knows SET proposition=$p, since_chapter=$since",
                {"p": k.proposition_id, "since": k.since_chapter})
            return k
        ktbl, klocal = _split(k.knower_id)
        ptbl, plocal = _split(k.proposition_id)
        # RELATE 箭头位不接受内联函数,用 RecordID 绑参
        self._execute_write(
            "RELATE $k->knows->$p SET since_chapter=$since, until_chapter=$until, "
            "polarity=$pol, acquired_via=$via"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"k": RecordID(ktbl, klocal), "p": RecordID(ptbl, plocal),
             "since": k.since_chapter, "until": k.until_chapter, "pol": k.polarity,
             "via": k.acquired_via,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        return k

    def add_event(self, ev: Event) -> Event:
        _, local = _split(ev.id)
        ev_rid = RecordID("event", local)
        loc_local = _split(ev.location)[1] if ev.location else None
        self._execute_write(
            "CREATE type::record('event', $local) SET etype=$t, event_type=$t, "
            "valid_from=$vf, story_chapter=$vf, "
            "motivated_by_goal=$g, location=$loc, preconditions=$pre",
            {"local": local, "t": ev.type, "vf": ev.story_time, "g": ev.motivated_by_goal,
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
        """删除某章 ingest 产出的命题 + knows 边(幂等再 ingest 的前置清理)。
        只清 ingest_seq=seq,作者直编/种子(ingest_seq=NONE)不动。"""
        self._execute_write("DELETE knows WHERE ingest_seq = $seq", {"seq": seq})
        self._execute_write("DELETE proposition WHERE ingest_seq = $seq", {"seq": seq})

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
            "SELECT entity_id, entity, attribute, value, valid_from, valid_to, secret, leak_markers "
            "FROM type::record('proposition',$local)", {"local": local})
        if not rows:
            return None
        r = rows[0]
        eid = r.get("entity_id") or r.get("entity") or ""
        return Fact(oid, eid, r["attribute"], r["value"], r["valid_from"],
                    r.get("valid_to"), r.get("secret", False), r.get("leak_markers", []))

    def facts_at(self, chapter: int) -> list[Fact]:
        rows = self._query(
            "SELECT meta::id(id) AS local, entity_id, entity, attribute, value, "
            "valid_from, valid_to, secret, leak_markers FROM proposition "
            "WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch)", {"ch": chapter})
        return [Fact(f"fact:{r['local']}", r.get("entity_id") or r.get("entity") or "",
                     r["attribute"], r["value"],
                     r["valid_from"], r.get("valid_to"), r.get("secret", False),
                     r.get("leak_markers", [])) for r in rows]

    def characters(self) -> list[Entity]:
        rows = self._query("SELECT meta::id(id) AS local, name, backstory FROM character")
        return [Entity(f"role:{r['local']}", "character", r["name"],
                       traits={"backstory": r.get("backstory")}) for r in rows]

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
            f"SELECT meta::id(id) AS local, entity_id, entity, attribute, value, valid_from, valid_to, "
            f"secret, leak_markers, vector::distance::knn() AS dist "
            f"FROM proposition WHERE embedding <|{int(k)},COSINE|> $qv ORDER BY dist", {"qv": qv})
        return [Fact(f"fact:{r['local']}", r.get("entity_id") or r.get("entity") or "",
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

    # --- 母题 motif ---
    def add_motif(self, name: str, theme: str = "", echoes: str = "", unfolding: str = "") -> None:
        self._execute_write(
            "CREATE motif SET name=$n, theme=$t, echoes=$e, unfolding=$u",
            {"n": name, "t": theme, "e": echoes, "u": unfolding})

    def list_motifs(self) -> list[dict]:
        return self._query("SELECT meta::id(id) AS id, name, theme, echoes, unfolding FROM motif")

    # --- 通用 增删改(设定库编辑用)---
    def _update_by(self, table: str, local: str, fields: dict) -> None:
        fields = {k: v for k, v in fields.items() if v is not None}
        if not fields:
            return
        sets = ", ".join(f"{k}=${k}" for k in fields)
        self._execute_write(f"UPDATE type::record('{table}',$_l) SET {sets}", {"_l": local, **fields})

    def _delete_by(self, table: str, local: str) -> None:
        self._execute_write(f"DELETE type::record('{table}',$_l)", {"_l": local})

    def update_record(self, oid: str, fields: dict) -> None:
        t, l = _split(oid)
        self._update_by(t, l, fields)

    def delete_record(self, oid: str) -> None:
        t, l = _split(oid)
        self._delete_by(t, l)

    def update_promise(self, pid: str, fields: dict) -> None:
        self._update_by("promise", pid, fields)

    def delete_promise(self, pid: str) -> None:
        self._delete_by("promise", pid)

    def update_motif(self, mid: str, fields: dict) -> None:
        self._update_by("motif", mid, fields)

    def delete_motif(self, mid: str) -> None:
        self._delete_by("motif", mid)

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

    # --- 声音库(per-character 4类独白 + 版本)---
    def add_voice_sample(self, character: str, kind: str, text: str, since_chapter: int = 0) -> None:
        self._execute_write(
            "CREATE voice_sample SET character=$c, kind=$k, text=$t, since_chapter=$s",
            {"c": character, "k": kind, "t": text, "s": since_chapter})

    def list_voice_samples(self, character: str) -> list[dict]:
        return self._query(
            "SELECT meta::id(id) AS id, character, kind, text, since_chapter "
            "FROM voice_sample WHERE character=$c ORDER BY since_chapter", {"c": character})

    def latest_voice_samples(self, character: str, upto_chapter: int) -> dict:
        """时间门:每 kind 取 since_chapter≤upto 的最新版(不剧透未来版本)。返回 {kind: text}。"""
        rows = self._query(
            "SELECT kind, text, since_chapter FROM voice_sample "
            "WHERE character=$c AND since_chapter <= $u ORDER BY since_chapter",
            {"c": character, "u": upto_chapter})
        out: dict = {}
        for r in rows:                 # 升序遍历,后覆盖前 → 各 kind 最新版
            out[r["kind"]] = r["text"]
        return out

    # --- 声音进化标记 ---
    def add_voice_flag(self, character: str, seq: int, reason: str) -> None:
        self._execute_write(
            "CREATE voice_evolution_flag SET character=$c, seq=$s, reason=$r, status='open'",
            {"c": character, "s": seq, "r": reason})

    def list_voice_flags(self, status: str = "open") -> list[dict]:
        return self._query(
            "SELECT meta::id(id) AS id, character, seq, reason, status "
            "FROM voice_evolution_flag WHERE status=$st", {"st": status})

    # --- 伏笔/promise ---
    def plant_promise(self, text: str, setup_chapter: int, kind: str = "promise") -> None:
        self._execute_write(
            "CREATE promise SET text=$t, setup_chapter=$s, payoff_chapter=NONE, status='open', kind=$k",
            {"t": text, "s": setup_chapter, "k": kind})

    def list_promises(self) -> list[dict]:
        return self._query("SELECT meta::id(id) AS id, text, setup_chapter, payoff_chapter, "
                           "status, kind FROM promise ORDER BY setup_chapter")

    def open_promises(self) -> list[dict]:
        return [p for p in self.list_promises() if p["status"] == "open"]

    def advance_promise(self, pid: str, payoff_chapter: int) -> None:
        self._execute_write("UPDATE type::record('promise',$pid) SET status='closed', "
                            "payoff_chapter=$p", {"pid": pid, "p": payoff_chapter})

    # --- 章节正文(manuscript)---
    def save_chapter(self, seq: int, prose: str, title: str = "", focalizer: str | None = None) -> None:
        """落/覆盖某章正文(UPSERT)。manuscript 是作者草稿,不经 elicitation 待批。"""
        text_for_embed = f"{title} {prose[:200]}".strip()
        from scribe3.embed import embed
        vec = embed([text_for_embed])[0]
        self._execute_write(
            "UPSERT type::record('chapter',$seq) SET seq=$seq, title=$title, "
            "focalizer=$foc, prose=$prose, embedding=$v",
            {"seq": seq, "title": title, "foc": focalizer, "prose": prose, "v": vec})

    def get_chapter(self, seq: int) -> dict | None:
        rows = self._query("SELECT seq,title,focalizer,prose FROM type::record('chapter',$seq)",
                           {"seq": seq})
        return rows[0] if rows else None

    def list_chapters(self) -> list[dict]:
        return self._query("SELECT seq,title FROM chapter ORDER BY seq")

    def stats(self) -> dict:
        """本书章数 + 字数(DB侧聚合,避免回传全表正文)。"""
        rows = self._query(
            "SELECT count() AS chapter_count, math::sum(string::len(prose)) AS word_count "
            "FROM chapter GROUP ALL")
        r = rows[0] if rows else {"chapter_count": 0, "word_count": 0}
        return {"chapter_count": r.get("chapter_count", 0), "word_count": r.get("word_count", 0)}

    # --- 北极星(作品意图,单例)---
    def get_intent(self) -> dict:
        rows = self._query("SELECT reader_feeling, emotional_arc, red_lines FROM intent:main")
        r = rows[0] if rows else {}
        return {"reader_feeling": r.get("reader_feeling", ""), "emotional_arc": r.get("emotional_arc", ""),
                "red_lines": r.get("red_lines", "")}

    def set_intent(self, fields: dict) -> None:
        self._execute_write("UPSERT intent:main CONTENT $c", {"c": {
            "reader_feeling": fields.get("reader_feeling", ""),
            "emotional_arc": fields.get("emotional_arc", ""),
            "red_lines": fields.get("red_lines", ""),
        }})

    def graph(self, chapter: int | None = None) -> dict:
        """知识图谱:角色/命题节点 + knows 边(谁知道什么)。chapter 给定则只到该章。
        scribe3 是图库,这是 Atlas 视图的数据源。"""
        ch = chapter if chapter is not None else 9999
        chars = [{"id": e.id, "type": "character", "label": e.name} for e in self.characters()]
        props = [{"id": f.id, "type": "proposition", "label": (f.value or "")[:18],
                  "secret": f.secret} for f in self.facts_at(ch)]
        edges = []
        for k in self.knowledge:
            if k.knower_id == "reader" or k.since_chapter > ch:
                continue
            edges.append({"src": k.knower_id, "dst": k.proposition_id, "rel": "knows"})
        return {"nodes": chars + props, "edges": edges}

    def max_chapter(self) -> int:
        """有事件的最大章号(体检确定扫描范围);无事件→0。"""
        rows = self._query("SELECT valid_from FROM event ORDER BY valid_from DESC LIMIT 1")
        return rows[0]["valid_from"] if rows else 0

    def events_at(self, chapter: int) -> list[Event]:
        """读取某章全部事件(沿图边取回 participants+effects,补 P03 限知裂口)。"""
        rows = self._query(
            "SELECT meta::id(id) AS local, event_type, etype, story_chapter, valid_from, motivated_by_goal, "
            "  (SELECT meta::id(out) AS clocal, role FROM ->involves) AS parts, "
            "  (SELECT meta::id(out) AS plocal FROM ->causes) AS effs, "
            "  (SELECT meta::id(out) AS slocal, ctype FROM ->causal) AS causals "
            "FROM event WHERE story_chapter = $ch OR (story_chapter IS NONE AND valid_from = $ch)", {"ch": chapter})
        out = []
        for r in rows:
            participants = {p["role"]: f"role:{p['clocal']}" for p in (r.get("parts") or [])}
            effects = [f"fact:{e['plocal']}" for e in (r.get("effs") or [])]
            causal_in = [(f"ev:{c['slocal']}", c["ctype"]) for c in (r.get("causals") or [])]
            etype = r.get("event_type") or r.get("etype") or ""
            story_chapter = r.get("story_chapter") if r.get("story_chapter") is not None else r.get("valid_from", 0)
            out.append(Event(f"ev:{r['local']}", etype,
                             participants=participants,
                             story_time=story_chapter,
                             effects=effects,
                             causal_in=causal_in,
                             motivated_by_goal=r.get("motivated_by_goal")))
        return out

    @property
    def knowledge(self) -> list[KnowledgeEdge]:
        rows = self._query(
            "SELECT meta::tb(in) AS itb, meta::id(in) AS iid, meta::tb(out) AS otb, "
            "meta::id(out) AS olocal, since_chapter, until_chapter, polarity, acquired_via FROM knows")
        edges = [KnowledgeEdge(_join(r["itb"], r["iid"]), _join(r["otb"], r["olocal"]),
                               r.get("polarity", True), 1.0, r.get("since_chapter", 0),
                               r.get("until_chapter"), r.get("acquired_via", "given")) for r in rows]
        # 并入 reader 帧(knower=reader)
        rr = self._query("SELECT proposition, since_chapter FROM reader_knows")
        edges += [KnowledgeEdge("reader", r["proposition"], True, 1.0,
                                r.get("since_chapter", 0), None, "given") for r in rr]
        return edges
