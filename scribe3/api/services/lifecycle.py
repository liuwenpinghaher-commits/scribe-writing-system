"""Service helpers extracted from app_impl (architecture split Phase B).

Runtime: ``app_impl._rebind_services()`` rebinds each public function into
``app_impl`` globals (monkeypatch / router rebind).  Do not call these for
side-effectful paths without going through ``scribe3.app`` / ``app_impl``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict, deque
from functools import wraps
from typing import Any, Optional


# Note: function bodies resolve free names via rebound globals on app_impl.
def _normalize_lifecycle_id(object_type: str, object_id: str) -> str:
    if object_type == "material":
        return object_id
    prefix = _OBJECT_PREFIX.get(object_type)
    if not prefix:
        raise HTTPException(status_code=404, detail=f"unsupported object type '{object_type}'")
    return object_id if object_id.startswith(prefix + ":") else f"{prefix}:{object_id}"


def _impact_token(work: str, object_type: str, object_id: str, references: list[dict]) -> str:
    raw = json.dumps(
        {"work": work, "type": object_type, "id": object_id, "references": references},
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _object_impact(st: SurrealStore, object_type: str, object_id: str, work: str) -> dict:
    normalized = _normalize_lifecycle_id(object_type, object_id)
    if object_type == "material":
        raw = st.material_lifecycle_impact(normalized)
    else:
        raw = st.record_lifecycle_impact(normalized)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"{object_type} '{object_id}' 不存在")
    references = [
        {"kind": kind, "count": count}
        for kind, count in sorted((raw.get("counts") or {}).items())
        if count
    ]
    payload = {
        "object": {
            "type": object_type,
            "id": normalized,
            "label": raw["object"].get("label") or normalized,
        },
        "references": references,
        "recommended_action": "archive" if references else "hard_delete_allowed",
    }
    payload["confirm_impact_token"] = _impact_token(work, object_type, normalized, references)
    return payload


def _delete_object_with_lifecycle(st: SurrealStore, object_type: str, object_id: str,
                                  work: str, confirm_impact_token: str | None):
    impact = _object_impact(st, object_type, object_id, work)
    has_refs = any((r.get("count") or 0) > 0 for r in impact["references"])
    if has_refs and confirm_impact_token != impact["confirm_impact_token"]:
        return JSONResponse(status_code=409, content=impact)
    normalized = impact["object"]["id"]
    if object_type == "material":
        ok = st.delete_material(normalized, cleanup_refs=True)
    else:
        ok = st.delete_record(normalized, cleanup_refs=True)
    if not ok:
        raise HTTPException(status_code=404, detail=f"{object_type} '{object_id}' 不存在")
    return {"ok": True, "impact": impact}


def _archive_object_with_lifecycle(st: SurrealStore, object_type: str, object_id: str, work: str):
    impact = _object_impact(st, object_type, object_id, work)
    normalized = impact["object"]["id"]
    if object_type == "material":
        ok = st.update_material(normalized, {"archived": True})
    else:
        if st.exists(normalized):
            st.update_record(normalized, {"archived": True})
            ok = True
        else:
            ok = False
    if not ok:
        raise HTTPException(status_code=404, detail=f"{object_type} '{object_id}' 不存在")
    return {"ok": True, "object": impact["object"], "impact": impact}

