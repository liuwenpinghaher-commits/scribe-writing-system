"""SessionEntity · 讨论产物草稿（非正典，work 隔离）。"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from copy import deepcopy
from typing import Any

_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}  # work -> {drafts: {id: draft}}


def _key(work: str) -> str:
    return f"orch_session_drafts:{(work or 'main')}"


def _load(work: str) -> dict[str, Any]:
    w = work or "main"
    if w in _cache:
        return _cache[w]
    blob: dict[str, Any] = {"drafts": {}}
    try:
        from scribe3 import settings_store
        raw = settings_store.get_override(_key(w))
        if raw:
            data = json.loads(raw)
            if isinstance(data, dict) and isinstance(data.get("drafts"), dict):
                blob = data
    except Exception:
        pass
    _cache[w] = blob
    return blob


def _save(work: str) -> None:
    w = work or "main"
    blob = _cache.get(w) or {"drafts": {}}
    try:
        from scribe3 import settings_store
        settings_store.set_override(_key(w), json.dumps(blob, ensure_ascii=False))
    except Exception:
        pass


def clear_ram() -> None:
    with _lock:
        _cache.clear()


def clear_work(work: str = "main", *, disk: bool = True) -> None:
    w = work or "main"
    with _lock:
        _cache.pop(w, None)
        if disk:
            try:
                from scribe3 import settings_store
                settings_store.delete_override(_key(w))
            except Exception:
                pass


def list_drafts(work: str = "main") -> list[dict[str, Any]]:
    with _lock:
        drafts = _load(work).get("drafts") or {}
        return [deepcopy(v) for v in drafts.values()]


def get_draft(work: str, draft_id: str) -> dict[str, Any] | None:
    with _lock:
        d = (_load(work).get("drafts") or {}).get(draft_id)
        return deepcopy(d) if d else None


def find_by_label(work: str, label: str, object_type: str | None = None) -> dict[str, Any] | None:
    lab = (label or "").strip()
    if not lab:
        return None
    with _lock:
        for d in (_load(work).get("drafts") or {}).values():
            if object_type and d.get("object_type") != object_type:
                continue
            if d.get("label") == lab or lab in (d.get("aliases") or []):
                return deepcopy(d)
    return None


def upsert_draft(
    work: str,
    *,
    object_type: str,
    label: str,
    fields: dict[str, Any] | None = None,
    aliases: list[str] | None = None,
    draft_id: str | None = None,
    status: str = "drafting",
) -> dict[str, Any]:
    """创建或合并会话草稿（非正典）。"""
    lab = (label or "").strip()
    if not lab:
        raise ValueError("draft label required")
    ot = object_type or "character"
    with _lock:
        blob = _load(work)
        drafts = blob.setdefault("drafts", {})
        existing = None
        if draft_id and draft_id in drafts:
            existing = drafts[draft_id]
        else:
            for d in drafts.values():
                if d.get("object_type") == ot and d.get("label") == lab:
                    existing = d
                    break
        if existing:
            row = deepcopy(existing)
            if fields:
                merged = dict(row.get("fields") or {})
                merged.update(fields)
                row["fields"] = merged
            if aliases:
                als = list(row.get("aliases") or [])
                for a in aliases:
                    if a and a not in als:
                        als.append(a)
                row["aliases"] = als
            row["status"] = status or row.get("status") or "drafting"
            row["updated_at"] = int(time.time())
            drafts[row["draft_id"]] = row
            _save(work)
            return deepcopy(row)
        did = draft_id or f"draft:{ot[:4]}:{uuid.uuid4().hex[:10]}"
        row = {
            "draft_id": did,
            "work": work or "main",
            "object_type": ot,
            "label": lab,
            "aliases": list(aliases or []),
            "fields": dict(fields or {}),
            "status": status or "drafting",
            "canon": False,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        drafts[did] = row
        _save(work)
        return deepcopy(row)


def mark_status(work: str, draft_id: str, status: str) -> dict[str, Any] | None:
    with _lock:
        blob = _load(work)
        d = (blob.get("drafts") or {}).get(draft_id)
        if not d:
            return None
        d["status"] = status
        d["updated_at"] = int(time.time())
        if status == "approved":
            d["canon"] = True  # 标记已走正典路径（真正写库仍在 executor）
        _save(work)
        return deepcopy(d)


# —— 规则抽取 ——

_STOP = r"的|之|与|和|被|把|将|给|向|在|从|为|写入|设定|档案|恐惧|欲望|外貌|，|,|。|、"

_NAME_PATTERNS = (
    r"主角草案[：:\s]*([一-龥]{2,4})",
    r"([一-龥]{2,4})（暂定名）",
    r"(?:名叫|名为|叫做|定名)[：:\s]*([一-龥]{2,4})",
    r"(?:角色|人物)[·:：\s]*([一-龥A-Za-z0-9]{1,12})",
    r"主角(?!草案)[·:：\s]*([一-龥]{2,4})",
)

_PSEUDO = frozenset({
    "设定", "本身", "档案", "关系", "列表", "主角", "配角", "角色", "人物", "草案",
})


def _cut_name(raw: str) -> str:
    raw = (raw or "").strip()
    m = re.match(rf"^(.+?)(?:{_STOP}|$)", raw)
    name = (m.group(1) if m else raw).strip()
    if re.fullmatch(r"[一-龥]+", name):
        name = name[:4]
    return name


def extract_named_entities(message: str, *, object_type_hint: str | None = None) -> list[dict[str, Any]]:
    """从消息规则抽取可成草稿的专名。"""
    text = message or ""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    ot = object_type_hint or "character"
    for pat in _NAME_PATTERNS:
        for m in re.finditer(pat, text):
            name = _cut_name(m.group(1) or "")
            if not name or name in _PSEUDO or name in seen:
                continue
            seen.add(name)
            found.append({"object_type": ot if ot != "proposition" else "character", "label": name, "fields": {"name": name}})
    # 势力
    if re.search(r"势力|门派|组织", text):
        m = re.search(r"(?:势力|门派|组织)[·:：\s「『]*([一-龥]{2,8})", text)
        if m:
            name = _cut_name(m.group(1))
            if name not in _PSEUDO and name not in seen:
                found.append({"object_type": "faction", "label": name, "fields": {"name": name}})
    return found


def upsert_from_message(
    work: str,
    message: str,
    *,
    object_type_hint: str | None = None,
) -> list[dict[str, Any]]:
    """抽取并 upsert；返回本轮触达的草稿列表。"""
    out: list[dict[str, Any]] = []
    for ent in extract_named_entities(message, object_type_hint=object_type_hint):
        row = upsert_draft(
            work,
            object_type=ent["object_type"],
            label=ent["label"],
            fields=ent.get("fields"),
        )
        out.append(row)
    return out
