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
        prev_raw = st.get_pilot_card(int(seq))
    except Exception as e:
        _log.debug("merge_pilot_card read fail-soft: %s", e)
    card = merge_pilot_card_dict(prev_raw, patch)
    try:
        st.set_pilot_card(int(seq), json.dumps(card, ensure_ascii=False))
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


def format_drive_three_lines(drive: dict | None) -> dict[str, Any]:
    """只读三行摘要：引爆 / 对立 / 钩子（UI 用）。"""
    d = drive if isinstance(drive, dict) else {}
    inc = d.get("inciting_force") if isinstance(d.get("inciting_force"), dict) else {}
    opp = d.get("opposition") if isinstance(d.get("opposition"), dict) else {}
    inciting = str(inc.get("summary") or "").strip()
    who = str(opp.get("who_or_what") or "").strip()
    wants = str(opp.get("wants") or "").strip()
    opposition = " ".join(x for x in (who, f"要 {wants}" if wants else "") if x).strip()
    end_hook = str(d.get("end_hook") or "").strip()
    present = bool(inciting or opposition or end_hook or d.get("scene_turn"))
    return {
        "present": present,
        "inciting": inciting,
        "opposition": opposition,
        "end_hook": end_hook,
        "scene_turn": str(d.get("scene_turn") or "").strip(),
    }


def parse_stakes_presence(synopsis: str | None) -> dict[str, Any]:
    """与 brief.parse_chapter_meta 对齐的轻量 stakes/高压探测（纯函数，无 I/O）。"""
    text = synopsis or ""
    stakes = ""
    try:
        from scribe3.brief import parse_chapter_meta
        meta = parse_chapter_meta(text) or {}
        stakes = str(meta.get("stakes") or "").strip()
        try:
            pressure = int(meta.get("pressure") or 0)
        except (TypeError, ValueError):
            pressure = 0
        role = str(meta.get("role") or "")
    except Exception:
        meta = {}
        pressure = 0
        role = ""
        # fallback 正则
        m = re.search(r"(?:stakes|赌注)\s*[:：]\s*([^\n]+)", text, re.I)
        if m:
            stakes = (m.group(1) or "").strip()
        m2 = re.search(r"压力级\s*[:：]\s*(\d)", text)
        if m2:
            pressure = int(m2.group(1))
        m3 = re.search(r"chapter_role\s*[:：]\s*(\S+)", text, re.I)
        if m3:
            role = m3.group(1)
    high = pressure >= 4 or role in ("高压", "推进", "高潮", "决战")
    warning = ""
    if high and not stakes:
        warning = "missing_outline_stakes"
    return {
        "present": bool(stakes),
        "stakes": stakes,
        "high_pressure": high,
        "pressure": pressure,
        "role": role,
        "warning": warning,
    }


def chapter_execution_soft_status(
    *,
    seq: int = 0,
    prose: str | None = "",
    drive: dict | None = None,
    synopsis: str | None = "",
) -> dict[str, Any]:
    """章执行软状态聚合（只读 · advisory only · 永不 blocking）。

    UI / GET API 同源；与 full_check soft_fulfill 共用 soft_fulfill_drive。
    """
    d = drive if isinstance(drive, dict) else {}
    drive_summary = format_drive_three_lines(d)
    stakes = parse_stakes_presence(synopsis or "")
    prose_s = (prose or "").strip()
    soft = None
    if prose_s:
        soft = soft_fulfill_drive(prose_s, d)
    drift = drive_prose_drift(d, prose_s) if prose_s else {"drift": False, "advisory": "", "reason": "no_prose"}
    return {
        "seq": int(seq or 0),
        "drive_summary": drive_summary,
        "stakes": stakes,
        "soft_fulfill": (
            {
                "ok_soft": soft.get("ok_soft"),
                "gaps": list(soft.get("gaps") or []),
                "quotes": soft.get("quotes"),
                "prose_cn": soft.get("prose_cn"),
                "collapse_combo": soft.get("collapse_combo"),
                "steer_hint": soft.get("steer_hint") or "",
                "severity": "advisory",
            }
            if soft
            else None
        ),
        "drift": {
            "drift": bool(drift.get("drift")),
            "advisory": str(drift.get("advisory") or ""),
            "reason": str(drift.get("reason") or ""),
        },
        "severity": "advisory",
        "has_prose": bool(prose_s),
    }


# ── draft_loop 真源决策（shipped · 单测必须调这些函数）──────────────────

_LEN_GE_STEER_RE = re.compile(r"可见汉字\s*≥\s*(\d{3,5})")
_LEN_CAP_STEER_RE = re.compile(r"(?:勿超过|不超过|可见汉字\s*≤)\s*(\d{3,5})")

BASE_LENGTH_STEER = (
    "本章交完整文学正文：可见汉字目标约 4800–5500 字（去空白后），"
    "连续场景与对话，气味/触感锚，禁止公式注水尾（条N存档/换位完成/观察条/勒紧半指）。"
    "用 ⟦PROPOSAL scope=chapter⟧ 围栏交整章。"
    "宁短勿巷志凑字；密拍预算优先于凑满 4800；欠戏禁止用气味/街景注水。"
    "限知与硬红线优先于戏剧合同与字数目标。"
)
CRAFT_NOVEL_STEER_TAIL = (
    "优先冲突与行动推进，禁止风景巡礼式注水；戏剧合同优先于字数目标。"
)


def build_draft_ec_advisories(
    prose: str | None,
    drive: dict | None,
    *,
    soft_fulfill_on: bool = False,
    drift_on: bool = False,
) -> dict[str, Any]:
    """有 prose 时算 soft_fulfill / drift advisories（纯函数）。

    返回 ``{advisories: list[str], ful: dict|None}``。
    """
    advisories: list[str] = []
    ful = None
    p = (prose or "").strip()
    if not p:
        return {"advisories": [], "ful": None}
    if soft_fulfill_on:
        ful = soft_fulfill_drive(p, drive if isinstance(drive, dict) else None)
        if ful.get("steer_hint"):
            advisories.append(str(ful["steer_hint"]))
    if drift_on:
        dr = drive_prose_drift(drive if isinstance(drive, dict) else None, p)
        if dr.get("drift") and dr.get("advisory"):
            advisories.append(str(dr["advisory"]))
    return {"advisories": advisories, "ful": ful}


def decide_legacy_force_clear(
    prose: str | None,
    steer: str | None,
    *,
    has_drama: bool = False,
) -> bool:
    """现网 steer 清稿规则（强制重写 / 可见汉字≥N / 超长压缩）。纯函数。"""
    prose_now = (prose or "").strip()
    if not prose_now:
        return False
    prose_cn = cn_len(prose_now)
    s = steer or ""
    if not s:
        return False
    m = _LEN_GE_STEER_RE.search(s)
    target = int(m.group(1)) if m else 0
    m_cap = _LEN_CAP_STEER_RE.search(s)
    cap = int(m_cap.group(1)) if m_cap else 0
    if target and prose_cn < target:
        return ("【强制重写】" in s) or (not has_drama)
    if "【强制重写】" in s and (not target) and prose_cn < 4500:
        return True
    if cap and prose_cn > cap and ("【强制重写】" in s or "压缩" in s):
        return True
    return False


def decide_resteer_force_clear(
    *,
    resteer_enabled: bool,
    prose: str | None,
    ful: dict | None,
) -> bool:
    """路径 D：SOFT_FULFILL_RESTEER + collapse_combo。"""
    if not resteer_enabled:
        return False
    if not (prose or "").strip():
        return False
    if not ful or not ful.get("collapse_combo"):
        return False
    return True


def assemble_draft_length_steer(
    *,
    craft_novel: bool = False,
    narrative_engine: bool = False,
    default_drama_steer: bool = False,
    author_steer: str = "",
    fulfill_hint: str = "",
) -> str:
    """组装首写/清稿后生成用的 length_steer（含 EC Bundle）。

    **这是 draft_loop 生成路径的 shipped 真源**；单测必须 import 本函数。
    """
    length_steer = BASE_LENGTH_STEER
    if craft_novel:
        length_steer += CRAFT_NOVEL_STEER_TAIL
    if narrative_engine and default_drama_steer:
        params = resolve_drama_steer_params(author_steer)
        if params.get("enabled"):
            length_steer += format_default_drama_steer(
                dialogue_min=int(params.get("dialogue_min") or DEFAULT_DIALOGUE_MIN),
                soft_len_floor=int(params.get("soft_len_floor") or DEFAULT_SOFT_LEN_FLOOR),
            )
    if fulfill_hint:
        length_steer += " " + str(fulfill_hint)
    return length_steer


def build_draft_loop_msg(
    seq: int,
    length_steer: str,
    author_steer: str = "",
) -> str:
    """loop_chapter 的 msg 字符串（shipped）。"""
    msg = f"按简报与演绎写第{seq}章完整正文。{length_steer}"
    if author_steer:
        msg += f"\n作者意图:{author_steer}"
    return msg


def plan_draft_loop(
    *,
    prose: str | None,
    steer: str = "",
    has_drama: bool = False,
    drive: dict | None = None,
    narrative_engine: bool = False,
    default_drama_steer: bool = False,
    soft_fulfill_on: bool = False,
    drift_on: bool = False,
    resteer_on: bool = False,
    craft_novel: bool = False,
    seq: int = 1,
) -> dict[str, Any]:
    """draft_loop 核心决策（无 I/O）。

    返回::
      {
        "action": "skip" | "generate",
        "force_clear": bool,
        "advisories": list[str],
        "ful": dict|None,
        "length_steer": str,   # generate only
        "msg": str,            # generate only
        "skipped": str|None,
      }

    draft_loop **必须**调用本函数；测试 **必须** import 本函数。
    """
    prose_now = (prose or "").strip()
    adv_pack = build_draft_ec_advisories(
        prose_now,
        drive,
        soft_fulfill_on=soft_fulfill_on,
        drift_on=drift_on,
    )
    advisories = list(adv_pack.get("advisories") or [])
    ful = adv_pack.get("ful")

    force_clear = decide_legacy_force_clear(prose_now, steer, has_drama=has_drama)
    if decide_resteer_force_clear(
        resteer_enabled=resteer_on, prose=prose_now, ful=ful,
    ):
        force_clear = True

    # 清稿后视为无正文
    effective_prose = "" if force_clear else prose_now

    if effective_prose:
        return {
            "action": "skip",
            "force_clear": False,
            "advisories": [a for a in advisories if a],
            "ful": ful,
            "length_steer": "",
            "msg": "",
            "skipped": "正文已在,跳过生成(advisory 稿手动采纳后走此路)",
        }

    hint = ""
    if ful and ful.get("steer_hint") and force_clear:
        hint = str(ful["steer_hint"])
    length_steer = assemble_draft_length_steer(
        craft_novel=craft_novel,
        narrative_engine=narrative_engine,
        default_drama_steer=default_drama_steer,
        author_steer=steer or "",
        fulfill_hint=hint,
    )
    msg = build_draft_loop_msg(seq, length_steer, steer or "")
    return {
        "action": "generate",
        "force_clear": bool(force_clear),
        "advisories": [a for a in advisories if a],
        "ful": ful,
        "length_steer": length_steer,
        "msg": msg,
        "skipped": None,
    }
