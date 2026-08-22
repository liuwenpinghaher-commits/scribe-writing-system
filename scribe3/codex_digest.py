"""实体摘要 → proposition(attribute=codex_digest)。纯函数 + 可选落库。"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("scribe3.codex_digest")

DIGEST_ATTRIBUTE = "codex_digest"
SOURCE = "codex_digest"
_VALUE_MAX = 200
_KEY_FIELDS = {
    "character": ("name", "gender"),
    "faction": ("name",),
    "place": ("name",),
    "item": ("name",),
}

# 每种实体取哪几簇做摘要（字段簇，不是通过条件）
_KIND_GROUPS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "character": (
        ("identity", ("name", "alias", "gender", "occupation", "appearance")),
        ("want", ("surface_goal", "deep_need", "fear")),
        ("voice", ("speech_style", "personality_detail")),
    ),
    "faction": (
        ("identity", ("name", "ideology", "status")),
        ("agenda", ("secret_agenda", "origin")),
    ),
    "place": (
        ("identity", ("name", "description", "rules")),
    ),
    "item": (
        ("identity", ("name", "function", "origin")),
    ),
}


def _clip(value: object) -> str:
    text = value if isinstance(value, str) else str(value or "")
    text = " ".join(text.split())
    if len(text) > _VALUE_MAX:
        text = text[:_VALUE_MAX] + "…"
    return text


def digest_payloads(kind: str, entity_id: str, row: dict[str, Any] | None) -> list[dict[str, str]]:
    """一实体可多条：总摘 + 字段簇。不落库。"""
    data = row if isinstance(row, dict) else {}
    groups = _KIND_GROUPS.get(str(kind or ""), ())
    out: list[dict[str, str]] = []
    total_parts: list[str] = []
    for group, keys in groups:
        bits: list[str] = []
        for key in keys:
            val = _clip(data.get(key) or "")
            if val:
                bits.append(f"{key}：{val}")
        if group == "identity" and any(_has_secret_mark(data, k) for k in data):
            bits.append("secret：标了私密")
        if not bits:
            continue
        joined = _clip("；".join(bits))
        total_parts.append(joined)
        out.append({
            "attribute": DIGEST_ATTRIBUTE,
            "field_group": group,
            "value": joined,
            "source_entity": entity_id,
            "entity_id": entity_id,
        })
    if total_parts:
        out.insert(0, {
            "attribute": DIGEST_ATTRIBUTE,
            "field_group": "all",
            "value": " / ".join(total_parts)[:_VALUE_MAX],
            "source_entity": entity_id,
            "entity_id": entity_id,
        })
    aliases = data.get("alias") or data.get("aliases") or data.get("aka")
    if aliases:
        out.append({
            "attribute": DIGEST_ATTRIBUTE,
            "field_group": "alias",
            "value": _clip(aliases),
            "source_entity": entity_id,
            "entity_id": entity_id,
        })
    blob = " ".join(p.get("value") or "" for p in out)
    if not _keys_preserved(kind, data, blob):
        _log.warning("digest key-fields missing, fallback raw identity entity=%s", entity_id)
        raw_bits = []
        for key in _KEY_FIELDS.get(str(kind or ""), ("name",)):
            val = _clip(data.get(key) or "")
            if val:
                raw_bits.append(f"{key}：{val}")
        if any(_has_secret_mark(data, k) for k in data):
            raw_bits.append("secret：标了私密")
        fallback = "；".join(raw_bits)[:_VALUE_MAX] or _clip(data.get("name") or entity_id)
        return [{
            "attribute": DIGEST_ATTRIBUTE,
            "field_group": "raw",
            "value": fallback,
            "source_entity": entity_id,
            "entity_id": entity_id,
        }]
    return out


def _has_secret_mark(data: dict[str, Any], key: str) -> bool:
    k = str(key)
    return k.endswith("_secret") and bool(data.get(key))


def _keys_preserved(kind: str, data: dict[str, Any], blob: str) -> bool:
    for key in _KEY_FIELDS.get(str(kind or ""), ()):
        val = str(data.get(key) or "").strip()
        if val and val not in blob:
            return False
    secret_on = any(_has_secret_mark(data, k) for k in data)
    if secret_on and "私密" not in blob and "secret" not in blob.lower():
        # 不把秘密正文写进摘要，只要求标记还在
        marked = any(str(k).endswith("_secret") and str(k).replace("_secret", "") in blob for k in data)
        if not marked:
            return False
    return True


def sync_entity_digests(store: Any, kind: str, entity_id: str, row: dict[str, Any] | None) -> dict[str, int | bool]:
    from scribe3.feature_flags import flag_truthy
    if not flag_truthy("SCRIBE3_CODEX_DIGEST_SYNC"):
        return {"skipped": True, "created": 0, "updated": 0}
    payloads = digest_payloads(kind, entity_id, row)
    created = 0
    updated = 0
    failed = 0
    upsert = getattr(store, "upsert_bridge_proposition", None)
    find = getattr(store, "find_bridge_proposition_local", None)
    if not callable(upsert):
        return {"skipped": True, "created": 0, "updated": 0, "failed": 0, "reason": "no_store"}
    prepared: list[tuple[dict[str, str], Any]] = []
    for p in payloads:
        attr = f"{DIGEST_ATTRIBUTE}:{p['field_group']}"
        existing = None
        if callable(find):
            try:
                existing = find(entity_id, attr, SOURCE)
            except Exception:
                existing = None
        prepared.append((p, existing))
    for p, existing in prepared:
        attr = f"{DIGEST_ATTRIBUTE}:{p['field_group']}"
        try:
            upsert(
                local=existing,
                entity_id=entity_id,
                attribute=attr,
                value=p["value"],
                source=SOURCE,
            )
            if existing:
                updated += 1
            else:
                created += 1
        except Exception as exc:
            failed += 1
            _log.warning("digest upsert failed entity=%s group=%s err=%s", entity_id, p["field_group"], type(exc).__name__)
    return {
        "skipped": False,
        "created": created,
        "updated": updated,
        "failed": failed,
        "ok": failed == 0,
    }
