# scribe3/execution_contract.py
"""执行合同层（Execution Contract）· 纯函数 steer / fulfill / stamp / drift。

设计真源：``docs/plans/2026-08-10-narrative-rootcause-optimal-execution.md`` rev.1.1

产品原则：引导优先；默认 non-blocking；soft_len_floor=2400；长度 gap 仅与对白低组合。
本模块无 Surreal/LLM I/O（merge_pilot_card 除外，可选 st）。
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

_log = logging.getLogger("scribe3.execution_contract")

DEFAULT_DIALOGUE_MIN = 4
DEFAULT_SOFT_LEN_FLOOR = 2400
DRAMA_STEER_BUNDLE_VER = "v1"

_DIALOGUE_MIN_RE = re.compile(r"对白\s*≥\s*(\d{1,2})")
_LEN_GE_RE = re.compile(r"可见汉字\s*≥\s*(\d{3,5})")
_OPT_OUT_DIALOGUE = ("禁止对白", "少对白", "日记体", "独白章", "无对白")
_QUOTE_RE = re.compile(r'[「"“]')


def cn_len(prose: str | None) -> int:
    return len(re.sub(r"\s+", "", prose or ""))


def count_quotes(prose: str | None) -> int:
    """引号计数（主信号；与 AB 证据口径一致）。"""
    return len(_QUOTE_RE.findall(prose or ""))


def format_default_drama_steer(
    *,
    dialogue_min: int = DEFAULT_DIALOGUE_MIN,
    soft_len_floor: int = DEFAULT_SOFT_LEN_FLOOR,
) -> str:
    """默认首写执行合同文案（≤200 字级；唯一真源）。"""
    return (
        f"执行合同：对白≥{dialogue_min}处且须带对立（要求/拒绝/代价）；"
        f"戏优先于字数；仅当缺对白对立/缺事件推进时 soft 下限约{soft_len_floor}字；"
        f"目标仍约4800–5500但禁止注水；跟主角可以，须逼近或兑现本章事件驱动；"
        f"开篇优先外力/对立。"
    )


def resolve_drama_steer_params(steer: str | None) -> dict[str, Any]:
    """解析作者意图：返回 {enabled, dialogue_min, soft_len_floor, reason?}。"""
    d_min, floor = DEFAULT_DIALOGUE_MIN, DEFAULT_SOFT_LEN_FLOOR
    s = steer or ""
    if any(k in s for k in _OPT_OUT_DIALOGUE):
        return {
            "enabled": False,
            "dialogue_min": d_min,
            "soft_len_floor": floor,
            "reason": "author_opt_out_dialogue",
        }
    m = _DIALOGUE_MIN_RE.search(s)
    if m:
        d_min = max(d_min, int(m.group(1)))
    # 作者可见汉字≥N 用于现网 clear；soft floor 不自动抬到 target（KD-EC-13 解耦）
    return {
        "enabled": True,
        "dialogue_min": d_min,
        "soft_len_floor": floor,
    }


def format_fulfill_hint(gaps: list[str]) -> str:
    if not gaps:
        return ""
    bits = []
    if "dialogue_low" in gaps:
        bits.append("对白偏少或缺对立（要求/拒绝/代价）")
    if "short_and_dialogue_low" in gaps:
        bits.append("短稿且对白不足，建议扩写戏与对白")
    if "opener_weak_with_low_dialogue" in gaps:
        bits.append("开篇外力弱且对白不足")
    return "执行合同 soft：" + "；".join(bits) + "。（advisory only，不硬停）"


def soft_fulfill_drive(
    prose: str | None,
    drive: dict | None = None,
    *,
    dialogue_min: int = DEFAULT_DIALOGUE_MIN,
    soft_len_floor: int = DEFAULT_SOFT_LEN_FLOOR,
) -> dict[str, Any]:
    """写后 soft 履约。永远 severity=advisory；永不 blocking。"""
    from scribe3.narrative_drive import soft_opener_event_trace

    quotes = count_quotes(prose)
    prose_cn = cn_len(prose)
    opener = soft_opener_event_trace(prose or "", drive if isinstance(drive, dict) else None)
    gaps: list[str] = []
    if quotes < dialogue_min:
        gaps.append("dialogue_low")
    # 长度：仅与对白低组合（pass2≈2983 且 quotes 高 → 不 length-fail）
    if prose_cn < soft_len_floor and quotes < dialogue_min:
        gaps.append("short_and_dialogue_low")
    if not opener.get("force_felt") and quotes < dialogue_min:
        gaps.append("opener_weak_with_low_dialogue")
    collapse_combo = (
        quotes < dialogue_min
        and prose_cn < soft_len_floor
        and not bool(opener.get("force_felt"))
    )
    return {
        "ok_soft": not gaps,
        "quotes": quotes,
        "prose_cn": prose_cn,
        "opener": opener,
        "gaps": gaps,
        "collapse_combo": collapse_combo,
        "steer_hint": format_fulfill_hint(gaps),
        "severity": "advisory",
        "dialogue_min": dialogue_min,
        "soft_len_floor": soft_len_floor,
    }


def drive_content_fp(drive: dict | None, synopsis_fp: str = "") -> str:
    """drive core 指纹；version 不参与（OQ-EC-8）。"""
    d = drive if isinstance(drive, dict) else {}
    inc = d.get("inciting_force") if isinstance(d.get("inciting_force"), dict) else {}
    opp = d.get("opposition") if isinstance(d.get("opposition"), dict) else {}
    core = "|".join(
        [
            str(inc.get("summary") or ""),
            str(opp.get("who_or_what") or ""),
            str(opp.get("wants") or ""),
            str(d.get("end_hook") or ""),
            str(d.get("scene_turn") or ""),
            str(d.get("stakes_line") or ""),
        ]
    )
    raw = f"{synopsis_fp or d.get('synopsis_fp') or ''}|{core}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_execution_stamp(
    drive: dict | None,
    prose: str | None,
    *,
    drama_steer_bundle: str = DRAMA_STEER_BUNDLE_VER,
) -> dict[str, Any]:
    """写成功后的 stamp 对象。"""
    from datetime import datetime, timezone

    d = drive if isinstance(drive, dict) else {}
    syn_fp = str(d.get("synopsis_fp") or "")
    try:
        from scribe3.review.fp import prose_fp as _prose_fp
        pfp = _prose_fp(prose)
    except Exception:
        pfp = hashlib.sha256((prose or "").encode("utf-8")).hexdigest()[:16]
    return {
        "drive_content_fp": drive_content_fp(d, syn_fp),
        "synopsis_fp": syn_fp,
        "prose_fp_at_write": pfp,
        "drama_steer_bundle": drama_steer_bundle,
        "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def drive_prose_drift(
    drive: dict | None,
    prose: str | None,
    stamp: dict | None = None,
) -> dict[str, Any]:
    """检测合同 core 是否相对 stamp 漂移。永不 clear。"""
    d = drive if isinstance(drive, dict) else {}
    st = stamp if isinstance(stamp, dict) else (d.get("execution_stamp") if isinstance(d.get("execution_stamp"), dict) else {})
    if not st:
        return {"drift": False, "reason": "no_stamp", "advisory": ""}
    cur = drive_content_fp(d, str(d.get("synopsis_fp") or st.get("synopsis_fp") or ""))
    old = str(st.get("drive_content_fp") or "")
    if old and cur and old != cur:
        return {
            "drift": True,
            "reason": "drive_core_changed",
            "advisory": "执行合同 soft：本章 narrative_drive 核心相对上次成稿已变，建议【强制重写】或核对正文（advisory only）。",
            "old_fp": old,
            "new_fp": cur,
        }
    return {"drift": False, "reason": "ok", "advisory": ""}


def preserve_execution_stamp(new_drive: dict, prev_drive: dict | None) -> dict:
    """ensure recompose 时保留 stamp（除非 prev 无 stamp）。"""
    if not isinstance(new_drive, dict):
        return new_drive
    prev = prev_drive if isinstance(prev_drive, dict) else {}
    stamp = prev.get("execution_stamp")
    if isinstance(stamp, dict) and stamp:
        new_drive["execution_stamp"] = stamp
    return new_drive


def attach_execution_stamp(drive: dict | None, prose: str | None) -> dict:
    """写成功：更新 stamp 到 drive 副本。"""
    d = dict(drive) if isinstance(drive, dict) else {}
    d["execution_stamp"] = build_execution_stamp(d, prose)
    return d


def merge_pilot_card_dict(prev: Any, patch: dict) -> dict:
    """纯函数：深度合并 pilot_card（一层键覆盖；嵌套 dict 浅 merge）。"""
    card: dict
    if isinstance(prev, dict):
        card = dict(prev)
    elif isinstance(prev, str) and prev.strip():
        try:
            parsed = json.loads(prev)
            card = dict(parsed) if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            card = {}
    else:
        card = {}
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(card.get(k), dict):
            merged = dict(card[k])
            merged.update(v)
            card[k] = merged
        else:
            card[k] = v
    return card


def merge_pilot_card(st: Any, seq: int, patch: dict) -> None:
    """Read-modify-write pilot_card；禁止整卡单键覆盖。"""
    if not patch:
        return
    prev_raw = None
    try:
        rows = st._query(
            "SELECT pilot_card FROM type::record('chapter',$seq)",
            {"seq": int(seq)},
        )
        if rows:
            prev_raw = rows[0].get("pilot_card")
    except Exception as e:
        _log.debug("merge_pilot_card read fail-soft: %s", e)
    card = merge_pilot_card_dict(prev_raw, patch)
    try:
        st._execute_write(
            "UPDATE type::record('chapter',$seq) SET pilot_card=$c",
            {"seq": int(seq), "c": json.dumps(card, ensure_ascii=False)},
        )
    except Exception as e:
        _log.warning("merge_pilot_card write fail-soft: %s", e)


def summarize_soft_fulfill(ful: dict | None) -> dict[str, Any]:
    """pilot_card 摘要（小）。"""
    f = ful if isinstance(ful, dict) else {}
    return {
        "ok_soft": f.get("ok_soft"),
        "quotes": f.get("quotes"),
        "prose_cn": f.get("prose_cn"),
        "gaps": list(f.get("gaps") or [])[:8],
        "collapse_combo": f.get("collapse_combo"),
        "severity": "advisory",
    }


def count_dialogue_keyword_hits(text: str | None) -> int:
    return (text or "").count("对白")
