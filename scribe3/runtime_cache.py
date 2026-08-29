"""本机固定缓存目录。macOS 会清 /var/folders/.../T，模型不要放那里。"""
from __future__ import annotations

import os

DEFAULT_CACHE_ROOT = os.path.expanduser("~/.cache/scribe3")
DEFAULT_JIEBA_CACHE = os.path.join(DEFAULT_CACHE_ROOT, "jieba.cache")


def apply_jieba_cache_env() -> str:
    path = os.environ.get("SCRIBE3_JIEBA_CACHE") or DEFAULT_JIEBA_CACHE
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    try:
        import jieba
        jieba.dt.cache_file = path
    except Exception:
        pass
    return path
