"""v6.1+ 产品钩子：讨论/定稿 → 全类型抽取 → ChangePack + 持久化候选。"""
from __future__ import annotations

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
    """把 pack items 写入 canon_candidate，返回 ids。"""
    if st is None or not hasattr(st, "add_canon_candidate"):
        return [i.get("id") for i in (pack_dict.get("items") or []) if i.get("id")]
    ids = []
    for it in pack_dict.get("items") or []:
        if not isinstance(it, dict):
            continue
        row = {
            "id": it.get("id"),
            "seq": seq,
            "source": source,
            "extractor": "hybrid",
            "module": it.get("module"),
            "op": it.get("op"),
            "target": it.get("target"),
            "field": it.get("field"),
            "before": it.get("before"),
            "after": it.get("after"),
            "evidence": it.get("evidence"),
            "risk": it.get("risk"),
            "layer": it.get("layer"),
            "status": "pending",
            "change_pack_id": pack_dict.get("id"),
            "impact": pack_dict.get("impact"),
            "confidence": 1.0,
        }
        try:
            cid = st.add_canon_candidate(row)
            ids.append(cid)
            # 双写旧人物队列兼容
            if it.get("module") == "character" and (it.get("op") == "add" or not it.get("field")):
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
    if claims is not None:
        use_claims = list(claims)
    else:
        use_claims = extract_claims_from_prose(
            text or "",
            known_character_names=_known_names(st),
            complete_fn=complete_fn,
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
    if claims is not None:
        use_claims = list(claims)
    else:
        use_claims = extract_claims_from_prose(
            prose or "",
            known_character_names=_known_names(st),
            complete_fn=complete_fn,
        )
    rep = build_post_finalize_report(
        seq=seq,
        prose=prose or "",
        work=work,
        claims=use_claims,
        canon_snapshot=snap,
        chapter_index=cidx,
    )
    if persist and rep.get("change_pack"):
        _persist_pack_items(st, rep["change_pack"], seq=seq, source="prose_finalize")
    rep["debt"] = st.count_canon_debt() if st is not None and hasattr(st, "count_canon_debt") else {}
    rep["modules_all"] = sorted({
        *(rep["sections"]["l1_requires_approval"].get("modules") or []),
        *(rep["sections"]["l2_objective"].get("modules") or []),
    })
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
