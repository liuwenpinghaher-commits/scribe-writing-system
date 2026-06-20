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

    def init_schema(self) -> None:
        from .schema import ddl
        for stmt in ddl():
            self.db.query(stmt)
