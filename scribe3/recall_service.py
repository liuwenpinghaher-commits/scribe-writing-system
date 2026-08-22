"""统一召回中枢。影子期只记 diff，不改写章输出。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger("scribe3.recall_service")

_BUDGET_BY_TAG = {
    "playbook_codex": 800,
    "discuss_codex": 800,
    "canonical": 600,
    "volume_intro": 400,
    "ledger": 900,
}

_SHADOW_RING: list[dict[str, Any]] = []
_SHADOW_RING_MAX = 500


def budget_for(tag: str, default: int = 400) -> int:
    """召回/组装预算单源。未登记的 tag 用 default。"""
    try:
        return int(_BUDGET_BY_TAG.get(str(tag or ""), default))
    except (TypeError, ValueError):
        return int(default)


def record_shadow_stat(rec: dict[str, Any] | None) -> None:
    if not isinstance(rec, dict) or rec.get("ok") is False:
        return
    _SHADOW_RING.append({
        "path": str(rec.get("path") or ""),
        "threshold_ok": bool(rec.get("threshold_ok")),
        "secret_leak_count": int(rec.get("secret_leak_count") or 0),
        "channels": list(rec.get("channels") or []),
        "seq": rec.get("seq"),
    })
    overflow = len(_SHADOW_RING) - _SHADOW_RING_MAX
    if overflow > 0:
        del _SHADOW_RING[:overflow]


def summarize_recall_shadow(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """按 path 分组的 threshold_ok 通过率。无 rows 则读进程内环。"""
    items = rows if rows is not None else list(_SHADOW_RING)
    by_path: dict[str, dict[str, Any]] = {}
    for rec in items:
        if not isinstance(rec, dict):
            continue
        path = str(rec.get("path") or "unknown") or "unknown"
        bucket = by_path.setdefault(path, {"n": 0, "ok": 0, "secret_leak": 0, "vector_n": 0})
        bucket["n"] += 1
        if rec.get("threshold_ok"):
            bucket["ok"] += 1
        bucket["secret_leak"] += int(rec.get("secret_leak_count") or 0)
        chans = rec.get("channels") or []
        if any(c in ("hybrid", "semantic", "vector") for c in chans):
            bucket["vector_n"] += 1
    grouped = {}
    for path, b in by_path.items():
        n = int(b["n"] or 0)
        grouped[path] = {
            "n": n,
            "threshold_ok_rate": round((b["ok"] / n) if n else 0.0, 4),
            "secret_leak_sum": int(b["secret_leak"]),
            "vector_n": int(b["vector_n"]),
        }
    return {"by_path": grouped, "n": sum(int(b["n"]) for b in grouped.values())}


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
    needles = [p for p in q.split() if len(p) >= 2]

    facts_fn = getattr(store, "facts_at", None)
    if callable(facts_fn):
        try:
            rows = list(facts_fn(int(chapter)) or [])
            hits = [h for h in (_as_hit(f, "facts_at") for f in rows) if h and not h.secret]
            if needles:
                hits = [
                    h for h in hits
                    if any(n in f"{h.entity_id}|{h.attribute}|{h.value}" for n in needles)
                ]
            if hits:
                packs.append(hits)
            channels.append("facts_at")
        except Exception as exc:
            _log.info("recall facts_at skip: %s", type(exc).__name__)

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
            try:
                from scribe3.pipeline_trace_hooks import note_guide_missing
                note_guide_missing("recall_hybrid_skip")
            except Exception:
                pass
    elif callable(semantic) and q:
        try:
            rows = list(semantic(q, k=8, chapter=int(chapter)) or [])
            hits = [h for h in (_as_hit(f, "semantic") for f in rows) if h and not h.secret]
            packs.append(hits)
            channels.append("semantic")
        except Exception as exc:
            _log.info("recall semantic skip: %s", type(exc).__name__)
            try:
                from scribe3.pipeline_trace_hooks import note_guide_missing
                note_guide_missing("recall_semantic_skip")
            except Exception:
                pass

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
                try:
                    from scribe3.pipeline_trace_hooks import note_guide_missing
                    note_guide_missing("recall_graph_skip")
                except Exception:
                    pass

    fused = _rrf(packs) if packs else []
    if fused:
        try:
            from scribe3.feature_flags import flag_truthy as _ft
            if _ft("SCRIBE3_EPISTEMIC_ORACLE") and focalizer and str(focalizer).strip() not in (
                "", "chief", "author", "主编",
            ):
                from scribe3.epistemic import visible_to
                allow = set(visible_to(store, work or "", int(chapter), focalizer))
                if allow:
                    visible_blobs: set[str] = set()
                    facts_fn2 = getattr(store, "facts_at", None)
                    if callable(facts_fn2):
                        for f in list(facts_fn2(int(chapter)) or []):
                            fid = str(_fact_get(f, "id") or "")
                            if fid and fid in allow:
                                visible_blobs.add(
                                    f"{_fact_get(f, 'entity_id') or ''}|{_fact_get(f, 'value') or ''}"
                                )
                    if visible_blobs:
                        fused = [
                            h for h in fused
                            if f"{h.entity_id}|{h.value}" in visible_blobs
                        ]
        except Exception as exc:
            _log.info("recall epistemic skip: %s", type(exc).__name__)
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


def shadow_diff(
    store: Any, seq: int, focalizer: str, legacy_text: str, query: str = "",
    path: str = "",
) -> dict[str, Any]:
    """并行算影子，输出不变。默认不走向量；开 SCRIBE3_RECALL_SHADOW_VECTOR 纳入对照。"""
    try:
        from scribe3.feature_flags import flag_truthy
        facts_fn = getattr(store, "facts_at", None)
        hits: list[RecallHit] = []
        channels: list[str] = []
        if callable(facts_fn):
            rows = list(facts_fn(int(seq)) or [])
            for f in rows:
                h = _as_hit(f, "facts_at")
                if h and not h.secret:
                    hits.append(h)
            if hits:
                channels.append("facts_at")
        if flag_truthy("SCRIBE3_RECALL_SHADOW_VECTOR"):
            vec = recall(
                store,
                chapter=int(seq),
                focalizer=focalizer,
                query=query or focalizer,
                budget_tag="playbook_codex",
            )
            hits.extend(vec.hits)
            channels.extend(list(vec.channels or []))
        pack = RecallPack(
            hits=hits[:12],
            skip_reason="" if hits else "empty",
            budget_tag="playbook_codex",
            channels=channels,
        )
    except Exception as exc:
        rec = {"ok": False, "error": type(exc).__name__, "seq": int(seq)}
        _log.info("recall_shadow fail %s", rec)
        try:
            from scribe3.pipeline_trace_hooks import note_guide_missing
            note_guide_missing("recall_shadow_fail")
        except Exception:
            pass
        return rec
    shadow = pack_text(pack)
    legacy_ids = set()
    for line in str(legacy_text or "").splitlines():
        if " / " in line:
            legacy_ids.add(line.split(" / ", 1)[0].strip())
    shadow_ids = {h.entity_id.replace("role:", "") for h in pack.hits}
    secret_ids: set[str] = set()
    try:
        facts_fn = getattr(store, "facts_at", None)
        if callable(facts_fn):
            for f in list(facts_fn(int(seq)) or []):
                if _fact_get(f, "secret") is True:
                    val = str(_fact_get(f, "value") or "").strip()
                    if val:
                        secret_ids.add(val)
    except Exception:
        pass
    leaked = {s for s in secret_ids if s and s in str(legacy_text or "")}
    both = legacy_ids | shadow_ids
    jacc = (len(legacy_ids & shadow_ids) / len(both)) if both else 1.0
    leg_n = max(len(legacy_text or ""), 1)
    secret_diff = 0.0 if not leaked else 1.0
    budget_delta = abs(len(shadow or "") - len(legacy_text or "")) / leg_n
    rec = {
        "ok": True,
        "seq": int(seq),
        "path": str(path or ""),
        "legacy_len": len(legacy_text or ""),
        "shadow_len": len(shadow or ""),
        "channels": pack.channels,
        "skip": pack.skip_reason,
        "legacy_ids": sorted(legacy_ids),
        "shadow_ids": sorted(shadow_ids),
        "same_entities": legacy_ids == shadow_ids,
        "entity_jaccard": round(jacc, 4),
        "secret_leak_count": len(leaked),
        "secret_jaccard_diff": secret_diff,
        "budget_delta": budget_delta,
    }
    rec["threshold_ok"] = (
        secret_diff <= 0.0 and jacc >= 0.92 and budget_delta <= 0.15
    )
    if secret_diff > 0.0:
        _log.warning("recall_shadow 限知泄漏 seq=%s leaked=%s", seq, sorted(leaked)[:8])
    if jacc < 0.92:
        _log.warning("recall_shadow 通用实体 Jaccard=%.4f < 0.92 seq=%s", jacc, seq)
    if budget_delta > 0.15:
        _log.warning("recall_shadow 预算偏差=%.4f > 0.15 seq=%s", budget_delta, seq)
    _log.info("recall_shadow %s", rec)
    try:
        record_shadow_stat(rec)
    except Exception:
        pass
    try:
        from scribe3.pipeline_trace_hooks import note_guide_missing, note_recall_shadow
        note_recall_shadow(rec)
        if pack.skip_reason:
            note_guide_missing(f"recall_shadow:{pack.skip_reason}")
    except Exception:
        pass
    return rec
