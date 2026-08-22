"""v6.1+ 产品钩子：讨论/定稿 → 全类型抽取 → ChangePack + 持久化候选。"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import logging
from typing import Any, Callable, Iterable, Mapping

from scribe3.canon_extract import extract_claims_from_prose
from scribe3.canon_loop import (
    CanonClaim,
    build_post_finalize_report,
    pack_from_claims,
    pack_from_discussion_text,
)

_log = logging.getLogger("scribe3")


def _iter_characters(st: Any) -> list[Any]:
    """兼容 SurrealStore.characters() 与 InMemoryCanonStore.characters dict。"""
    if st is None:
        return []
    chars = getattr(st, "characters", None)
    if chars is None:
        return []
    if callable(chars):
        try:
            return list(chars() or [])
        except Exception:
            return []
    if isinstance(chars, dict):
        # InMemory: bare → fields dict
        return list(chars.items())
    if isinstance(chars, (list, tuple)):
        return list(chars)
    return []


def build_canon_snapshot_from_store(st: Any) -> dict[str, Any]:
    snap: dict[str, Any] = {"characters": {}, "world_rules": {}, "intent": {}}
    if st is None:
        return snap
    if hasattr(st, "snapshot") and callable(st.snapshot):
        try:
            s = st.snapshot()
            if isinstance(s, dict) and s.get("characters") is not None:
                return {
                    "characters": dict(s.get("characters") or {}),
                    "world_rules": dict(s.get("world_rules") or {}),
                    "intent": dict(s.get("intent") or {}),
                }
        except Exception as e:
            _log.warning("canon snapshot via store.snapshot: %s", e)
    try:
        for c in _iter_characters(st):
            if isinstance(c, tuple) and len(c) == 2:
                bare, row = c[0], dict(c[1] or {})
                bare = str(bare).split(":")[-1]
                row.setdefault("name", bare)
                if bare:
                    snap["characters"][bare] = row
                    snap["characters"][f"role:{bare}"] = row
                continue
            bare = str(getattr(c, "id", "") or "").split(":")[-1]
            traits = dict(getattr(c, "traits", None) or {})
            row = {"name": getattr(c, "name", bare), **traits}
            if bare:
                snap["characters"][bare] = row
            cid = str(getattr(c, "id", "") or "")
            if cid:
                snap["characters"][cid] = row
    except Exception as e:
        _log.warning("canon snapshot characters: %s", e)
    try:
        if hasattr(st, "list_world_rules"):
            for r in st.list_world_rules() or []:
                if isinstance(r, dict) and r.get("name"):
                    snap["world_rules"][r["name"]] = r
    except Exception as e:
        _log.warning("canon snapshot world_rules: %s", e)
    try:
        if hasattr(st, "get_intent"):
            snap["intent"] = st.get_intent() or {}
        elif isinstance(getattr(st, "intent", None), dict):
            snap["intent"] = dict(st.intent)
    except Exception as e:
        _log.warning("canon snapshot intent: %s", e)
    return snap


def chapter_index_from_store(st: Any, max_seq: int = 50) -> dict[str, list[int]]:
    idx: dict[str, list[int]] = {}
    if st is None:
        return idx
    try:
        names = []
        for c in _iter_characters(st):
            if isinstance(c, tuple) and len(c) == 2:
                n = str(c[0]).split(":")[-1]
                if isinstance(c[1], dict) and c[1].get("name"):
                    n = str(c[1]["name"])
                if n:
                    names.append(n)
                continue
            n = (getattr(c, "name", None) or "").strip()
            if n:
                names.append(n)
        for seq in range(1, max_seq + 1):
            ch = st.get_chapter(seq) if hasattr(st, "get_chapter") else None
            if not ch:
                continue
            if not isinstance(ch, dict):
                continue
            blob = f"{ch.get('title') or ''}{ch.get('synopsis') or ''}{ch.get('prose') or ''}"
            for n in names:
                if n and n in blob:
                    idx.setdefault(n, [])
                    if seq not in idx[n]:
                        idx[n].append(seq)
                    idx[f"role:{n}"] = list(idx[n])
    except Exception as e:
        _log.warning("chapter_index: %s", e)
    return idx


def _known_names(st: Any) -> list[str]:
    out = []
    if st is None:
        return out
    try:
        for c in _iter_characters(st):
            if isinstance(c, tuple) and len(c) == 2:
                n = str(c[0]).split(":")[-1]
                if isinstance(c[1], dict) and c[1].get("name"):
                    n = str(c[1]["name"])
                if n:
                    out.append(n)
                continue
            n = (getattr(c, "name", None) or "").strip()
            if n:
                out.append(n)
    except Exception:
        pass
    return out


def _persist_pack_items(st: Any, pack_dict: dict, *, seq: int | None, source: str) -> list[str]:
    """把 pack items 写入 canon_candidate，返回 ids。

    噪声 / 库中已有 / 本批重复 → status=rejected（仍落库可审计，不占待批）。
    """
    if st is None or not hasattr(st, "add_canon_candidate"):
        return [i.get("id") for i in (pack_dict.get("items") or []) if i.get("id")]
    from scribe3.canon_inbox import codex_already_has, dedupe_key, is_noise_heuristic

    ids: list[str] = []
    seen_keys: set[str] = set()
    # 已 pending 的键：避免同对象反复入队
    try:
        for p in (st.list_canon_candidates(status="pending") or []):
            seen_keys.add(dedupe_key(p))
        for p in (st.list_canon_candidates(status="rejected") or []):
            seen_keys.add(dedupe_key(p))
    except Exception:
        pass

    for it in pack_dict.get("items") or []:
        if not isinstance(it, dict):
            continue
        conf = it.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else 1.0
        except Exception:
            conf_f = 1.0
        ev = (it.get("evidence") or "")
        ext = (it.get("extractor") or "").strip().lower()
        if not ext:
            if ev.startswith("【"):
                ext = "marker"
            elif conf is not None and 0.5 <= conf_f < 0.99:
                ext = "llm"
            else:
                ext = "hybrid"
        bare_add = (not it.get("field")) and (it.get("op") or "add") in ("add", "plant")
        if bare_add and not ev.startswith("【") and ext not in ("llm", "llm_v1", "marker"):
            if conf_f >= 0.99 or ext in ("hybrid", ""):
                conf_f = min(conf_f, 0.45)
                ext = "heuristic"
            elif conf is None:
                conf_f = 0.45
                ext = "heuristic"
        pre = {
            "module": it.get("module"), "op": it.get("op"), "target": it.get("target"),
            "field": it.get("field"), "after": it.get("after"), "extractor": ext,
            "confidence": conf_f, "evidence": it.get("evidence"),
        }
        status = "pending"
        dkey = dedupe_key(pre)
        if is_noise_heuristic(pre):
            status = "rejected"
        elif codex_already_has(st, pre):
            status = "rejected"
        elif dkey in seen_keys and bare_add:
            status = "rejected"
        if status == "pending":
            seen_keys.add(dkey)
        row = {
            "id": it.get("id"),
            "seq": seq,
            "source": source,
            "extractor": ext,
            "module": it.get("module"),
            "op": it.get("op"),
            "target": it.get("target"),
            "field": it.get("field"),
            "before": it.get("before"),
            "after": it.get("after"),
            "evidence": it.get("evidence"),
            "risk": it.get("risk"),
            "layer": it.get("layer"),
            "status": status,
            "change_pack_id": pack_dict.get("id"),
            "impact": pack_dict.get("impact"),
            "confidence": conf_f,
        }
        try:
            cid = st.add_canon_candidate(row)
            ids.append(cid)
            if (
                status == "pending"
                and it.get("module") == "character"
                and (it.get("op") == "add" or not it.get("field"))
            ):
                name = (it.get("target") or "").split(":")[-1]
                if name and hasattr(st, "add_unverified_ref") and seq is not None:
                    try:
                        st.add_unverified_ref(name, int(seq), "canon_extract")
                    except Exception:
                        pass
        except Exception as e:
            _log.warning("persist candidate: %s", e)
            if it.get("id"):
                ids.append(it["id"])
    return ids


def discussion_change_pack(
    *,
    work: str,
    text: str,
    source: str = "discussion",
    claims: Iterable[CanonClaim | Mapping[str, Any]] | None = None,
    st: Any = None,
    canon_snapshot: Mapping[str, Any] | None = None,
    chapter_index: Mapping[str, list[int]] | None = None,
    complete_fn: Callable[[str], str] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    snap = canon_snapshot if canon_snapshot is not None else build_canon_snapshot_from_store(st)
    cidx = chapter_index if chapter_index is not None else chapter_index_from_store(st)
    from scribe3.canon_extract import resolve_extract_mode
    if claims is not None:
        use_claims = list(claims)
    else:
        use_claims = extract_claims_from_prose(
            text or "",
            known_character_names=_known_names(st),
            complete_fn=complete_fn,
            mode=resolve_extract_mode(),
            canon_snapshot=snap if isinstance(snap, dict) else None,
        )
    pack = pack_from_discussion_text(
        text or "",
        work=work,
        source=source,
        canon_snapshot=snap,
        chapter_index=cidx,
        claims=use_claims,
    )
    d = pack.to_dict()
    if persist:
        _persist_pack_items(st, d, seq=None, source=source)
    d["debt"] = st.count_canon_debt() if st is not None and hasattr(st, "count_canon_debt") else {}
    return d


def body_confirmed_report(
    *,
    work: str,
    seq: int,
    prose: str = "",
    claims: Iterable[CanonClaim | Mapping[str, Any]] | None = None,
    st: Any = None,
    canon_snapshot: Mapping[str, Any] | None = None,
    chapter_index: Mapping[str, list[int]] | None = None,
    complete_fn: Callable[[str], str] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    if not prose and st is not None and hasattr(st, "get_chapter"):
        ch = st.get_chapter(seq) or {}
        prose = ch.get("prose") or ""
    snap = canon_snapshot if canon_snapshot is not None else build_canon_snapshot_from_store(st)
    cidx = chapter_index if chapter_index is not None else chapter_index_from_store(st)
    from scribe3.canon_extract import resolve_extract_mode
    from scribe3.chapter_analysis import claims_for_prose_unified, unified_analysis_enabled
    extract_mode = resolve_extract_mode()
    analysis_meta: dict[str, Any] = {}
    if claims is not None:
        use_claims = list(claims)
    elif complete_fn and extract_mode in ("llm", "hybrid") and unified_analysis_enabled():
        use_claims, analysis_meta = claims_for_prose_unified(
            prose or "",
            complete_fn,
            st=st,
            work=work,
            seq=seq,
            mode=extract_mode,
        )
        # hybrid：再叠启发式
        if extract_mode == "hybrid":
            extra = extract_claims_from_prose(
                prose or "",
                known_character_names=_known_names(st),
                complete_fn=None,
                mode="heuristic",
                canon_snapshot=snap if isinstance(snap, dict) else None,
            )
            seen = {(c.module, c.target, c.field, str(c.after)[:40]) for c in use_claims}
            for c in extra:
                key = (c.module, c.target, c.field, str(c.after)[:40])
                if key not in seen:
                    use_claims.append(c)
                    seen.add(key)
    else:
        use_claims = extract_claims_from_prose(
            prose or "",
            known_character_names=_known_names(st),
            complete_fn=complete_fn,
            mode=extract_mode,
            canon_snapshot=snap if isinstance(snap, dict) else None,
        )
    rep = build_post_finalize_report(
        seq=seq,
        prose=prose or "",
        work=work,
        claims=use_claims,
        canon_snapshot=snap,
        chapter_index=cidx,
    )
    # 标注抽取器，便于收件箱区分模型 vs 规则
    pack = rep.get("change_pack")
    if isinstance(pack, dict):
        for it in pack.get("items") or []:
            if not isinstance(it, dict):
                continue
            if (it.get("evidence") or "").startswith("【"):
                it.setdefault("extractor", "marker")
            elif analysis_meta.get("unified") and complete_fn:
                it.setdefault("extractor", "llm")
            elif extract_mode == "llm" and complete_fn:
                it.setdefault("extractor", "llm")
            elif extract_mode == "heuristic":
                it.setdefault("extractor", "heuristic")
            else:
                it.setdefault("extractor", "hybrid")
    if persist and rep.get("change_pack"):
        _persist_pack_items(st, rep["change_pack"], seq=seq, source="prose_finalize")

    # 同一模型结果驱动 L2 知识回写（与 ingest 同源；幂等 purge）
    ingest_result = None
    kn = analysis_meta.get("knowledge")
    if (
        persist
        and st is not None
        and kn is not None
        and complete_fn
        and extract_mode in ("llm", "hybrid")
    ):
        try:
            from scribe3.ingest import apply_delta, grep_back_verify
            open_p = None
            try:
                if hasattr(st, "open_promises"):
                    open_p = st.open_promises()
            except Exception:
                open_p = None
            verify = grep_back_verify(kn, prose or "")
            kn2 = verify.get("delta") or kn
            applied = apply_delta(st, kn2, seq, open_promises=open_p)
            # 钉指纹：后台/手动 ingest 对同正文跳过二次 purge
            try:
                import hashlib
                from scribe3.api.services.ingest_bg import mark_chapter_ingest_status
                fp = hashlib.sha256((prose or "").encode("utf-8")).hexdigest()[:16]
                mark_chapter_ingest_status(
                    st, seq, "ok", "unified_finalize", prose_fp=fp,
                )
            except Exception as me:
                _log.warning("mark ingest_prose_fp after finalize: %s", me)
            ingest_result = {
                "applied": applied,
                "source": "unified_finalize",
                "format": analysis_meta.get("format"),
                "annotated": verify.get("annotated") or [],
            }
        except Exception as e:
            _log.warning("unified finalize apply_delta seq=%s: %s", seq, e)
            ingest_result = {"applied": -1, "error": str(e)[:200], "source": "unified_finalize"}

    rep["debt"] = st.count_canon_debt() if st is not None and hasattr(st, "count_canon_debt") else {}
    rep["modules_all"] = sorted({
        *(rep["sections"]["l1_requires_approval"].get("modules") or []),
        *(rep["sections"]["l2_objective"].get("modules") or []),
    })
    rep["extract_mode"] = extract_mode
    rep["extract_used_llm"] = bool(complete_fn) and extract_mode in ("llm", "hybrid")
    rep["unified_analysis"] = bool(analysis_meta.get("unified"))
    rep["unified_format"] = analysis_meta.get("format")
    rep["ingest"] = ingest_result
    # 确定性 QC（与模型分析共享同一份 prose，零额外 LLM）
    try:
        from scribe3.chapter_analysis import quick_qc_summary
        rep["qc_quick"] = quick_qc_summary(prose or "")
    except Exception as e:
        _log.warning("qc_quick: %s", e)
        rep["qc_quick"] = None
    # 可选：终选时一并跑纪律并写入章后缓存，供 /post-check 复用（默认关，免拖慢终选）
    import os
    if (
        persist
        and complete_fn
        and (get_flag("SCRIBE3_FINALIZE_RUN_DISCIPLINE") or "").strip().lower()
        in ("1", "true", "yes", "on")
    ):
        try:
            from scribe3.chapter_analysis import run_discipline_with_cache
            disc = run_discipline_with_cache(
                work=work, seq=seq, prose=prose or "",
                complete_fn=complete_fn, st=st, force=False,
            )
            rep["discipline"] = {
                "violations": disc.get("violations") or [],
                "changed": disc.get("changed"),
                "cache_hit": disc.get("cache_hit"),
                "source": disc.get("source"),
            }
        except Exception as e:
            _log.warning("finalize discipline cache: %s", e)
    return rep


def run_chapter_extract(
    st: Any,
    *,
    work: str,
    seq: int,
    complete_fn: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """手动/API：对一章正文全量抽取并落 pending。"""
    ch = st.get_chapter(seq) if st and hasattr(st, "get_chapter") else {}
    prose = (ch or {}).get("prose") or ""
    return body_confirmed_report(
        work=work, seq=seq, prose=prose, st=st,
        complete_fn=complete_fn, persist=True,
    )
