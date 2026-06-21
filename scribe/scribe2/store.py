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


def _norm(v):
    """RecordID → 干净的 'table:hex' 字符串(供 JSON 序列化 + 前端/_idpart round-trip)。"""
    if isinstance(v, RecordID):
        return f"{v.table_name}:{v.id}"
    return v


def _d(rec):
    """RecordID/对象 → 普通 dict;把内含的 RecordID 字段归一成字符串。"""
    if rec is None:
        return None
    d = dict(rec) if not isinstance(rec, dict) else rec
    return {k: _norm(v) for k, v in d.items()}


class Store:
    """SurrealDB 领域存取薄封装。表名即实体类型;id 用 uuid hex(record id = table:⟨id⟩)。
    CRUD 走 SDK 原生方法(create/select/merge),避免 SurrealQL record-id 字面量解析坑。"""

    def __init__(self, db):
        self.db = db

    def create(self, table: str, data: dict) -> str:
        rid = uuid.uuid4().hex
        self.db.create(RecordID(table, rid), data)
        return rid

    @staticmethod
    def _hex(rid: str) -> str:
        """归一:'table:hex' 或 'hex' → 'hex'(前端可能回传带表名的 id)。"""
        s = str(rid)
        return s.split(":", 1)[1].strip("⟨⟩`") if ":" in s else s

    def get(self, table: str, rid: str) -> dict | None:
        r = self.db.select(RecordID(table, self._hex(rid)))
        rows = r if isinstance(r, list) else ([r] if r else [])
        return _d(rows[0]) if rows else None

    def list(self, table: str, where: str = "", vars: dict | None = None) -> list[dict]:
        if where:
            # table 是内部受控字符串(枚举),可安全插值;过滤值走参数
            q = f"SELECT * FROM {table} WHERE {where};"
            return [_d(r) for r in _rows(self.db.query(q, vars or {}))]
        return [_d(r) for r in (self.db.select(table) or [])]

    def update(self, table: str, rid: str, patch: dict) -> None:
        self.db.merge(RecordID(table, self._hex(rid)), patch)

    def delete(self, table: str, rid: str) -> None:
        self.db.delete(RecordID(table, self._hex(rid)))

    def delete_where(self, table: str, where: str, vars: dict) -> None:
        self.db.query(f"DELETE FROM {table} WHERE {where};", vars)


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
                         types: list | None = None, expand: bool = False):
        """统一知识检索:逐内容表算 cosine 相似(向量),按书过滤,合并去重排序。
        expand=True 时,对命中实体顺图(任意边,双向)带回关联实体。
        work 为存储归属串(如 'work:1');几百实体暴力 cosine 足够。"""
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
        hits = out[:k]
        if not expand:
            return hits
        hit_ids = {str(h.get("id")) for h in hits}
        related = []
        for h in hits:
            # h["id"] 已被 _d 归一成 'table:hex' 字符串,图遍历需还原成 RecordID
            tb_, hx_ = str(h["id"]).split(":", 1)
            rows = _rows(self.db.query(
                "SELECT ->?->?.* AS o, <-?<-?.* AS i FROM $rid;",
                {"rid": RecordID(tb_, hx_)}))
            for r in rows:
                for side in ("o", "i"):
                    for x in (r.get(side) or []):
                        xd = _d(x)
                        if str(xd.get("id")) not in hit_ids:
                            hit_ids.add(str(xd.get("id"))); related.append(xd)
        return {"hits": hits, "related": related}

    def init_schema(self) -> None:
        from .schema import ddl
        for stmt in ddl():
            try:
                self.db.query(stmt)
            except Exception:
                pass  # 幂等:已定义的表/索引重复 DEFINE 忽略
