"""实体摘要 → proposition(attribute=codex_digest)。纯函数 + 可选落库。"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("scribe3.codex_digest")

DIGEST_ATTRIBUTE = "codex_digest"
SOURCE = "codex_digest"
_VALUE_MAX = 400

# 每种实体取哪几簇做摘要（字段簇，不是通过条件）
_KIND_GROUPS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "character": (
        ("identity", ("name", "alias", "occupation", "appearance")),
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
        if not bits:
            continue
        joined = "；".join(bits)
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
    return out


def sync_entity_digests(store: Any, kind: str, entity_id: str, row: dict[str, Any] | None) -> dict[str, int | bool]:
    from scribe3.feature_flags import flag_truthy
    if not flag_truthy("SCRIBE3_CODEX_DIGEST_SYNC"):
        return {"skipped": True, "created": 0, "updated": 0}
    payloads = digest_payloads(kind, entity_id, row)
    created = 0
    updated = 0
    upsert = getattr(store, "upsert_bridge_proposition", None)
    find = getattr(store, "find_bridge_proposition_local", None)
    if not callable(upsert):
        return {"skipped": True, "created": 0, "updated": 0, "reason": "no_store"}
    for p in payloads:
        attr = f"{DIGEST_ATTRIBUTE}:{p['field_group']}"
        existing = None
        if callable(find):
            try:
                existing = find(entity_id, attr, SOURCE)
            except Exception:
                existing = None
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
            _log.warning("digest upsert failed entity=%s group=%s err=%s", entity_id, p["field_group"], type(exc).__name__)
    return {"skipped": False, "created": created, "updated": updated}
