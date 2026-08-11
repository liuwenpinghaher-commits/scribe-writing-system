"""Benchmark / 参考作品库（O32 · 默认 JSON 落盘 · 无 Surreal 迁移）。"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_MEM: dict[str, dict[str, Any]] = {}
_LOADED = False


def benchmark_lib_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_BENCHMARK_LIB") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def default_benchmark_path() -> str:
    """默认落盘：SCRIBE3_BENCHMARK_PATH > SCRIBE3_DATA_DIR/benchmarks.json > ~/.scribe3/benchmarks.json。"""
    env = (os.environ.get("SCRIBE3_BENCHMARK_PATH") or "").strip()
    if env:
        return env
    data = (os.environ.get("SCRIBE3_DATA_DIR") or "").strip()
    if data:
        return str(Path(data) / "benchmarks.json")
    return str(Path.home() / ".scribe3" / "benchmarks.json")


def _path() -> str:
    return default_benchmark_path()


def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    _load_disk()
    _LOADED = True


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
        parent = os.path.dirname(path) or "."
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_MEM, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def list_benchmarks() -> list[dict[str, Any]]:
    with _LOCK:
        _ensure_loaded()
        return sorted(_MEM.values(), key=lambda x: str(x.get("title") or ""))


def get_benchmark(bid: str) -> dict[str, Any] | None:
    with _LOCK:
        _ensure_loaded()
        return dict(_MEM[bid]) if bid in _MEM else None


def upsert_benchmark(entry: dict[str, Any]) -> dict[str, Any]:
    """新增或更新。字段：id?, title, notes, tags[], beats_sample? 真落盘。"""
    with _LOCK:
        _ensure_loaded()
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
            "path": _path(),
        }
        _MEM[eid] = row
        _save_disk()
        return dict(row)


def delete_benchmark(bid: str) -> bool:
    with _LOCK:
        _ensure_loaded()
        if bid in _MEM:
            _MEM.pop(bid, None)
            _save_disk()
            return True
        return False


def clear_benchmarks_for_tests() -> None:
    global _LOADED
    with _LOCK:
        _MEM.clear()
        _LOADED = False
