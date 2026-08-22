"""parked · 故事完成宣称（narrative-mainline · story_ready / assert_story_claim）。

半成品：仅测试引用，未接入作者主路径。接线计划见 docs/plans/parked-modules.md。
设计：docs/plans/2026-08-13-narrative-mainline.md R2
"""
from __future__ import annotations

import os
from typing import Any

from scribe3.anti_meta_narration import scan_anti_meta
from scribe3.narrative_contract import (
    conflict_beats_ok,
    cn_len,
    contract_content_fp,
    resolve_beat_items,
    suggest_scene_contract,
    validate_narrative_contract,
)
from scribe3.reader_ready import pad_hard_claim, scene_cover
from scribe3.review.fp import prose_fp


def _flag(name: str, default: str = "0") -> bool:
    v = (os.environ.get(name) if os.environ.get(name) is not None else default) or default
    return str(v).strip().lower() not in ("0", "false", "no", "off", "")


def story_complete_enabled() -> bool:
    return _flag("SCRIBE3_STORY_COMPLETE", "0")


def scene_cover_in_claim() -> bool:
    """Clamp: if STORY_COMPLETE=0, always True (must participate)."""
    if not story_complete_enabled():
        return True
    return _flag("SCRIBE3_SCENE_COVER_IN_CLAIM", "0")


def clamp_claim_flags() -> dict[str, Any]:
    """Enforce KD16 matrix; return effective flags + log notes."""
    notes: list[str] = []
    sc = story_complete_enabled()
    cover_raw = _flag("SCRIBE3_SCENE_COVER_IN_CLAIM", "1" if not sc else "0")
    cover_eff = cover_raw
    if not sc and not cover_raw:
        cover_eff = True
        notes.append("clamp_cover_to_1_while_story_complete_0")
    if not sc:
        cover_eff = True
    return {
        "STORY_COMPLETE": sc,
        "SCENE_COVER_IN_CLAIM": cover_eff,
        "notes": notes,
    }


def _load_contract(st, seq: int | None) -> dict[str, Any]:
    if st is None or seq is None:
        return validate_narrative_contract(None)
    try:
        ch = st.get_chapter(int(seq)) or {}
    except Exception:
        return validate_narrative_contract(None)
    raw = ch.get("narrative_contract")
    if not raw:
        return validate_narrative_contract(None)
    return validate_narrative_contract(raw)


def _load_beats(st, seq: int | None, contract: dict) -> list:
    chapter_beats = None
    if st is not None and seq is not None:
        try:
            ch = st.get_chapter(int(seq)) or {}
            chapter_beats = ch.get("beats")
        except Exception:
            chapter_beats = None
    return resolve_beat_items(contract, chapter_beats)


def _get_story_ack(st, work: str, seq: int) -> dict | None:
    if st is None:
        return None
    if hasattr(st, "get_reader_ack"):
        try:
            # kind-aware signature
            import inspect
            sig = inspect.signature(st.get_reader_ack)
            if "kind" in sig.parameters:
                return st.get_reader_ack(work, int(seq), kind="story")
            # fallback: only reader path — story ack unavailable
            return None
        except Exception:
            return None
    return None


def build_story_ready(
    prose: str,
    *,
    st=None,
    work: str | None = None,
    seq: int | None = None,
    contract: dict | None = None,
    beats=None,
    load_ack: bool = True,
    scaffold_ok: bool | None = None,
) -> dict[str, Any]:
    """Build story_ready payload (narrative completion SSOT when flag on)."""
    flags = clamp_claim_flags()
    am = scan_anti_meta(prose or "") if _flag("SCRIBE3_ANTI_META", "1") else {
        "hits": [], "ok_for_claim": True, "claim_blocking_ids": [],
    }
    hits = am.get("hits") or []
    pad = pad_hard_claim(prose or "", hits)
    guards_ok = bool(am.get("ok_for_claim")) and not pad

    if contract is None:
        c = _load_contract(st, seq)
    else:
        c = validate_narrative_contract(contract)

    if beats is None:
        beat_items = _load_beats(st, seq, c)
    else:
        beat_items = resolve_beat_items(c, beats)

    cb = conflict_beats_ok(beat_items)
    # diagnostic cover (never sole claim when STORY_COMPLETE)
    sc = scene_cover(prose or "", beat_items if isinstance(beat_items, list) else [], hits)

    fp = prose_fp(prose)
    c_fp = contract_content_fp(c)
    human_story_acked = False
    ack_row = None
    note_ok = False
    if load_ack and st is not None and seq is not None and work:
        try:
            ack_row = _get_story_ack(st, work, int(seq))
            ack_cfp = str((ack_row or {}).get("contract_fp") or "")
            if (
                ack_row
                and (ack_row.get("prose_fp") or "") == fp
                and ack_cfp
                and ack_cfp == c_fp
            ):
                human_story_acked = True
                note_ok = cn_len(str(ack_row.get("note") or "")) >= 10
                if not note_ok:
                    human_story_acked = False
        except Exception:
            human_story_acked = False

    contract_ok = bool((c.get("validation") or {}).get("ok"))
    beats_ok = bool(cb.get("ok"))

    machine_story_ok = contract_ok and beats_ok and guards_ok
    if flags["STORY_COMPLETE"] and flags["SCENE_COVER_IN_CLAIM"]:
        # transitional: also require old cover
        machine_story_ok = machine_story_ok and (sc.get("ok") is True)

    may_claim_story = bool(machine_story_ok and human_story_acked)

    if not machine_story_ok:
        phase = "red"
    elif not human_story_acked:
        phase = "yellow"
    else:
        phase = "green"

    blocking: list[str] = []
    if not contract_ok:
        blocking.append("narrative_contract")
    if not beats_ok:
        blocking.append("conflict_beats")
    for h in hits:
        if (h.get("severity") or "") == "claim_blocking":
            blocking.append(f"anti_meta.{h.get('id')}")
    if pad:
        blocking.append("pad_hard_claim")
    if flags["STORY_COMPLETE"] and flags["SCENE_COVER_IN_CLAIM"] and sc.get("ok") is not True:
        blocking.append("scene_cover")

    ack_safe = None
    if isinstance(ack_row, dict):
        ack_safe = {
            "prose_fp": ack_row.get("prose_fp"),
            "contract_fp": ack_row.get("contract_fp"),
            "work": ack_row.get("work"),
            "seq": ack_row.get("seq"),
            "note": ack_row.get("note"),
            "kind": ack_row.get("kind") or "story",
        }

    suggest_block = None
    if st is not None and seq is not None:
        try:
            ch_full = st.get_chapter(int(seq)) or {}
            suggest_block = suggest_scene_contract(ch_full)
            # 不得把 suggest.ok / adopted_would_be.ok 写入 contract.ok
        except Exception:
            suggest_block = None

    return {
        "schema": "story_ready.v1",
        "flags": flags,
        "contract": {
            "ok": contract_ok,
            "errors": (c.get("validation") or {}).get("errors") or [],
            "fields": {k: c.get(k) for k in ("desire", "obstacle", "turn", "cost")},
        },
        "contract_fp": c_fp,
        "suggest": (
            {
                "persist": False,
                "needs_author": (suggest_block or {}).get("needs_author"),
                "lock_warnings": (suggest_block or {}).get("lock_warnings") or [],
                "draft": (suggest_block or {}).get("draft"),
            }
            if suggest_block
            else None
        ),
        "conflict_beats": cb,
        "guards_ok": guards_ok,
        "anti_meta": am,
        "pad_hard_claim": pad,
        "scene_cover_diag": sc,
        "machine_story_ok": machine_story_ok,
        "human_story_acked": human_story_acked,
        "phase": phase,
        "blocking": blocking,
        "claims": {
            "may_claim_story": may_claim_story,
            "may_claim_readable": may_claim_story,  # alias when story path
            "may_claim_serializable": False,
        },
        "scaffold_diag": {"ok": scaffold_ok},
        "ack": ack_safe,
        "prose_fp": fp,
        "length_policy": {
            "cn_len": cn_len(prose),
            "soft_floor": 800,
        },
    }


def assert_story_claim(
    prose: str,
    *,
    st=None,
    work: str | None = None,
    seq: int | None = None,
    require_ack: bool = True,
    contract: dict | None = None,
    beats=None,
    scaffold_ok: bool | None = None,
) -> dict[str, Any]:
    """Hard gate for story claim. Not for draft save."""
    if not _flag("SCRIBE3_ANTI_META_BLOCK_CLAIM", "1"):
        return {"allowed": True, "code": "flag_off", "story_ready": {}}

    sr = build_story_ready(
        prose,
        st=st,
        work=work,
        seq=seq,
        contract=contract,
        beats=beats,
        load_ack=require_ack,
        scaffold_ok=scaffold_ok,
    )
    if not sr.get("contract", {}).get("ok"):
        return {
            "allowed": False,
            "code": "narrative_contract_required",
            "detail": "叙事合同未过最小门槛（欲望/阻力/回合/代价）",
            "blocking": sr.get("blocking") or ["narrative_contract"],
            "story_ready": sr,
        }
    if not (sr.get("conflict_beats") or {}).get("ok"):
        return {
            "allowed": False,
            "code": "conflict_beats_required",
            "detail": "需要至少一条冲突形态节拍（非道具标签）",
            "blocking": sr.get("blocking") or ["conflict_beats"],
            "story_ready": sr,
        }
    if not sr.get("guards_ok"):
        return {
            "allowed": False,
            "code": "reader_claim",
            "detail": "正文未过护栏（验收腔或 pad）",
            "blocking": sr.get("blocking") or [],
            "story_ready": sr,
        }
    if require_ack and not sr.get("human_story_acked"):
        return {
            "allowed": False,
            "code": "story_ack_required",
            "detail": "场面或确认已过期，请再签",
            "blocking": ["story_ack_required"],
            "story_ready": sr,
        }
    if not sr["claims"].get("may_claim_story"):
        return {
            "allowed": False,
            "code": "story_claim",
            "detail": "不可宣称故事完成",
            "blocking": sr.get("blocking") or [],
            "story_ready": sr,
        }
    return {
        "allowed": True,
        "code": "ok",
        "story_ready": sr,
        "reader_ready": None,  # caller may dual-write
    }
