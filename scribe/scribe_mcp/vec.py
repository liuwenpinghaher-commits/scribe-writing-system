"""向量检索层(sqlite-vec)—— 替代 pgvector 的本地方案(工程8 核实更新)。

分两层(可分别验证):
  1) VecStore: 纯 sqlite-vec 的 KNN 机制(接收已算好的向量)—— 确定性可单测。
  2) embed():  把文本转向量的嵌入提供方 —— 可插拔(本地 fastembed / 远程 embedding API)。
     注:火山 coding-plan key 不提供 embeddings(404),故嵌入提供方独立可换。
ponytail: sqlite-vec 当前仅暴力扫描(<10万向量够用);规模化再迁 pgvector/HNSW(实现4 接口不变)。
"""
from __future__ import annotations

import sqlite3

try:
    import sqlite_vec
    _HAS_VEC = True
except ImportError:  # pragma: no cover
    _HAS_VEC = False


class VecStore:
    """基于 sqlite-vec 的最近邻检索。每个 work 一张逻辑表(用 work_id 过滤防串味)。"""

    def __init__(self, conn: sqlite3.Connection, dim: int):
        if not _HAS_VEC:
            raise RuntimeError("未安装 sqlite-vec:`uv pip install sqlite-vec`")
        self.conn = conn
        self.dim = dim
        # 表名按维度后缀:换嵌入模型(维度变)自动隔到新表,旧表自然作废,永不维度冲突
        self.table = f"vec_segments_{dim}"
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        # vec0 虚拟表:work_id 为可过滤元数据列(防跨书串味 00 §2.7);+content 为辅助存储文本片段
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {self.table} USING vec0("
            f"segment_id TEXT PRIMARY KEY, work_id TEXT, +content TEXT, embedding float[{dim}])"
        )
        conn.commit()

    def add(self, segment_id: str, work_id: str, vector: list[float], content: str = "") -> None:
        if len(vector) != self.dim:
            raise ValueError(f"向量维度 {len(vector)} != {self.dim}")
        self.conn.execute(
            f"INSERT OR REPLACE INTO {self.table}(segment_id, work_id, content, embedding) "
            "VALUES(?,?,?,?)",
            (segment_id, work_id, content, sqlite_vec.serialize_float32(vector)),
        )
        self.conn.commit()

    def knn(self, work_id: str, query: list[float], k: int = 5) -> list[tuple[str, float, str]]:
        """返回 [(segment_id, distance, content)],仅本书(防串味)。距离越小越近。"""
        rows = self.conn.execute(
            f"SELECT segment_id, distance, content FROM {self.table} "
            "WHERE embedding MATCH ? AND work_id = ? AND k = ? ORDER BY distance",
            (sqlite_vec.serialize_float32(query), work_id, k),
        ).fetchall()
        return [(r[0], r[1], r[2]) for r in rows]


_MODEL = {"m": None}  # 缓存 ONNX 模型(避免每次调用重载,写作路径高频)
# 中文小说优先多语模型;不可用回退默认 bge-small-en。可用环境变量覆盖。
import os as _os
_MODEL_NAME = _os.environ.get("SCRIBE_EMBED_MODEL", "")


def _get_model():
    if _MODEL["m"] is None:
        from fastembed import TextEmbedding  # 延迟导入(重依赖)
        candidates = [_MODEL_NAME] if _MODEL_NAME else [
            "BAAI/bge-small-zh-v1.5", "intfloat/multilingual-e5-small", "BAAI/bge-small-en-v1.5"]
        last = None
        for name in candidates:
            try:
                _MODEL["m"] = TextEmbedding(model_name=name) if name else TextEmbedding()
                break
            except Exception as e:  # 模型不可用则试下一个
                last = e
        if _MODEL["m"] is None:
            _MODEL["m"] = TextEmbedding()  # 最终回退默认  # noqa: 让 fastembed 报清晰错
            if last:
                pass
    return _MODEL["m"]


def embed(texts: list[str]) -> list[list[float]]:
    """文本→向量。本地 fastembed(ONNX,CPU),模型缓存。中文优先多语模型。

    可换成任意 embedding API(若拿到支持 embeddings 的 key)。火山 coding key 不支持。
    """
    try:
        model = _get_model()
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "需要嵌入提供方:`uv pip install fastembed`(本地 ONNX),"
            "或接入支持 /embeddings 的 API key。火山 coding key 不支持 embeddings。"
        ) from e
    return [list(map(float, v)) for v in model.embed(texts)]
