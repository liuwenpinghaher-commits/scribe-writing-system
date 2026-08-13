"""双灯 · 读者可读机判 + 宣称硬门（dual-lamp）。

lamps.scaffold = 可开写（由调用方传入 craft 摘要，默认未知）
lamps.reader = 机判可读（anti_meta + scene_cover + pad）
may_claim_readable = machine_ok ∧ human_acked
"""
from __future__ import annotations

import os
import re
from typing import Any

from scribe3.anti_meta_narration import is_meta_span, scan_anti_meta
from scribe3.review.fp import prose_fp


def _flag(name: str, default: str = "1") -> bool:
    v = (os.environ.get(name) or default).strip().lower()
    return v not in ("0", "false", "no", "off", "")


def cn_len(s: str) -> int:
    return len(re.sub(r"\s+", "", (s or "").strip()))


def _beat_text(b: Any) -> str:
    if isinstance(b, str):
        return b.strip()
    if isinstance(b, dict):
        return str(b.get("text") or "").strip()
    return ""


_BEAT_STOP = frozenset({
    "下令", "发现", "指出", "必须", "本章", "不得", "不能", "不要",
    "并且", "以及", "然后", "于是", "一个", "这个", "那个", "他们",
    "我们", "自己", "什么", "怎么", "是否", "没有", "已经", "还是",
})


def beat_scene_keywords(beat: str, *, n: int = 4) -> list[str]:
    """从口号拍抽出 2–4 个场面词（封炉/缺页/刀鞘），供 scene_cover 命中。"""
    bt = (beat or "").strip()
    if not bt:
        return []
    parts = [t for t in re.split(r"[\s,，。；;：:、！？!?]+", bt) if len(t) >= 2]
    keys: list[str] = []
    for t in parts:
        if t in _BEAT_STOP:
            continue
        if len(t) >= 2:
            keys.append(t)
        # 长口号再切 2 字场面核
        if len(t) >= 4:
            for i in range(0, len(t) - 1):
                chunk = t[i : i + 2]
                if chunk not in _BEAT_STOP and chunk not in keys:
                    keys.append(chunk)
    # 保序去重
    seen: set[str] = set()
    out: list[str] = []
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
        if len(out) >= n:
            break
    return out


def _keyword_ranges(prose: str, beat: str) -> list[tuple[int, int]]:
    """Locate beat keywords in prose (C11-like coarse)."""
    text = prose or ""
    bt = (beat or "").strip()
    if not bt or not text:
        return []
    ranges: list[tuple[int, int]] = []
    # try full beat snippet (first 12 chars compact)
    compact = re.sub(r"\s+", "", bt)
    if len(compact) >= 4:
        # search progressive prefixes
        for n in (min(12, len(compact)), min(8, len(compact)), min(6, len(compact)), 4):
            if n < 4:
                continue
            needle = compact[:n]
            idx = text.find(needle) if needle in text else -1
            if idx >= 0:
                ranges.append((idx, idx + len(needle)))
                return ranges
    tokens = [t for t in re.split(r"[\s,，。；;：:、]+", bt) if len(t) >= 2]
    for t in tokens[:6]:
        start = 0
        while True:
            i = text.find(t, start)
            if i < 0:
                break
            ranges.append((i, i + len(t)))
            start = i + len(t)
            if len(ranges) >= 3:
                break
        if ranges:
            return ranges
    # R12：口号拍抽场面词（封炉/缺页/刀鞘）再找
    for t in beat_scene_keywords(bt):
        i = text.find(t)
        if i >= 0:
            ranges.append((i, i + len(t)))
            if len(ranges) >= 3:
                break
    return ranges


def scene_cover(
    prose: str,
    beats: list | None,
    anti_meta_hits: list[dict] | None,
) -> dict[str, Any]:
    if beats is None:
        return {"ok": None, "degraded": True, "reason": "no_beats", "beat_ratio": 0.0}
    bl = [_beat_text(b) for b in beats]
    bl = [b for b in bl if b]
    if not bl:
        return {"ok": None, "degraded": True, "reason": "empty_beats", "beat_ratio": 0.0}
    hits = anti_meta_hits or []
    n = len(prose or "")
    tail_start = int(n * 0.75) if n else 0
    valid = 0
    for b in bl:
        ranges = _keyword_ranges(prose or "", b)
        good = []
        for a, c in ranges:
            # SC3 / dual-lamp: meta·SEO·验收清单行内命中一律无效
            if is_meta_span(prose or "", a, c, hits):
                continue
            if a >= tail_start and is_meta_span(
                prose or "", max(0, a - 20), min(n, c + 20), hits
            ):
                continue
            good.append((a, c))
        if good:
            valid += 1
    ratio = valid / max(1, len(bl))
    return {
        "ok": ratio >= 2 / 3,
        "degraded": False,
        "beat_ratio": ratio,
        "valid": valid,
        "total": len(bl),
    }


def pad_hard_claim(prose: str, anti_hits: list[dict]) -> bool:
    claim = [h for h in anti_hits if (h.get("severity") or "") == "claim_blocking"]
    if len(claim) < 2:
        return False
    if cn_len(prose) < 800:
        return False
    n = max(1, len(prose or ""))
    tail = int(n * 0.75)
    in_tail = sum(1 for h in claim if int(h.get("start") or 0) >= tail)
    return (in_tail / max(1, len(claim))) >= 0.6


def build_reader_ready(
    prose: str,
    *,
    st=None,
    work: str | None = None,
    seq: int | None = None,
    beats=None,
    open_promises=None,  # noqa: ARG001 reserved
    load_ack: bool = True,
    require_scene_cover: bool = True,
    scaffold_ok: bool | None = None,
) -> dict[str, Any]:
    """Build dual-lamp reader_ready payload."""
    am = scan_anti_meta(prose or "") if _flag("SCRIBE3_ANTI_META", "1") else {
        "hits": [], "ok_for_claim": True, "claim_blocking_ids": [],
    }
    degraded: list[str] = []
    hits = am.get("hits") or []

    if beats is None and st is not None and seq is not None:
        try:
            ch = st.get_chapter(int(seq)) or {}
            beats = ch.get("beats")
        except Exception:
            beats = None
            degraded.append("beats_load")

    if require_scene_cover and not beats:
        sc = {"ok": None, "degraded": True, "reason": "no_beats", "beat_ratio": 0.0}
        degraded.append("scene_cover")
    elif not require_scene_cover and beats is None:
        sc = {"ok": None, "degraded": True, "reason": "cover_skipped", "beat_ratio": 0.0}
        degraded.append("scene_cover")
    else:
        sc = scene_cover(prose or "", beats if isinstance(beats, list) else [], hits)

    human_acked = False
    ack_row = None
    fp = prose_fp(prose)
    if load_ack and st is not None and seq is not None and work:
        try:
            if hasattr(st, "get_reader_ack"):
                ack_row = st.get_reader_ack(work, int(seq))
            if ack_row and (ack_row.get("prose_fp") or "") == fp:
                human_acked = True
        except Exception:
            degraded.append("reader_ack")
            human_acked = False

    pad = pad_hard_claim(prose or "", hits)
    machine_ok = (
        bool(am.get("ok_for_claim"))
        and sc.get("ok") is True
        and not pad
        and "anti_meta" not in degraded
        and sc.get("degraded") is not True
    )

    if not machine_ok:
        phase = "red"
    elif not human_acked:
        phase = "yellow"
    else:
        phase = "green"

    blocking = [
        f"anti_meta.{h.get('id')}"
        for h in hits
        if (h.get("severity") or "") == "claim_blocking"
    ]
    if sc.get("ok") is False:
        blocking.append("scene_cover")
    if pad:
        blocking.append("pad_hard_claim")
    if sc.get("ok") is None and require_scene_cover:
        blocking.append("scene_cover_degraded")

    soft = [
        f"anti_meta.{h.get('id')}"
        for h in hits
        if (h.get("severity") or "") == "soft"
    ]
    clen = cn_len(prose)
    if clen < 800:
        soft.append("length.below_soft_floor")

    scaffold = scaffold_ok
    lamps = {
        "scaffold": {
            "ok": scaffold,
            "label": "可开写",
            "source": "caller_or_gate",
            "blocking": [],
        },
        "reader": {
            "ok": machine_ok,
            "phase": phase,
            "label": "可读",
            "blocking": blocking,
            "soft": soft,
            "human_ack_required": True,
            "human_acked": human_acked,
            "degraded": list(degraded),
            "prose_fp": fp,
        },
    }
    claims = {
        "may_claim_scaffold": bool(scaffold) if scaffold is not None else False,
        "may_claim_readable": bool(machine_ok and human_acked),
        "may_claim_serializable": False,  # needs H9 external
    }
    # ack_row may contain Surreal RecordID — never put raw in HTTP JSON
    ack_safe = None
    if isinstance(ack_row, dict):
        ack_safe = {
            "prose_fp": ack_row.get("prose_fp"),
            "work": ack_row.get("work"),
            "seq": ack_row.get("seq"),
            "note": ack_row.get("note"),
        }
    return {
        "machine_reader_ok": machine_ok,
        "human_acked": human_acked,
        "lamps": lamps,
        "claims": claims,
        "anti_meta": am,
        "scene_cover": sc,
        "length_policy": {
            "cn_len": clen,
            "soft_floor": 800,
            "pad_hard_claim": pad,
            "pad_suspect": clen >= 1500 and len(hits) >= 1,
        },
        "degraded": degraded,
        "ack": ack_safe,
        "prose_fp": fp,
    }


def assert_reader_claim(
    prose: str,
    *,
    st=None,
    work: str | None = None,
    seq: int | None = None,
    require_ack: bool = True,
    beats=None,
    scaffold_ok: bool | None = None,
) -> dict[str, Any]:
    """Hard gate for readable/serializable claims. Not for draft save."""
    if not _flag("SCRIBE3_ANTI_META_BLOCK_CLAIM", "1"):
        return {"allowed": True, "code": "flag_off", "reader_ready": {}}
    if st is None or work is None or seq is None:
        if beats is None:
            return {
                "allowed": False,
                "code": "reader_claim",
                "detail": "缺少作品/章上下文，无法判定可读",
                "blocking": ["missing_context"],
                "reader_ready": {},
            }
    rr = build_reader_ready(
        prose,
        st=st,
        work=work,
        seq=seq,
        beats=beats,
        load_ack=require_ack,
        require_scene_cover=True,
        scaffold_ok=scaffold_ok,
    )
    if not rr["machine_reader_ok"]:
        return {
            "allowed": False,
            "code": "reader_claim",
            "detail": "正文未过可读机判（含验收腔或场面未覆盖）",
            "blocking": (rr.get("lamps") or {}).get("reader", {}).get("blocking") or [],
            "reader_ready": rr,
        }
    if require_ack and not rr["human_acked"]:
        return {
            "allowed": False,
            "code": "reader_ack_required",
            "detail": "请像读者一样通读并确认（尚未确认或正文已改）",
            "blocking": ["reader_ack_required"],
            "reader_ready": rr,
        }
    return {"allowed": True, "code": "ok", "reader_ready": rr}


def anti_meta_issues_for_post(prose: str) -> list[dict[str, Any]]:
    """Issues for post/collect — advisory only (never S1/BLOCKING)."""
    am = scan_anti_meta(prose or "")
    out = []
    for h in am.get("hits") or []:
        out.append({
            "type": "anti_meta",
            "message": h.get("message_zh") or "验收腔",
            "text": h.get("quote") or "",
            "range": [h.get("start"), h.get("end")],
            "meta": {
                "severity": "advisory",  # never S1 — save must not 409
                "kind": h.get("id"),
                "claim_severity": h.get("severity"),
                "source": "anti_meta_narration",
            },
        })
    return out
