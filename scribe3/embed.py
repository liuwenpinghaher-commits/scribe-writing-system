"""本地 CPU 中文 embedding(BAAI/bge-small-zh-v1.5,512 维)用于语义 RAG。

生产容器常无公网：须挂载预下载模型缓存(见 deploy/prod docker-compose 的
`/opt/scribe3/data/models` 与 `HF_ENDPOINT=https://hf-mirror.com`)。
首次加载会读缓存；无缓存且无网时 fail 由调用方 soft-fail。
"""
from __future__ import annotations

import hashlib
import os
import threading
from collections import OrderedDict

# 在 import huggingface/fastembed 之前配置国内镜像与缓存路径。
if not os.environ.get("HF_ENDPOINT"):
    # 腾讯云等机房直连 huggingface.co 常超时；默认走镜像，可 env 覆盖。
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
# 统一缓存目录（compose 挂载到 /models）
_default_hf = os.environ.get("SCRIBE3_HF_HOME") or os.environ.get("HF_HOME") or ""
if _default_hf:
    os.environ.setdefault("HF_HOME", _default_hf)
DEFAULT_FASTEMBED_CACHE = os.path.expanduser("~/.cache/scribe3/fastembed")


def apply_fastembed_cache_env() -> str:
    """缓存在固定目录。macOS 会清 /var/folders/.../T，隔一阵就要重下 54.6MB。"""
    if os.environ.get("FASTEMBED_CACHE_PATH"):
        return os.environ["FASTEMBED_CACHE_PATH"]
    path = os.environ.get("SCRIBE3_FASTEMBED_CACHE") or DEFAULT_FASTEMBED_CACHE
    os.environ["FASTEMBED_CACHE_PATH"] = path
    os.makedirs(path, exist_ok=True)
    return path


apply_fastembed_cache_env()

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
