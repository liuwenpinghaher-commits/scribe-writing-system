"""SurrealStore · 故事本体 v2 的 SurrealDB 持久层(NS=scribe3)。

把纵切片的内存 World 迁到 SurrealDB,接口与 World 鸭子兼容——knowledge.project_frame /
render.build_render_prompt 不改一行即可跑在真库上(证明限知范式在持久层照样成立)。

不变量:**改世界状态只经 _execute_write 单一落库点**(开发标准 §0 不变量1)。
oid 映射:本体 id(role:焦三 / fact:治眼)↔ SurrealDB record(character:焦三 / proposition:治眼)。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from surrealdb import RecordID, Surreal

from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge

# 本体 id 前缀 ↔ SurrealDB 表名
ONT2TBL = {"role": "character", "place": "place", "fact": "proposition", "ev": "event"}
TBL2ONT = {"character": "role", "place": "place", "proposition": "fact", "event": "ev"}
TBL2KIND = {"character": "character", "place": "place"}


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
    db.signin({"username": "root", "password": "root"})
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


class SurrealStore:
    """SurrealDB 后端的 World。默认连 NS=scribe3 / DB=main(与 scribe2 的 NS=scribe 隔离)。"""

    def __init__(self, url: str | None = None, ns: str = "scribe3", db: str = "main",
                 user: str = "root", password: str = "root"):
        self.url = url or os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc")
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
        for f in sorted(d.glob("*.surql")):
            self._db.query(f.read_text(encoding="utf-8"))

    # --- 唯一写入点 ---
    def _execute_write(self, surql: str, vars: dict) -> None:
        """改世界状态的唯一落库点。所有 add_* 经此(开发标准不变量1)。"""
        self._db.query(surql, vars)

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

    def add_fact(self, f: Fact) -> Fact:
        _, local = _split(f.id)
        self._execute_write(
            "UPSERT type::record('proposition', $local) SET entity=$entity, attribute=$attr, "
            "value=$value, valid_from=$vf, valid_to=$vt, secret=$secret, leak_markers=$lm",
            {"local": local, "entity": f.entity_id, "attr": f.attribute, "value": f.value,
             "vf": f.valid_from, "vt": f.valid_to, "secret": f.secret, "lm": f.leak_markers})
        return f

    def add_knowledge(self, k: KnowledgeEdge) -> KnowledgeEdge:
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
            "polarity=$pol, acquired_via=$via",
            {"k": RecordID(ktbl, klocal), "p": RecordID(ptbl, plocal),
             "since": k.since_chapter, "until": k.until_chapter, "pol": k.polarity,
             "via": k.acquired_via})
        return k

    def add_event(self, ev: Event) -> Event:
        _, local = _split(ev.id)
        self._execute_write(
            "CREATE type::record('event', $local) SET etype=$t, valid_from=$vf, motivated_by_goal=$g",
            {"local": local, "t": ev.type, "vf": ev.story_time, "g": ev.motivated_by_goal})
        return ev

    def grant_public(self, fact_id: str, chapter: int) -> None:
        for c in self.characters():
            self.add_knowledge(KnowledgeEdge(c.id, fact_id, since_chapter=chapter, acquired_via="given"))

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
            "SELECT entity, attribute, value, valid_from, valid_to, secret, leak_markers "
            "FROM type::record('proposition',$local)", {"local": local})
        if not rows:
            return None
        r = rows[0]
        return Fact(oid, r["entity"], r["attribute"], r["value"], r["valid_from"],
                    r.get("valid_to"), r.get("secret", False), r.get("leak_markers", []))

    def facts_at(self, chapter: int) -> list[Fact]:
        rows = self._query(
            "SELECT meta::id(id) AS local, entity, attribute, value, valid_from, valid_to, "
            "secret, leak_markers FROM proposition "
            "WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch)", {"ch": chapter})
        return [Fact(f"fact:{r['local']}", r["entity"], r["attribute"], r["value"],
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
            f"SELECT meta::id(id) AS local, entity, attribute, value, valid_from, valid_to, "
            f"secret, leak_markers, vector::distance::knn() AS dist "
            f"FROM proposition WHERE embedding <|{int(k)},COSINE|> $qv ORDER BY dist", {"qv": qv})
        return [Fact(f"fact:{r['local']}", r["entity"], r["attribute"], r["value"], r["valid_from"],
                     r.get("valid_to"), r.get("secret", False), r.get("leak_markers", [])) for r in rows]

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
        self._execute_write(
            "UPSERT type::record('chapter',$seq) SET seq=$seq, title=$title, "
            "focalizer=$foc, prose=$prose",
            {"seq": seq, "title": title, "foc": focalizer, "prose": prose})

    def get_chapter(self, seq: int) -> dict | None:
        rows = self._query("SELECT seq,title,focalizer,prose FROM type::record('chapter',$seq)",
                           {"seq": seq})
        return rows[0] if rows else None

    def list_chapters(self) -> list[dict]:
        return self._query("SELECT seq,title FROM chapter ORDER BY seq")

    def stats(self) -> dict:
        """本书章数 + 字数(去空白)——作品库卡片用。"""
        rows = self._query("SELECT prose FROM chapter")
        wc = sum(len("".join((r.get("prose") or "").split())) for r in rows)
        return {"chapter_count": len(rows), "word_count": wc}

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
        rows = self._query(
            "SELECT meta::id(id) AS local, etype, valid_from, motivated_by_goal "
            "FROM event WHERE valid_from = $ch", {"ch": chapter})
        return [Event(f"ev:{r['local']}", r["etype"], story_time=r["valid_from"],
                      motivated_by_goal=r.get("motivated_by_goal")) for r in rows]

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
