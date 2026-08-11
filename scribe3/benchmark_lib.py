"""Benchmark / 参考作品库（O32 · 进程内 + 可选 JSON 文件 · 无 Surreal 迁移）。"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any

_LOCK = threading.Lock()
_MEM: dict[str, dict[str, Any]] = {}


def benchmark_lib_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_BENCHMARK_LIB") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _path() -> str | None:
    p = (os.environ.get("SCRIBE3_BENCHMARK_PATH") or "").strip()
    return p or None


def _load_disk() -> None:
    path = _path()
    if not path or not os.path.isfile(path):
        return
    try:
        data = json.loads(open(path, encoding="utf-8").read())
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    _MEM[str(k)] = v
    except Exception:
        pass


def _save_disk() -> None:
    path = _path()
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_MEM, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def list_benchmarks() -> list[dict[str, Any]]:
    with _LOCK:
        if not _MEM and _path():
            _load_disk()
        return sorted(_MEM.values(), key=lambda x: str(x.get("title") or ""))


def get_benchmark(bid: str) -> dict[str, Any] | None:
    with _LOCK:
        return dict(_MEM[bid]) if bid in _MEM else None


def upsert_benchmark(entry: dict[str, Any]) -> dict[str, Any]:
    """新增或更新。字段：id?, title, notes, tags[], beats_sample?"""
    with _LOCK:
        if not _MEM and _path():
            _load_disk()
        eid = str(entry.get("id") or "").strip() or uuid.uuid4().hex[:12]
        row = {
            "id": eid,
            "title": str(entry.get("title") or "未命名").strip() or "未命名",
            "notes": str(entry.get("notes") or ""),
            "tags": list(entry.get("tags") or []),
            "beats_sample": entry.get("beats_sample"),
            "updated_at": time.time(),
            "advisory_only": True,
            "not_auto_write_prose": True,
        }
        _MEM[eid] = row
        _save_disk()
        return dict(row)


def delete_benchmark(bid: str) -> bool:
    with _LOCK:
        if bid in _MEM:
            _MEM.pop(bid, None)
            _save_disk()
            return True
        return False


def clear_benchmarks_for_tests() -> None:
    with _LOCK:
        _MEM.clear()
