"""移植自 scribe2/embed.py:本地 CPU 中文优化 embedding(无网络/无 key)。
BAAI/bge-small-zh-v1.5,512 维。用于设定/命题的语义 RAG 召回。

Task 16-B 缓存(做实):按 sha256(normalized_text) + model_version 缓存向量。捕获恒开、
每轮 add_memory_item / memory_vector / _material_index_fields 都会 embed,重复文本(同一句
设定/命题/查询)命中缓存即省一次真实前向,是当前生产价值最高的一处缓存。
规范化仅折叠空白(内容不同 → sha256 不同 → 各自单独算,内容保真);换模型时 model_version
进键 → 旧向量键自然失效,绝不把旧模型向量返给新模型。
"""
import hashlib
import threading
from collections import OrderedDict

_model = None
_MODEL_NAME = "BAAI/bge-small-zh-v1.5"

# 缓存:key = f"{model_version()}:{sha256(normalized_text)}" → 向量。
_CACHE: "OrderedDict[str, list]" = OrderedDict()
_CACHE_MAX = 4096
_LOCK = threading.RLock()
_stats = {"hits": 0, "misses": 0}


def model_version() -> str:
    """当前 embedding 模型版本标识(进缓存键;换模型即令旧缓存键失效)。"""
    return _MODEL_NAME


def _m():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=_MODEL_NAME)
    return _model


def _compute(texts: list[str]) -> list[list[float]]:
    """真实前向(隔离成可 monkeypatch 的接缝:测试免加载 fastembed 模型)。"""
    return [list(map(float, v)) for v in _m().embed(texts)]


def _normalize(text: str) -> str:
    return " ".join((text or "").split())


def _key(text: str) -> str:
    digest = hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()
    return f"{model_version()}:{digest}"


def embed(texts: list[str]) -> list[list[float]]:
    """批量 embedding,带 sha256+model_version 缓存:命中项直接取缓存,只把未命中项送算。
    返回顺序与输入对齐;缓存的向量对应【规范化后】文本(空白折叠,内容保真)。"""
    out: list = [None] * len(texts)
    to_compute: list[str] = []
    slots: list[tuple[int, str]] = []
    with _LOCK:
        for i, t in enumerate(texts):
            k = _key(t)
            v = _CACHE.get(k)
            if v is not None:
                _CACHE.move_to_end(k)
                _stats["hits"] += 1
                out[i] = v
            else:
                _stats["misses"] += 1
                to_compute.append(_normalize(t))
                slots.append((i, k))
    if to_compute:
        computed = _compute(to_compute)
        with _LOCK:
            for (i, k), v in zip(slots, computed):
                out[i] = v
                _CACHE[k] = v
                _CACHE.move_to_end(k)
                while len(_CACHE) > _CACHE_MAX:
                    _CACHE.popitem(last=False)
    return out


def dim() -> int:
    return len(embed(["probe"])[0])


def cache_stats() -> dict:
    with _LOCK:
        return {"size": len(_CACHE), **_stats}


def clear_cache() -> None:
    with _LOCK:
        _CACHE.clear()
        _stats["hits"] = 0
        _stats["misses"] = 0
