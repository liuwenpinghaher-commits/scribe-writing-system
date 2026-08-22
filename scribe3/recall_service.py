"""统一召回中枢。影子期只记 diff，不改写章输出。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger("scribe3.recall_service")

_BUDGET_BY_TAG = {
    "playbook_codex": 400,
    "discuss_codex": 800,
    "canonical": 600,
}


@dataclass
class RecallHit:
    entity_id: str
    attribute: str
    value: str
    channel: str
    score: float = 0.0
    secret: bool = False


@dataclass
class RecallPack:
    hits: list[RecallHit] = field(default_factory=list)
    skip_reason: str = ""
    budget_tag: str = ""
    channels: list[str] = field(default_factory=list)


def _fact_get(f: Any, key: str, default: Any = None) -> Any:
    if isinstance(f, dict):
        return f.get(key, default)
    return getattr(f, key, default)


def _as_hit(f: Any, channel: str, score: float = 0.0) -> RecallHit | None:
    val = str(_fact_get(f, "value") or "").strip()
    if not val:
        return None
    secret = bool(_fact_get(f, "secret") is True)
    return RecallHit(
        entity_id=str(_fact_get(f, "entity_id") or ""),
        attribute=str(_fact_get(f, "attribute") or ""),
        value=val,
        channel=channel,
        score=score,
        secret=secret,
    )


def _rrf(packs: list[list[RecallHit]], k: int = 60) -> list[RecallHit]:
    scores: dict[tuple[str, str, str], float] = {}
    keep: dict[tuple[str, str, str], RecallHit] = {}
    for hits in packs:
        for i, h in enumerate(hits):
            key = (h.entity_id, h.attribute, h.value)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + i + 1)
            keep.setdefault(key, h)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    out: list[RecallHit] = []
    for key, sc in ranked:
        h = keep[key]
        out.append(RecallHit(h.entity_id, h.attribute, h.value, h.channel, sc, h.secret))
    return out


def recall(
    store: Any,
    *,
    chapter: int,
    focalizer: str = "",
    query: str = "",
    budget_tag: str = "playbook_codex",
    work: str | None = None,
) -> RecallPack:
    """六段中的可落地部分：语义/BM25/图；时态+限知 fail-closed。直取槽不接管。"""
    from scribe3.feature_flags import flag_truthy
    cap = _BUDGET_BY_TAG.get(budget_tag, 400)
    channels: list[str] = []
    packs: list[list[RecallHit]] = []
    q = " ".join([str(query or "").strip(), str(focalizer or "").replace("role:", "")]).strip()

    hybrid = getattr(store, "hybrid_recall", None)
    semantic = getattr(store, "semantic_recall", None)
    if callable(hybrid) and q:
        try:
            rows = list(hybrid(q, int(chapter), k=8) or [])
            hits = [h for h in (_as_hit(f, "hybrid") for f in rows) if h and not h.secret]
            packs.append(hits)
            channels.append("hybrid")
        except Exception as exc:
            _log.info("recall hybrid skip: %s", type(exc).__name__)
    elif callable(semantic) and q:
        try:
            rows = list(semantic(q, k=8, chapter=int(chapter)) or [])
            hits = [h for h in (_as_hit(f, "semantic") for f in rows) if h and not h.secret]
            packs.append(hits)
            channels.append("semantic")
        except Exception as exc:
            _log.info("recall semantic skip: %s", type(exc).__name__)

    if flag_truthy("SCRIBE3_GRAPH_RELATION_RECALL"):
        graph_fn = getattr(store, "relation_recall", None)
        if callable(graph_fn) and focalizer:
            try:
                rows = list(graph_fn(str(focalizer).replace("role:", ""), hops=2, chapter=int(chapter)) or [])
                hits = [h for h in (_as_hit(f, "graph") for f in rows) if h and not h.secret]
                packs.append(hits)
                channels.append("graph")
            except Exception as exc:
                _log.info("recall graph skip: %s", type(exc).__name__)

    fused = _rrf(packs) if packs else []
    if not fused:
        return RecallPack(hits=[], skip_reason="empty", budget_tag=budget_tag, channels=channels)
    text_acc = 0
    kept: list[RecallHit] = []
    for h in fused:
        n = len(h.value)
        if text_acc + n > cap and kept:
            break
        kept.append(h)
        text_acc += n
    return RecallPack(hits=kept, skip_reason="", budget_tag=budget_tag, channels=channels)


def pack_text(pack: RecallPack) -> str:
    if not pack.hits:
        return ""
    lines = ["这些已经为真，不许另造。"]
    for h in pack.hits:
        eid = h.entity_id.replace("role:", "")
        attr = h.attribute
        lines.append(f"{eid} / {attr}：{h.value}" if attr else f"{eid}：{h.value}")
    return "\n".join(lines)


def shadow_diff(store: Any, seq: int, focalizer: str, legacy_text: str, query: str = "") -> dict[str, Any]:
    """并行算影子，输出不变。默认不走向量（避免写章路径加载 embedding）。"""
    try:
        facts_fn = getattr(store, "facts_at", None)
        hits: list[RecallHit] = []
        if callable(facts_fn):
            rows = list(facts_fn(int(seq)) or [])
            for f in rows:
                h = _as_hit(f, "facts_at")
                if h and not h.secret:
                    hits.append(h)
        pack = RecallPack(hits=hits[:8], skip_reason="" if hits else "empty", budget_tag="playbook_codex", channels=["facts_at"] if hits else [])
    except Exception as exc:
        rec = {"ok": False, "error": type(exc).__name__, "seq": int(seq)}
        _log.info("recall_shadow fail %s", rec)
        return rec
    shadow = pack_text(pack)
    legacy_ids = set()
    for line in str(legacy_text or "").splitlines():
        if " / " in line:
            legacy_ids.add(line.split(" / ", 1)[0].strip())
    shadow_ids = {h.entity_id.replace("role:", "") for h in pack.hits}
    rec = {
        "ok": True,
        "seq": int(seq),
        "legacy_len": len(legacy_text or ""),
        "shadow_len": len(shadow or ""),
        "channels": pack.channels,
        "skip": pack.skip_reason,
        "legacy_ids": sorted(legacy_ids),
        "shadow_ids": sorted(shadow_ids),
        "same_entities": legacy_ids == shadow_ids,
    }
    _log.info("recall_shadow %s", rec)
    try:
        from scribe3.pipeline_trace_hooks import note_guide_missing
        if pack.skip_reason:
            note_guide_missing(f"recall_shadow:{pack.skip_reason}")
    except Exception:
        pass
    return rec
