"""冰山前置：写厚水下质量，正文只露出水面。

字数在这里 = 「这块材料够不够撑一场戏」，不是文学分、不是宣称。
不进 GATE-B 的 80 字「可开写」口径，不进 may_claim_*。
空字段 = 还没写，允许。一旦写入大纲/节拍/演绎，必须达到覆盖地板——
80 字口号不能落库，否则系统会把它当成「已经有大纲」。
"""
from __future__ import annotations

import os
import re
from typing import Any

# 水下质量地板（覆盖/信息量，不是评分）
SYNOPSIS_FLOOR = 500
BEAT_EACH_FLOOR = 500
BEAT_SUM_FLOOR = 2000
DEDUCTION_FLOOR = 5000
DRAFT_FLOOR = 10000
PROSE_SURFACE = 5000  # 水面：正文要有足够面积让冰山露出来

# 注入帽：刚过闸必须全给；只砍「写超了很多」的尾巴。final 与 thicken 同档。
INJECT_CAP = {
    "synopsis": 2500,
    "beat": 1200,
    "scene_truth": 2500,
    "deduction": 4000,
    "draft": 12000,
}
DEDUCTION_PACK_CAP = 6000
NEAR_FLOOR_RATIO = 1.2

_WS = re.compile(r"\s+")

# 这些阶段是在写厚冰山，不得用冰山闸卡住
_THICKEN_PHASES = frozenset({
    "outline", "plan", "beats", "deduce", "scaffold", "meta",
})
_PROSE_PHASES = frozenset({"", "draft", "final", "write", "prose"})


def cn_len(text: str | None) -> int:
    return len(_WS.sub("", text or ""))


def _floor_for(field: str) -> int:
    return {
        "synopsis": SYNOPSIS_FLOOR,
        "beat": BEAT_EACH_FLOOR,
        "scene_truth": 0,
        "deduction": 0,
        "draft": DRAFT_FLOOR,
    }.get(field, 0)


def clip_for(field: str, text: str | None) -> str:
    """唯一冰山裁切：近地板不裁；否则裁到 INJECT_CAP 且不低于地板。"""
    raw = text or ""
    if not raw:
        return ""
    n = cn_len(raw)
    floor = _floor_for(field)
    cap = int(INJECT_CAP.get(field) or 0)
    if floor and n <= int(floor * NEAR_FLOOR_RATIO):
        return raw
    if not cap or n <= cap:
        return raw
    # 按字符裁到 cap，尽量不拆到地板以下
    keep = max(cap, floor)
    if len(raw) <= keep:
        return raw
    return raw[:keep]


def iceberg_enabled() -> bool:
    raw = os.environ.get("SCRIBE3_ICEBERG_WRITE")
    if raw is None or str(raw).strip() == "":
        return True
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def _beat_lens(ch: dict) -> list[int]:
    out: list[int] = []
    for b in ch.get("beats") or []:
        if isinstance(b, dict):
            out.append(cn_len(b.get("text")))
        else:
            out.append(cn_len(str(b or "")))
    return [n for n in out if n > 0]


def _deduction_sum(ch: dict) -> int:
    total = 0
    for d in ch.get("deductions") or []:
        if isinstance(d, dict):
            total += cn_len(d.get("prose") or d.get("text"))
        else:
            total += cn_len(str(d or ""))
    return total


def _draft_len(ch: dict) -> int:
    """排演稿：独立字段优先，避免把读者正文误当成草稿。"""
    for k in ("draft_prose", "rehearsal", "draft"):
        v = ch.get(k)
        if isinstance(v, str) and v.strip():
            return cn_len(v)
    return 0


def evaluate_iceberg(ch: dict | None, *, for_phase: str = "draft") -> dict[str, Any]:
    """返回 {ok, missing, measures, message}。纯函数。"""
    meta = ch if isinstance(ch, dict) else {}
    phase = (for_phase or "draft").strip().lower()
    syn = cn_len(meta.get("synopsis"))
    beats = _beat_lens(meta)
    bsum = sum(beats)
    thin_beats = [i + 1 for i, n in enumerate(beats) if n < BEAT_EACH_FLOOR]
    dsum = _deduction_sum(meta)
    draft_n = _draft_len(meta)
    prose_n = cn_len(meta.get("prose"))

    missing: list[dict[str, Any]] = []
    if syn < SYNOPSIS_FLOOR:
        missing.append({"id": "synopsis", "got": syn, "need": SYNOPSIS_FLOOR})
    if len(beats) < 3:
        missing.append({"id": "beat_count", "got": len(beats), "need": 3})
    if thin_beats:
        missing.append({
            "id": "beat_each", "got": beats, "need": BEAT_EACH_FLOOR,
            "thin": thin_beats,
        })
    if bsum < BEAT_SUM_FLOOR:
        missing.append({"id": "beat_sum", "got": bsum, "need": BEAT_SUM_FLOOR})
    if dsum < DEDUCTION_FLOOR:
        missing.append({"id": "deduction", "got": dsum, "need": DEDUCTION_FLOOR})
    if phase in ("final", "write") and draft_n < DRAFT_FLOOR:
        missing.append({"id": "draft", "got": draft_n, "need": DRAFT_FLOOR})

    ok = not missing
    bits = []
    for m in missing:
        bits.append(f"{m['id']} {m['got']}<{m['need']}")
    msg = (
        "冰山已厚，可以进正文。"
        if ok else
        "冰山未厚，先进大纲/节拍/演绎写厚（不是刷字数，是把水下质量堆够）："
        + "；".join(bits)
    )
    return {
        "ok": ok,
        "missing": missing,
        "measures": {
            "synopsis": syn,
            "beats": beats,
            "beat_sum": bsum,
            "deduction": dsum,
            "draft": draft_n,
            "prose": prose_n,
        },
        "floors": {
            "synopsis": SYNOPSIS_FLOOR,
            "beat_each": BEAT_EACH_FLOOR,
            "beat_sum": BEAT_SUM_FLOOR,
            "deduction": DEDUCTION_FLOOR,
            "draft": DRAFT_FLOOR,
            "prose_surface": PROSE_SURFACE,
        },
        "message": msg,
        "role": "iceberg_substrate",
    }


def should_block_prose_write(phase: str | None, *, write_intent: bool) -> bool:
    if not write_intent:
        return False
    p = (phase or "draft").strip().lower()
    if p in _THICKEN_PHASES:
        return False
    return p in _PROSE_PHASES


def persist_fields_blocked(fields: dict | None) -> dict[str, Any] | None:
    """写入大纲/节拍/演绎时的硬闸。None=放行。

    空串/空列表 = 尚未写厚，允许。非空但低于地板 = 挡，禁止口号落成「已有大纲」。
    """
    if not iceberg_enabled() or not isinstance(fields, dict):
        return None
    missing: list[dict[str, Any]] = []
    if "synopsis" in fields:
        raw = fields.get("synopsis")
        if raw is not None and str(raw).strip():
            n = cn_len(str(raw))
            if n < SYNOPSIS_FLOOR:
                missing.append({"id": "synopsis", "got": n, "need": SYNOPSIS_FLOOR})
    if "beats" in fields and fields.get("beats") is not None:
        fake = {"beats": fields.get("beats")}
        lens = _beat_lens(fake)
        if lens:
            thin = [i + 1 for i, n in enumerate(lens) if n < BEAT_EACH_FLOOR]
            if thin:
                missing.append({
                    "id": "beat_each", "got": lens, "need": BEAT_EACH_FLOOR, "thin": thin,
                })
            bsum = sum(lens)
            if bsum < BEAT_SUM_FLOOR:
                missing.append({"id": "beat_sum", "got": bsum, "need": BEAT_SUM_FLOOR})
            if len(lens) < 3:
                missing.append({"id": "beat_count", "got": len(lens), "need": 3})
    if "deductions" in fields and fields.get("deductions") is not None:
        dsum = _deduction_sum({"deductions": fields.get("deductions")})
        if dsum > 0 and dsum < DEDUCTION_FLOOR:
            missing.append({"id": "deduction", "got": dsum, "need": DEDUCTION_FLOOR})
    if not missing:
        return None
    bits = [f"{m['id']} {m['got']}<{m['need']}" for m in missing]
    return {
        "code": "iceberg_thin_persist",
        "message": "不能把薄材料存成大纲/节拍/演绎：" + "；".join(bits),
        "missing": missing,
        "role": "iceberg_substrate",
    }


def iceberg_http_detail(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": "iceberg_thin",
        "message": report.get("message") or "冰山未厚",
        "iceberg": report,
        "hint": "先让主编把大纲/每段节拍/演绎写厚；或 danger_draft / skip_iceberg 旁路（会写成口号戏）。",
    }
