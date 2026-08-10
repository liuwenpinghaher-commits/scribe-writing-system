# scribe3/narrative_drive.py
"""章级冲突/事件驱动合同（narrative_drive）· 纯合成 / 校验 / 格式化 / 对齐。

设计真源：``docs/plans/2026-08-10-narrative-event-engine.md`` rev.2.3

产品原则（引导优先）
--------------------
- **只强调一件事**：小说由冲突/事件推动。
- **引导 > 限制**：默认把合同注入 prompt；弱/缺字段 → advisory，不默认整章硬 park。
- **跟着主角逛可以**：只要在逼近/兑现当前冲突或事件，不是空洞巡礼。
- GATE / DETECT 硬拦由旗控制，代码默认关。

本模块无 Surreal / LLM I/O（ensure 除外：可选 st 写回）。
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

_log = logging.getLogger("scribe3.narrative_drive")

SCHEMA = "narrative_drive.v1"
ENGINE_TYPE_EVENT = "event"
MAX_EVENT_DRIVE_BLOCK = 220
ALIGN_JACCARD_MIN = 0.08
ALIGN_HOOK_JACCARD_MIN = 0.06

# 威胁/外力词表（种子与 continuation 弱判定；引导用，非刑典）
_THREAT_LEX: tuple[str, ...] = (
    "债", "禁", "讨", "到期", "期限", "三日", "当夜", "若不", "否则",
    "失", "收", "夺", "逼", "胁", "门", "钥", "匙", "封", "规矩",
    "代价", "若失败", "威胁", "对立", "索", "欠", "还清", "违约",
)

_FAIL_SPLIT_RE = re.compile(
    r"(?:若失败|失败则|否则|若不还|若不|再不|否则将)[，,：:]?\s*(.+)$"
)
_WS_RE = re.compile(r"\s+")


def synopsis_content_fp(synopsis: str | None) -> str:
    """规范化空白后的 synopsis 内容指纹（智能重算比对）。"""
    norm = _WS_RE.sub(" ", (synopsis or "").strip())
    if not norm:
        return ""
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _s(v: Any) -> str:
    return str(v or "").strip()


def _clip(s: str, n: int) -> str:
    s = _s(s)
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)] + "…"


def _has_threat(text: str) -> bool:
    t = _s(text)
    return bool(t) and any(x in t for x in _THREAT_LEX)


def _split_stakes_fail(stakes: str) -> tuple[str, str]:
    """从 stakes 句拆「若失败…」→ (body, if_fail)。"""
    s = _s(stakes)
    m = _FAIL_SPLIT_RE.search(s)
    if m:
        fail = _s(m.group(1))
        body = _s(s[: m.start()])
        return body or s, fail
    return s, ""


def empty_narrative_drive(*, reason: str = "empty") -> dict[str, Any]:
    """弱/空驱动骨架（仍可注入 advisory 引导）。"""
    return {
        "schema": SCHEMA,
        "engine_type": ENGINE_TYPE_EVENT,
        "version": 1,
        "inciting_force": {"kind": "other", "summary": "", "source_refs": []},
        "opposition": {"who_or_what": "", "wants": "", "leverage": ""},
        "deadline_or_cost": {"timer": "", "if_fail": "", "irreversible_if_pay": ""},
        "pov_camera": {
            "focalizer": "",
            "event_owner": "",
            "knower_polarity": "limited",
        },
        "scene_turn": "",
        "end_hook": "",
        "stakes_line": "",
        "anti_stroll": {
            "guidance_opener_hint": [
                "prefer_event_or_confrontation",
                "pov_follow_ok_if_serves_conflict",
            ],
            "required_force_before_mid": False,
        },
        "beats_binding": {
            "require_conflict_trace": True,
            "min_external_before_mid_beat": False,
        },
        "openers_plan": {
            "opener_class": "continuation_hook",
            "first_beat_must": "force_felt_or_conflict_approaching",
        },
        "multi_scene_pov": None,
        "composed_from": {
            "seed_tier": "none",
            "outline_stakes": False,
            "open_inventory_ids": [],
            "reason": reason,
        },
        "validation": {
            "ok": False,
            "errors": ["empty_drive"],
            "warnings": ["drama_weak"],
            "drama_weak": True,
        },
        "source": "assembled",
        "locked": False,
        "synopsis_fp": "",
    }


def validate_narrative_drive(
    drive: dict | None,
    *,
    high_pressure: bool = False,
) -> dict[str, Any]:
    """校验驱动合同；返回 validation 嵌套对象（不改写 drive）。

    引导优先：低压缺字段 → warnings + drama_weak，ok 仍可 True（可注入）。
    高压缺核心字段 → errors，ok=False（GATE 开时才 park；本函数不 park）。
    """
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(drive, dict) or not drive:
        return {
            "ok": False,
            "errors": ["missing_drive"],
            "warnings": ["drama_weak"],
            "drama_weak": True,
        }
    if drive.get("engine_type") not in (None, "", ENGINE_TYPE_EVENT, "event"):
        errors.append("engine_type_not_event")
    inc = drive.get("inciting_force") if isinstance(drive.get("inciting_force"), dict) else {}
    opp = drive.get("opposition") if isinstance(drive.get("opposition"), dict) else {}
    dl = drive.get("deadline_or_cost") if isinstance(drive.get("deadline_or_cost"), dict) else {}
    summary = _s(inc.get("summary"))
    wants = _s(opp.get("wants")) or _s(opp.get("who_or_what"))
    timer = _s(dl.get("timer"))
    if_fail = _s(dl.get("if_fail"))
    scene_turn = _s(drive.get("scene_turn"))
    end_hook = _s(drive.get("end_hook"))

    if not summary:
        (errors if high_pressure else warnings).append("missing_inciting_force")
    if not wants:
        (errors if high_pressure else warnings).append("missing_opposition")
    if not (timer or if_fail):
        (errors if high_pressure else warnings).append("missing_deadline_or_cost")
    if not scene_turn:
        (errors if high_pressure else warnings).append("missing_scene_turn")
    if not end_hook:
        warnings.append("missing_end_hook")

    drama_weak = bool(errors) or (not summary and not wants)
    if drama_weak and "drama_weak" not in warnings and not errors:
        warnings.append("drama_weak")
    ok = not errors
    # 低压：有任意戏剧核 → ok True（引导可注入）
    if not high_pressure and (summary or wants or scene_turn):
        ok = True
        errors = []
    return {
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "drama_weak": drama_weak or (not ok),
    }


def compose_narrative_drive_dict(
    meta: dict | None,
    inventory: dict | None = None,
    prev_hook: str = "",
    *,
    focalizer: str = "",
    preserve_source_refs: list | None = None,
    synopsis: str = "",
    high_pressure: bool | None = None,
) -> dict[str, Any]:
    """从大纲 meta + 可选库存合成 narrative_drive（无 I/O）。

    种子优先级（设计）：inventory 债/禁 → purpose deltas → events → **大纲 stakes**
    → prev_hook → 弱空骨架。**inventory 空不 fail**；大纲 stakes 一等公民。
    """
    meta = meta if isinstance(meta, dict) else {}
    inv = inventory if isinstance(inventory, dict) else {}
    stakes = _s(meta.get("stakes"))
    hook = _s(meta.get("hook"))
    role = _s(meta.get("role") or "推进")
    try:
        pressure = int(meta.get("pressure") or 0)
    except (TypeError, ValueError):
        pressure = 0
    if high_pressure is None:
        try:
            from scribe3.novel_quality_flags import drama_hard_pressure
            thr = int(drama_hard_pressure())
        except Exception:
            thr = 4
        high_pressure = pressure >= thr or role in ("高压", "推进", "高潮", "决战")

    seed_tier = "none"
    open_ids: list[str] = []
    kind = "other"
    summary = ""
    who = ""
    wants = ""
    leverage = ""
    timer = ""
    if_fail = ""
    source_refs: list[str] = list(preserve_source_refs or [])

    # tier A: overdue / open promises（债禁讨）
    for key in ("overdue_promises", "open_promises"):
        for p in inv.get(key) or []:
            if not isinstance(p, dict):
                continue
            lab = _s(p.get("label") or p.get("text") or p.get("summary") or p.get("title"))
            if not lab:
                continue
            if key == "overdue_promises" or _has_threat(lab):
                seed_tier = "inventory"
                kind = "debt_due" if any(x in lab for x in ("债", "欠", "还")) else "third_party_demand"
                summary = lab
                who = _s(p.get("from") or p.get("owner") or p.get("who") or "对立方")
                wants = lab
                pid = _s(p.get("id") or p.get("promise_id"))
                if pid:
                    open_ids.append(pid)
                    if f"promise:{pid}" not in source_refs:
                        source_refs.append(f"promise:{pid}")
                break
        if seed_tier != "none":
            break

    # tier B: purpose deltas
    if seed_tier == "none":
        for d in inv.get("purpose_deltas") or []:
            if not isinstance(d, dict):
                continue
            st = _s(d.get("status")).lower()
            if st and st not in ("planned", "carried"):
                continue
            k = _s(d.get("kind")).lower()
            if k and k not in ("promise", "fact", "knowledge", ""):
                continue
            lab = _s(d.get("summary") or d.get("text") or d.get("label"))
            if not lab:
                continue
            seed_tier = "inventory"
            kind = "opposition_wants"
            summary = lab
            wants = lab
            break

    # tier C: events soft
    if seed_tier == "none":
        for key in ("events_prev", "events_here"):
            for ev in inv.get(key) or []:
                lab = ""
                if isinstance(ev, dict):
                    lab = _s(ev.get("label") or ev.get("text") or ev.get("summary"))
                else:
                    lab = _s(ev)
                if lab and _has_threat(lab):
                    seed_tier = "inventory"
                    kind = "other"
                    summary = lab
                    wants = lab
                    break
            if seed_tier != "none":
                break

    # tier D: outline stakes / hook（一等）
    if seed_tier == "none" and stakes:
        seed_tier = "outline_stakes"
        kind = "outline_stakes"
        body, fail = _split_stakes_fail(stakes)
        summary = body or stakes
        if_fail = fail
        wants = fail or stakes
        who = "局势/对立面"
        if "outline:stakes" not in source_refs:
            source_refs.append("outline:stakes")
    if seed_tier == "none" and hook and _has_threat(hook):
        seed_tier = "outline_stakes"
        kind = "outline_stakes"
        summary = hook
        wants = hook
        if "outline:hook" not in source_refs:
            source_refs.append("outline:hook")

    # tier E: prev_hook continuation
    prev = _s(prev_hook) or _s(inv.get("prev_end_hook"))
    if seed_tier == "none" and prev and _has_threat(prev):
        seed_tier = "prev_hook"
        kind = "continuation_hook"
        summary = prev
        wants = prev
        who = "上章未决威胁"
        if "prev:end_hook" not in source_refs:
            source_refs.append("prev:end_hook")

    # tier F: synopsis 外力句弱提取
    if seed_tier == "none" and synopsis:
        for line in synopsis.splitlines():
            line = _s(line)
            if _has_threat(line) and len(line) >= 4:
                seed_tier = "outline_stakes"
                kind = "outline_stakes"
                summary = _clip(line, 80)
                wants = summary
                break

    if seed_tier == "none":
        drive = empty_narrative_drive(reason="no_seed")
        drive["pov_camera"]["focalizer"] = _s(focalizer)
        drive["end_hook"] = hook or prev
        drive["synopsis_fp"] = synopsis_content_fp(synopsis)
        drive["validation"] = validate_narrative_drive(drive, high_pressure=bool(high_pressure))
        return drive

    if stakes and not if_fail:
        _, fail2 = _split_stakes_fail(stakes)
        if fail2:
            if_fail = fail2
    if not who:
        who = "对立面/外力"
    if not wants:
        wants = summary
    scene_turn = f"因「{_clip(summary, 28)}」局势被迫转向，代价面：{_clip(if_fail or stakes or wants, 28)}"
    end_hook = hook or prev or _clip(summary, 40)
    stakes_line = stakes or (f"若失败，{if_fail}" if if_fail else summary)

    # 开篇引导类（推荐外力；非黑名单刑典）
    opener_class = {
        "debt_due": "debt_or_deadline",
        "taboo_breach": "taboo_or_breach",
        "door_opened": "door_or_seal",
        "third_party_demand": "third_party_demand",
        "deadline": "debt_or_deadline",
        "continuation_hook": "continuation_hook",
        "outline_stakes": "third_party_demand",
    }.get(kind, "third_party_demand")

    drive: dict[str, Any] = {
        "schema": SCHEMA,
        "engine_type": ENGINE_TYPE_EVENT,
        "version": 1,
        "inciting_force": {
            "kind": kind,
            "summary": summary,
            "source_refs": source_refs,
        },
        "opposition": {
            "who_or_what": who,
            "wants": wants,
            "leverage": leverage or _clip(if_fail or stakes, 24),
        },
        "deadline_or_cost": {
            "timer": timer,
            "if_fail": if_fail,
            "irreversible_if_pay": "",
        },
        "pov_camera": {
            "focalizer": _s(focalizer),
            "event_owner": who,
            "knower_polarity": "limited" if _s(focalizer) else "omniscient",
        },
        "scene_turn": scene_turn,
        "end_hook": end_hook,
        "stakes_line": stakes_line,
        "anti_stroll": {
            "guidance_opener_hint": [
                "prefer_event_or_confrontation",
                "pov_follow_ok_if_serves_conflict",
            ],
            "required_force_before_mid": True,
        },
        "beats_binding": {
            "require_conflict_trace": True,
            "min_external_before_mid_beat": True,
        },
        "openers_plan": {
            "opener_class": opener_class,
            "first_beat_must": "opposition_on_stage_or_force_felt",
        },
        "multi_scene_pov": None,
        "composed_from": {
            "seed_tier": seed_tier,
            "outline_stakes": seed_tier == "outline_stakes" or bool(stakes),
            "open_inventory_ids": open_ids,
        },
        "source": "assembled",
        "locked": False,
        "synopsis_fp": synopsis_content_fp(synopsis),
    }
    drive["validation"] = validate_narrative_drive(drive, high_pressure=bool(high_pressure))
    return drive


def format_event_drive_block(
    drive: dict | None,
    *,
    max_chars: int = MAX_EVENT_DRIVE_BLOCK,
    focalizer: str = "",
) -> str:
    """压缩「本章事件驱动」引导块（≤max_chars）。

    引导优先文案：强调冲突/事件推动；允许服务戏的跟主角。
    无实质字段 → 空串（不注入假合同）。
    自带前导 ``\\n\\n``。
    """
    if not isinstance(drive, dict) or not drive:
        return ""
    inc = drive.get("inciting_force") if isinstance(drive.get("inciting_force"), dict) else {}
    opp = drive.get("opposition") if isinstance(drive.get("opposition"), dict) else {}
    dl = drive.get("deadline_or_cost") if isinstance(drive.get("deadline_or_cost"), dict) else {}
    pov = drive.get("pov_camera") if isinstance(drive.get("pov_camera"), dict) else {}
    summary = _s(inc.get("summary"))
    wants = _s(opp.get("wants"))
    who = _s(opp.get("who_or_what"))
    scene_turn = _s(drive.get("scene_turn"))
    end_hook = _s(drive.get("end_hook"))
    if not (summary or wants or scene_turn):
        return ""

    kind = _s(inc.get("kind")) or "event"
    leverage = _s(opp.get("leverage"))
    timer = _s(dl.get("timer"))
    if_fail = _s(dl.get("if_fail"))
    foc = _s(focalizer) or _s(pov.get("focalizer"))
    owner = _s(pov.get("event_owner")) or who
    polar = _s(pov.get("knower_polarity")) or ("limited" if foc else "omniscient")

    # 先拼核心戏（引爆/对立/代价），再拼引导；超预算时裁相机与长引导，不丢冲突核
    header = "## 本章事件驱动（冲突/事件主时钟·优先执行）"
    core_lines = [
        f"- 引爆：{kind} — {_clip(summary, 40)}" if summary else f"- 引爆：{kind}",
    ]
    if who or wants:
        bit = f"- 对立：{_clip(who or '外力', 12)}"
        if wants:
            bit += f" 要 {_clip(wants, 28)}"
        if leverage:
            bit += f"（{_clip(leverage, 12)}）"
        core_lines.append(bit)
    cost_bits = []
    if timer:
        cost_bits.append(_clip(timer, 12))
    if if_fail:
        cost_bits.append(f"败则{_clip(if_fail, 20)}")
    if cost_bits:
        core_lines.append("- 代价：" + "；".join(cost_bits))
    if scene_turn:
        core_lines.append(f"- 翻转：{_clip(scene_turn, 36)}")
    if end_hook:
        core_lines.append(f"- 钩子：{_clip(end_hook, 28)}")

    guide_short = "优先冲突/事件推动；跟主角可以，须服务当前戏。"
    guide_full = (
        "优先写冲突与事件如何推着局势变；跟着主角走可以，"
        "但这段应逼近或兑现当前冲突/事件，避免空洞巡礼。"
    )
    cam = ""
    if foc or owner:
        cam = f"- 相机：{foc or '—'} / 事件主={owner or '—'}"

    def _join(parts: list[str]) -> str:
        return "\n".join(p for p in parts if p)

    # 尝试：核心 + 短引导 + 相机
    candidates = [
        _join([header, *core_lines, "## 引导", guide_full, cam]),
        _join([header, *core_lines, "## 引导", guide_short, cam]),
        _join([header, *core_lines, "## 引导", guide_short]),
        _join([header, *core_lines[:3], "## 引导", guide_short]),
        _join([header, core_lines[0], "## 引导", guide_short]),
    ]
    text = candidates[-1]
    for cand in candidates:
        if len(cand) <= max_chars:
            text = cand
            break
    else:
        text = text[: max_chars - 1] + "…"
    return "\n\n" + text


def align_beats_to_drive(
    beats: list | None,
    drive: dict | None,
    *,
    high_pressure: bool = False,
    chapter_hook: str = "",
) -> dict[str, Any]:
    """节拍是否可追溯到 drive 冲突（轻量 Jaccard；引导用）。

    默认低阈值；失败时低压 → warnings only；高压 + GATE 才可能 park（本函数不 park）。
    """
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(drive, dict) or not drive:
        return {"ok": True, "errors": [], "warnings": ["no_drive"], "matched": False}
    inc = drive.get("inciting_force") if isinstance(drive.get("inciting_force"), dict) else {}
    opp = drive.get("opposition") if isinstance(drive.get("opposition"), dict) else {}
    target = " ".join(filter(None, [_s(inc.get("summary")), _s(opp.get("wants"))]))
    refs = list(inc.get("source_refs") or [])
    if refs:
        # source_refs 非空 → 视为可追溯绕过
        return {
            "ok": True,
            "errors": [],
            "warnings": [],
            "matched": True,
            "via": "source_refs",
        }
    if not target:
        return {"ok": True, "errors": [], "warnings": ["empty_drive_target"], "matched": False}

    try:
        from scribe3.drama_beats import jaccard_cjk
    except Exception:
        def jaccard_cjk(a: str, b: str) -> float:  # type: ignore
            return 0.0

    matched = False
    best = 0.0
    for b in beats or []:
        if not isinstance(b, dict):
            continue
        kind = _s(b.get("kind") or "scene").lower()
        if kind == "bridge":
            continue
        cand = " ".join(
            filter(
                None,
                [
                    _s(b.get("conflict")),
                    _s(b.get("goal")),
                    _s(b.get("text")),
                    _s(b.get("turn")),
                ],
            )
        )
        if not cand:
            continue
        score = jaccard_cjk(cand, target)
        best = max(best, score)
        if score >= ALIGN_JACCARD_MIN:
            matched = True
            break
        # 子串兜底
        if len(target) >= 2 and (target[:4] in cand or cand[:4] in target):
            matched = True
            break

    # 钩子轻对齐
    hook_ok = True
    end_hook = _s(drive.get("end_hook"))
    ch_hook = _s(chapter_hook)
    if end_hook and ch_hook:
        hj = jaccard_cjk(end_hook, ch_hook)
        if hj < ALIGN_HOOK_JACCARD_MIN and end_hook not in ch_hook and ch_hook not in end_hook:
            hook_ok = False
            warnings.append("hook_weak_align")

    ok = matched
    if not matched:
        msg = "drive_beats_mismatch"
        if high_pressure:
            errors.append(msg)
        else:
            warnings.append(msg)
            ok = True  # 低压不拦
    return {
        "ok": ok if high_pressure else True,
        "errors": errors if high_pressure else [],
        "warnings": warnings + ([] if matched else (["drive_beats_mismatch"] if not high_pressure else [])),
        "matched": matched,
        "best_jaccard": best,
        "hook_ok": hook_ok,
    }


def format_narrative_park(drive: dict | None) -> str:
    """可选 GATE 用 park 文案（默认路径不调用）。"""
    val = (drive or {}).get("validation") if isinstance(drive, dict) else {}
    if not isinstance(val, dict):
        val = {}
    errs = ";".join(val.get("errors") or [])[:200]
    return (
        "narrative_incomplete:高压章事件驱动未过（可补大纲 stakes 或 PATCH narrative_drive 后继续）。"
        f"缺口：{errs or '缺 inciting/opposition'}。"
    )


def assemble_narrative_inventory(st: Any, seq: int) -> dict[str, Any]:
    """从 store 装配 inventory（fail-soft；空库存合法）。"""
    inv: dict[str, Any] = {
        "open_promises": [],
        "overdue_promises": [],
        "purpose_deltas": [],
        "events_here": [],
        "events_prev": [],
        "prev_end_hook": "",
    }
    try:
        if hasattr(st, "open_promises"):
            inv["open_promises"] = list(st.open_promises() or [])
    except Exception as e:
        _log.debug("open_promises fail-soft: %s", e)
    try:
        if hasattr(st, "events_at"):
            inv["events_here"] = list(st.events_at(seq) or [])
            if seq > 1:
                inv["events_prev"] = list(st.events_at(seq - 1) or [])
    except Exception as e:
        _log.debug("events_at fail-soft: %s", e)
    try:
        ch = st.get_chapter(seq) or {}
        deltas = ch.get("deltas") or []
        if isinstance(deltas, str):
            import json
            try:
                deltas = json.loads(deltas)
            except (ValueError, TypeError):
                deltas = []
        try:
            from scribe3.purpose import parse_deltas
            parsed = parse_deltas(deltas)
            inv["purpose_deltas"] = [
                d for d in (parsed or [])
                if isinstance(d, dict)
                and _s(d.get("status")).lower() in ("planned", "carried", "")
            ]
        except Exception:
            inv["purpose_deltas"] = [d for d in deltas if isinstance(d, dict)]
    except Exception as e:
        _log.debug("purpose_deltas fail-soft: %s", e)
    try:
        if seq > 1:
            prev = st.get_chapter(seq - 1) or {}
            pbm = prev.get("beats_meta") or {}
            if isinstance(pbm, dict):
                inv["prev_end_hook"] = _s(pbm.get("chapter_hook"))
            pnd = prev.get("narrative_drive") or {}
            if isinstance(pnd, dict) and not inv["prev_end_hook"]:
                inv["prev_end_hook"] = _s(pnd.get("end_hook"))
    except Exception as e:
        _log.debug("prev_end_hook fail-soft: %s", e)
    try:
        from scribe3.volume_signals import overdue_promises_in_range
        promises = inv.get("open_promises") or []
        if promises and callable(overdue_promises_in_range):
            inv["overdue_promises"] = list(
                overdue_promises_in_range(promises, up_to=seq) or []
            )
    except Exception:
        pass
    return inv


def ensure_narrative_drive(
    st: Any,
    seq: int,
    *,
    force: bool = False,
    steer: str = "",
) -> dict[str, Any] | None:
    """引导旗开时合成/刷新章级 narrative_drive 并落库。

    - 默认不 park；作者锁 / source=author 不覆盖（除非 force 或「强制重算驱动」）。
    - 旗关 → 返回 None，不写库。
    """
    try:
        from scribe3.novel_quality_flags import narrative_engine_enabled
        if not narrative_engine_enabled():
            return None
    except Exception:
        return None

    try:
        ch = st.get_chapter(seq) or {}
    except Exception as e:
        _log.warning("ensure_narrative_drive get_chapter failed: %s", e)
        return None

    drive = ch.get("narrative_drive") or {}
    if not isinstance(drive, dict):
        drive = {}
    synopsis = ch.get("synopsis") or ""
    fp_now = synopsis_content_fp(synopsis)
    steer_text = steer or ""
    try:
        if not steer_text and hasattr(st, "get_setting"):
            pass
    except Exception:
        pass
    # steer 从调用方传入；pilot 侧会给
    steer_force = "强制重算驱动" in steer_text or "【强制重算驱动】" in steer_text
    steer_soft = ("重算驱动" in steer_text) and not steer_force

    author_protected = bool(drive.get("locked")) or drive.get("source") == "author"
    if author_protected and not (force or steer_force):
        if drive:
            return drive

    need = (
        force
        or steer_force
        or not drive
        or (drive.get("validation") or {}).get("ok") is False
        or (
            fp_now
            and drive.get("synopsis_fp")
            and fp_now != drive.get("synopsis_fp")
            and not author_protected
            and drive.get("source") != "author"
        )
        or (steer_soft and not author_protected)
    )
    if not need and drive:
        return drive

    inv = assemble_narrative_inventory(st, seq)
    try:
        from scribe3.brief import parse_chapter_meta
        meta = parse_chapter_meta(synopsis) or {}
    except Exception:
        meta = {}
    prev_hook = inv.get("prev_end_hook") or ""
    prev_refs = list((drive.get("inciting_force") or {}).get("source_refs") or []) if drive else []
    prev_ver = int(drive.get("version") or 0) if drive else 0

    new_drive = compose_narrative_drive_dict(
        meta,
        inv,
        prev_hook,
        focalizer=_s(ch.get("focalizer")),
        preserve_source_refs=prev_refs,
        synopsis=synopsis,
    )
    new_drive["source"] = "assembled"
    new_drive["locked"] = False
    new_drive["synopsis_fp"] = fp_now
    new_drive["version"] = prev_ver + 1 if drive else 1

    try:
        st.update_chapter_meta(seq, {"narrative_drive": new_drive})
    except Exception as e:
        _log.warning("ensure_narrative_drive update_chapter_meta failed: %s", e)
        # 仍返回内存对象，供本轮注入
    return new_drive
