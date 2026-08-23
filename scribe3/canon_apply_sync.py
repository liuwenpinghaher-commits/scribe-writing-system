"""CRS-02：正典 Apply 成功后统一同步 digest / 限知桥 / 语义索引。"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("scribe3.canon_apply_sync")

_KIND_GETTERS = {
    "faction": ("get_faction", "faction"),
    "character": ("entity", "role"),
    "item": ("get_item", "item"),
    "term": ("get_term", "term"),
    "world_rule": ("get_world_rule", "world_rule"),
}


def after_canon_apply(store: Any, kind: str, entity_id: str, row: dict | None = None) -> dict[str, Any]:
    """失败 fail-soft，不回滚已经写进正典的那一行。"""
    stats: dict[str, Any] = {"kind": kind, "entity_id": entity_id}
    data = row if isinstance(row, dict) else {}
    if not data:
        data = _read_row(store, kind, entity_id) or {}
    try:
        from scribe3.codex_digest import sync_entity_digests
        stats["digest"] = sync_entity_digests(store, kind, entity_id, data)
    except Exception as e:
        _log.warning("after_canon_apply digest fail %s %s: %s", kind, entity_id, e)
        stats["digest_error"] = type(e).__name__
    try:
        if kind == "faction":
            from scribe3.codex_secret_bridge import sync_faction_secrets
            name = str(entity_id).split(":")[-1]
            stats["secrets"] = sync_faction_secrets(store, name, data)
        elif kind == "character":
            from scribe3.codex_secret_bridge import sync_role_secrets
            stats["secrets"] = sync_role_secrets(store, entity_id, data)
    except Exception as e:
        _log.warning("after_canon_apply secrets fail %s %s: %s", kind, entity_id, e)
        stats["secrets_error"] = type(e).__name__
    if kind != "fact":
        try:
            text = _index_blob(data)
            if text:
                embed_entity(store, entity_id, text)
                stats["indexed"] = True
        except Exception as e:
            _log.warning("after_canon_apply index fail %s %s: %s", kind, entity_id, e)
            stats["index_error"] = type(e).__name__
    return stats


def embed_entity(store: Any, entity_id: str, text: str) -> None:
    """非 fact 实体 Apply 后走与 fact 同一套语义索引。"""
    indexer = getattr(store, "semantic_index", None)
    if callable(indexer) and text:
        indexer(entity_id, text)


def _read_row(store: Any, kind: str, entity_id: str) -> dict | None:
    spec = _KIND_GETTERS.get(kind)
    if not spec:
        return None
    method, _prefix = spec
    fn = getattr(store, method, None)
    if not callable(fn):
        return None
    name = str(entity_id).split(":")[-1]
    try:
        row = fn(entity_id) if method == "entity" else fn(name)
    except Exception:
        return None
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    traits = getattr(row, "traits", None)
    name_v = getattr(row, "name", None)
    if isinstance(traits, dict):
        return {"name": name_v, **traits}
    return None


def _index_blob(row: dict) -> str:
    parts = []
    for key in ("name", "description", "definition", "ideology", "appearance", "cost"):
        val = row.get(key)
        if val:
            parts.append(str(val))
    return " ".join(parts).strip()
