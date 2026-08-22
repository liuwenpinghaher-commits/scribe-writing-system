"""Benchmark / 参考作品库（O32 · 默认 JSON 落盘 · 无 Surreal 迁移）。"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
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
    raw = (get_flag("SCRIBE3_BENCHMARK_LIB") or "1").strip().lower()
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


BENCHMARK_ADVISORY_MAX_CHARS = 800
BENCHMARK_ADVISORY_HEADER = "【对照参考·禁止仿写专名与原句】\n"


def benchmark_inject_enabled() -> bool:
    raw = (get_flag("SCRIBE3_BENCHMARK_INJECT") or "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def sanitize_benchmark_advisory_text(text: str) -> str:
    """跳过不安全仿写/书名号大段；复用 reference_craft 启发式。"""
    import re
    try:
        from scribe3.reference_craft import _UNSAFE_MECHANISM, _QUOTED_TEXT
    except Exception:
        _UNSAFE_MECHANISM = re.compile(r"(?:模仿|仿写|复刻|照搬|复制|套用|原句)")
        _QUOTED_TEXT = re.compile(r"[《》〈〉\"“”‘’]")
    t = " ".join(str(text or "").split()).strip()
    if not t:
        return ""
    if _UNSAFE_MECHANISM.search(t):
        # 剥掉危险句段，保留其余
        parts = re.split(r"[。！？\n]", t)
        keep = [p for p in parts if p.strip() and not _UNSAFE_MECHANISM.search(p)]
        t = "。".join(keep).strip()
    # 去掉长引号块
    t = re.sub(r"[「『\"].{20,}?[」』\"]", "…", t)
    if _QUOTED_TEXT.search(t) and len(t) > 200:
        t = _QUOTED_TEXT.sub("", t)
    return t[:BENCHMARK_ADVISORY_MAX_CHARS]


def build_advisory_preview(bid: str) -> dict[str, Any]:
    row = get_benchmark(bid)
    if not row:
        return {
            "id": bid,
            "ok": False,
            "error": "not_found",
            "advisory_only": True,
            "not_auto_write_prose": True,
        }
    body_bits = []
    if row.get("notes"):
        body_bits.append(str(row["notes"]))
    sample = row.get("beats_sample")
    if isinstance(sample, list):
        body_bits.append("；".join(str(x) for x in sample[:8] if x))
    elif sample:
        body_bits.append(str(sample)[:400])
    raw = "\n".join(body_bits) or str(row.get("title") or "")
    text = BENCHMARK_ADVISORY_HEADER + sanitize_benchmark_advisory_text(raw)
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "text": text,
        "tokens_est": max(1, len(text) // 2),
        "advisory_only": True,
        "not_auto_write_prose": True,
        "ok": True,
        "surface": "benchmark.advisory_preview",
    }


def build_benchmark_inject_segment(
    work: str = "main",
    *,
    limit: int = 2,
) -> str:
    """写路径用：旗关返回空；开则拼接最多 limit 条 advisory。"""
    if not benchmark_inject_enabled():
        return ""
    items = list_benchmarks()[: max(0, int(limit or 2))]
    if not items:
        return ""
    chunks = []
    for it in items:
        prev = build_advisory_preview(str(it.get("id") or ""))
        if prev.get("ok") and prev.get("text"):
            chunks.append(str(prev["text"]))
    if not chunks:
        return ""
    body = "\n\n".join(chunks)
    return body[: BENCHMARK_ADVISORY_MAX_CHARS * 2]


def upsert_benchmark(entry: dict[str, Any]) -> dict[str, Any]:
    """新增或更新。字段：id?, title, notes, tags[], beats_sample?, reference_work_id?"""
    with _LOCK:
        _ensure_loaded()
        eid = str(entry.get("id") or "").strip() or uuid.uuid4().hex[:12]
        row = {
            "id": eid,
            "title": str(entry.get("title") or "未命名").strip() or "未命名",
            "notes": str(entry.get("notes") or ""),
            "tags": list(entry.get("tags") or []),
            "beats_sample": entry.get("beats_sample"),
            "reference_work_id": (
                str(entry.get("reference_work_id") or "").strip() or None
            ),
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
