from __future__ import annotations
import uuid

from surrealdb import RecordID


def _rows(res):
    """SurrealDB SDK query() 返回归一为 list[dict]。
    实测 surrealdb 3.x query() 直接返回 list[dict];兼容旧版 [{'result':[...]}]。"""
    if not res:
        return []
    first = res[0]
    if isinstance(first, dict) and "result" in first and isinstance(first["result"], list):
        return first["result"]
    return res


def _d(rec):
    """RecordID/对象 → 普通 dict(便于断言/序列化)。"""
    if rec is None:
        return None
    return dict(rec) if not isinstance(rec, dict) else rec


class Store:
    """SurrealDB 领域存取薄封装。表名即实体类型;id 用 uuid hex(record id = table:⟨id⟩)。
    CRUD 走 SDK 原生方法(create/select/merge),避免 SurrealQL record-id 字面量解析坑。"""

    def __init__(self, db):
        self.db = db

    def create(self, table: str, data: dict) -> str:
        rid = uuid.uuid4().hex
        self.db.create(RecordID(table, rid), data)
        return rid

    def get(self, table: str, rid: str) -> dict | None:
        r = self.db.select(RecordID(table, rid))
        rows = r if isinstance(r, list) else ([r] if r else [])
        return _d(rows[0]) if rows else None

    def list(self, table: str, where: str = "", vars: dict | None = None) -> list[dict]:
        if where:
            # table 是内部受控字符串(枚举),可安全插值;过滤值走参数
            q = f"SELECT * FROM {table} WHERE {where};"
            return [_d(r) for r in _rows(self.db.query(q, vars or {}))]
        return [_d(r) for r in (self.db.select(table) or [])]

    def update(self, table: str, rid: str, patch: dict) -> None:
        self.db.merge(RecordID(table, rid), patch)


    def put_content(self, table: str, work: str, text: str, **fields) -> str:
        """写内容实体:record + embedding 同写,供向量/全文检索。"""
        from .embed import embed
        vec = embed([text])[0] if text else None
        rid = uuid.uuid4().hex
        self.db.create(RecordID(table, rid),
                       {"work": work, "text": text, "embedding": vec, **fields})
        return rid


    def relate(self, frm: str, edge: str, to: str, props: dict | None = None) -> None:
        """建图边。frm/to 是完整 record id 字符串(如 'character:⟨uuid⟩'),id 用反引号包防数字解析。"""
        self.db.query(f"RELATE {frm}->{edge}->{to} CONTENT $p;", {"p": props or {}})

    def neighbors(self, node: str, edge: str) -> list:
        rows = _rows(self.db.query(f"SELECT ->{edge}->?.* AS n FROM {node};"))
        return rows[0]["n"] if rows and rows[0].get("n") else []


    def search_knowledge(self, work: str, query: str, k: int = 6,
                         types: list | None = None) -> list:
        """统一知识检索:逐内容表算 cosine 相似(向量),按书过滤,合并去重排序。
        work 为存储时的归属串(如 'work:1')。几百实体用暴力 cosine 足够;规模化可换 HNSW <|k,EF|>。"""
        from .embed import embed
        from .schema import CONTENT_TABLES
        qv = embed([query])[0]
        tables = types or CONTENT_TABLES
        seen, out = set(), []
        for tb in tables:
            rows = _rows(self.db.query(
                f"SELECT id, text, name, vector::similarity::cosine(embedding, $qv) AS score "
                f"FROM {tb} WHERE work = $w AND embedding != NONE "
                f"ORDER BY score DESC LIMIT $k;",
                {"qv": qv, "w": work, "k": k}))
            for r in rows:
                rid = str(r.get("id"))
                if rid in seen:
                    continue
                seen.add(rid)
                rec = _d(r); rec["entity_type"] = tb; out.append(rec)
        out.sort(key=lambda r: r.get("score") or 0, reverse=True)
        return out[:k]

    def init_schema(self) -> None:
        from .schema import ddl
        for stmt in ddl():
            self.db.query(stmt)
