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
        # OI-1：无种子亦做大纲 enrich 观测（advisory）
        return _absorb_outline_fields(drive, meta, high_pressure=bool(high_pressure))

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
    # OI-1：显式 enrich 纪律（source_refs / outline_hook_absorbed / missing_outline_stakes）
    return _absorb_outline_fields(drive, meta, high_pressure=bool(high_pressure))


def _absorb_outline_fields(
    drive: dict,
    meta: dict | None,
    *,
    high_pressure: bool = False,
) -> dict:
    """幂等大纲 enrich：不改 seed_tier；补 source_refs / 观测键 / advisory warning。

    字段级 stakes_line/end_hook 收尾与现网 compose 对齐；本函数只保证可观测性合同。
    """
    if not isinstance(drive, dict):
        return drive
    meta = meta if isinstance(meta, dict) else {}
    stakes = _s(meta.get("stakes"))
    hook = _s(meta.get("hook"))

    cf = drive.get("composed_from") if isinstance(drive.get("composed_from"), dict) else {}
    if not isinstance(cf, dict):
        cf = {}
    drive["composed_from"] = cf

    inc = drive.get("inciting_force") if isinstance(drive.get("inciting_force"), dict) else {}
    refs = list(inc.get("source_refs") or [])
    dl = drive.get("deadline_or_cost") if isinstance(drive.get("deadline_or_cost"), dict) else {}
    if not isinstance(dl, dict):
        dl = {"timer": "", "if_fail": "", "irreversible_if_pay": ""}

    if stakes:
        drive["stakes_line"] = stakes
        if not _s(dl.get("if_fail")):
            _, fail = _split_stakes_fail(stakes)
            if fail:
                dl["if_fail"] = fail
                drive["deadline_or_cost"] = dl
        if "outline:stakes" not in refs:
            refs.append("outline:stakes")
        cf["outline_stakes"] = True

    if hook:
        drive["end_hook"] = hook
        cf["outline_hook_absorbed"] = True
        if "outline:hook" not in refs:
            refs.append("outline:hook")
    else:
        # 未提供 hook 时不强制 False（旧 drive 回填用「缺键」判定）
        if "outline_hook_absorbed" not in cf:
            cf["outline_hook_absorbed"] = False

    if not isinstance(inc, dict):
        inc = {"kind": "other", "summary": "", "source_refs": refs}
    else:
        inc = {**inc, "source_refs": refs}
    drive["inciting_force"] = inc

    val = drive.get("validation") if isinstance(drive.get("validation"), dict) else {}
    if not isinstance(val, dict):
        val = {"ok": True, "errors": [], "warnings": [], "drama_weak": False}
    warns = list(val.get("warnings") or [])
    if high_pressure and not stakes:
        if "missing_outline_stakes" not in warns:
            warns.append("missing_outline_stakes")
    val["warnings"] = warns
    drive["validation"] = val
    return drive


def needs_outline_enrich_recompose(
    drive: dict | None,
    synopsis: str = "",
    meta: dict | None = None,
) -> bool:
    """OI 上线回填谓词：旧 ok drive 缺 enrich 观测键时需 recompose。"""
    if not isinstance(drive, dict) or not drive:
        return True
    if (drive.get("validation") or {}).get("ok") is False:
        return True
    if meta is None:
        try:
            from scribe3.brief import parse_chapter_meta
            meta = parse_chapter_meta(synopsis or "") or {}
        except Exception:
            meta = {}
    meta = meta if isinstance(meta, dict) else {}
    stakes = _s(meta.get("stakes"))
    hook = _s(meta.get("hook"))
    cf = drive.get("composed_from") if isinstance(drive.get("composed_from"), dict) else {}
    refs = list(
        ((drive.get("inciting_force") or {}).get("source_refs") or [])
        if isinstance(drive.get("inciting_force"), dict)
        else []
    )
    if hook and not cf.get("outline_hook_absorbed"):
        return True
    if stakes and "outline:stakes" not in refs:
        return True
    if hook and "outline:hook" not in refs:
        return True
    return False


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

    # OI-3 / EC-1：对白净增；DEFAULT_DRAMA_STEER 开时固定 micro 给 core 让预算
    guide_full = (
        "优先冲突/事件；对白须带对立（要求/拒绝/代价）；"
        "跟主角可以，须逼近或兑现当前戏。"
    )
    guide_short = "对白承载对立；逼近戏；冲突优先。"
    guide_micro = "对白对立；逼近戏。"  # ≤24 字
    prefer_micro = False
    try:
        from scribe3.novel_quality_flags import (
            default_drama_steer_enabled,
            narrative_engine_enabled,
        )
        prefer_micro = bool(narrative_engine_enabled() and default_drama_steer_enabled())
    except Exception:
        prefer_micro = False
    cam = ""
    if foc or owner:
        cam = f"- 相机：{foc or '—'} / 事件主={owner or '—'}"

    def _join(parts: list[str]) -> str:
        return "\n".join(p for p in parts if p)

    # 裁剪：先丢 cam → 缩 guide → 保核心前三行（引爆/对立/代价）
    if prefer_micro:
        candidates = [
            _join([header, *core_lines, "## 引导", guide_micro, cam]),
            _join([header, *core_lines, "## 引导", guide_micro]),
            _join([header, *core_lines[:3], "## 引导", guide_micro]),
            _join([header, core_lines[0], "## 引导", guide_micro]),
        ]
    else:
        candidates = [
            _join([header, *core_lines, "## 引导", guide_full, cam]),
            _join([header, *core_lines, "## 引导", guide_short, cam]),
            _join([header, *core_lines, "## 引导", guide_short]),
            _join([header, *core_lines[:3], "## 引导", guide_micro]),
            _join([header, core_lines[0], "## 引导", guide_micro]),
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
    recompose_if: str | None = None,
    dry_run: bool = False,
    include_author: bool = False,
) -> dict[str, Any] | None:
    """引导旗开时合成/刷新章级 narrative_drive 并落库。

    - 默认不 park；作者锁 / source=author 不覆盖（除非 force+include_author 或「强制重算驱动」）。
    - recompose_if: None | \"outline_enrich\" | \"always\"（always 等价 force）
    - dry_run: 不写库，返回将合成的 drive（或现 drive）
    - 旗关 → 返回 None，不写库。
    """
    try:
        from scribe3.novel_quality_flags import narrative_engine_enabled
        if not narrative_engine_enabled():
            return None
    except Exception:
        return None

    if recompose_if == "always":
        force = True

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
    # steer 从调用方传入；pilot 侧会给
    steer_force = "强制重算驱动" in steer_text or "【强制重算驱动】" in steer_text
    steer_soft = ("重算驱动" in steer_text) and not steer_force

    author_protected = bool(drive.get("locked")) or drive.get("source") == "author"
    if author_protected and not ((force and include_author) or steer_force):
        if drive:
            return drive

    try:
        from scribe3.brief import parse_chapter_meta
        meta = parse_chapter_meta(synopsis) or {}
    except Exception:
        meta = {}

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
        or (
            recompose_if == "outline_enrich"
            and not author_protected
            and needs_outline_enrich_recompose(drive, synopsis, meta)
        )
    )
    if not need and drive:
        return drive

    inv = assemble_narrative_inventory(st, seq)
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
    # IA KD-IA-5：end_hook 与 drama 共用 chapter_hooks SSOT（非仅 synopsis meta.hook）
    try:
        from scribe3.chapter_hooks import resolve_chapter_hook
        resolved_hook = resolve_chapter_hook(
            ch, synopsis_meta=meta, prev_end_hook=prev_hook,
        )
        if resolved_hook:
            new_drive["end_hook"] = resolved_hook
    except Exception as e:
        _log.debug("resolve_chapter_hook fail-soft: %s", e)
    new_drive["source"] = "assembled"
    new_drive["locked"] = False
    new_drive["synopsis_fp"] = fp_now
    new_drive["version"] = prev_ver + 1 if drive else 1
    # EC-3：recompose 保留 execution_stamp
    try:
        from scribe3.execution_contract import preserve_execution_stamp
        new_drive = preserve_execution_stamp(new_drive, drive)
    except Exception:
        pass

    if dry_run:
        return new_drive

    try:
        st.update_chapter_meta(seq, {"narrative_drive": new_drive})
    except Exception as e:
        _log.warning("ensure_narrative_drive update_chapter_meta failed: %s", e)
        # 仍返回内存对象，供本轮注入
    return new_drive


def ensure_narrative_drive_range(
    st: Any,
    *,
    seqs: list[int] | None = None,
    force: bool = False,
    steer: str = "",
    recompose_if: str | None = None,
    dry_run: bool = True,
    max_seqs: int = 200,
    include_author: bool = False,
) -> dict[str, Any]:
    """ENGINE=1 批量 ensure。串行、fail-soft、永不 park。

    默认 dry_run=True（CLI 安全）。返回统计字段见设计 KD-OI-13。
    """
    stats: dict[str, Any] = {
        "enabled": False,
        "total": 0,
        "rewritten": 0,
        "already_ok_skip": 0,
        "skipped_locked": 0,
        "empty_seed": 0,
        "ensured_ok": 0,
        "dry_run_would_write": [],
        "errors": [],
        "coverage_ratio": 0.0,
        "dry_run": bool(dry_run),
        "recompose_if": recompose_if,
        "force": bool(force),
    }
    try:
        from scribe3.novel_quality_flags import narrative_engine_enabled
        if not narrative_engine_enabled():
            return stats
    except Exception:
        return stats
    stats["enabled"] = True

    if seqs is None:
        chapters: list = []
        try:
            if hasattr(st, "chapters_lite"):
                chapters = list(st.chapters_lite() or [])
            else:
                chapters = list(st.list_chapters() or [])
        except Exception as e:
            stats["errors"].append(f"list_chapters:{e}")
            chapters = []
        targets: list[int] = []
        for c in chapters:
            if not isinstance(c, dict):
                continue
            try:
                seq = int(c.get("seq"))
            except (TypeError, ValueError):
                continue
            # chapters_lite 有 synopsis/beats；list_chapters 仅 seq/title → 全收再按章 ensure
            if (
                _s(c.get("synopsis"))
                or c.get("beats")
                or c.get("narrative_drive")
                or ("synopsis" not in c and "beats" not in c)
            ):
                targets.append(seq)
    else:
        targets = [int(s) for s in seqs]

    targets = targets[: max(1, int(max_seqs or 200))]
    stats["total"] = len(targets)

    for seq in targets:
        try:
            ch = st.get_chapter(seq) or {}
            drive = ch.get("narrative_drive") or {}
            if not isinstance(drive, dict):
                drive = {}
            author_protected = bool(drive.get("locked")) or drive.get("source") == "author"
            if author_protected and not (force and include_author):
                # 仍可能因 steer_force 重算，这里 CLI 默认跳过
                if not force or not include_author:
                    stats["skipped_locked"] += 1
                    continue

            before = drive
            # 探测是否 need：dry_run 时用 ensure 的 dry_run
            out = ensure_narrative_drive(
                st,
                seq,
                force=force,
                steer=steer,
                recompose_if=recompose_if,
                dry_run=True,
                include_author=include_author,
            )
            if out is None:
                continue
            # 比较是否会写：version 增或字段变
            would = (
                not before
                or out.get("version") != before.get("version")
                or out.get("synopsis_fp") != before.get("synopsis_fp")
                or (out.get("composed_from") or {}) != (before.get("composed_from") or {})
                or (out.get("inciting_force") or {}).get("source_refs")
                != (before.get("inciting_force") or {}).get("source_refs")
            )
            # 若 ensure 内部 need=False 会返回原 drive 同 version
            if not would and before:
                stats["already_ok_skip"] += 1
                # 仍计可注入
                if format_event_drive_block(before):
                    stats["ensured_ok"] += 1
                continue

            if dry_run:
                stats["dry_run_would_write"].append(seq)
                if format_event_drive_block(out):
                    stats["ensured_ok"] += 1
                cf = (out.get("composed_from") or {})
                if cf.get("seed_tier") == "none" or (out.get("validation") or {}).get("drama_weak"):
                    stats["empty_seed"] += 1
                continue

            written = ensure_narrative_drive(
                st,
                seq,
                force=force,
                steer=steer,
                recompose_if=recompose_if,
                dry_run=False,
                include_author=include_author,
            )
            stats["rewritten"] += 1
            if written and format_event_drive_block(written):
                stats["ensured_ok"] += 1
            if written and (
                (written.get("composed_from") or {}).get("seed_tier") == "none"
                or (written.get("validation") or {}).get("drama_weak")
            ):
                stats["empty_seed"] += 1
        except Exception as e:
            stats["errors"].append(f"seq={seq}:{e}")
            if len(stats["errors"]) > 20:
                stats["errors"].append("…truncated")
                break

    tot = max(int(stats["total"] or 0), 1)
    stats["coverage_ratio"] = round(float(stats["ensured_ok"]) / tot, 4)
    return stats


# ── H2 · EVENT_LED 写后检测（完整 soft findings · 非仅 opener）────────────

_DIALOGUE_MARK_RE = re.compile(r"[「」『』""\"']")
_CONFLICT_LEX: tuple[str, ...] = (
    "对峙", "冲突", "逼", "威胁", "对立", "反抗", "拒绝", "争夺", "交锋",
    "质问", "怒", "抗", "阻", "拦", "夺", "讨债", "违约", "代价",
)


def _drive_anchor_phrases(drive: dict | None) -> dict[str, str]:
    """从 drive 抽出 inciting / opposition / hook 短语。"""
    d = drive if isinstance(drive, dict) else {}
    inc = d.get("inciting_force") if isinstance(d.get("inciting_force"), dict) else {}
    opp = d.get("opposition") if isinstance(d.get("opposition"), dict) else {}
    return {
        "inciting": _s(inc.get("summary")),
        "opposition_who": _s(opp.get("who_or_what")),
        "opposition_wants": _s(opp.get("wants")),
        "scene_turn": _s(d.get("scene_turn")),
        "end_hook": _s(d.get("end_hook")),
        "stakes_line": _s(d.get("stakes_line")),
    }


def _phrase_in_prose(phrase: str, prose: str, *, min_len: int = 2) -> bool:
    p = _s(phrase)
    if len(p) < min_len:
        return False
    # 整句或前缀片段命中
    if p in prose:
        return True
    if len(p) >= 4 and p[:4] in prose:
        return True
    if len(p) >= 6 and p[:6] in prose:
        return True
    # 空格/标点切词后 token 命中
    tokens = [t for t in re.split(r"[\s，。；、：:！？,.!?;]+", p) if len(t) >= 2]
    if tokens:
        hits = sum(1 for t in tokens if t in prose)
        if hits >= max(1, min(2, (len(tokens) + 1) // 2)):
            return True
    # 中文连续 2～3 字窗口：任一命中即认为有痕迹（soft 对齐，非精确引用）
    windows = set()
    for n in (3, 2):
        if len(p) < n:
            continue
        for i in range(0, len(p) - n + 1):
            w = p[i : i + n]
            if re.search(r"[\u4e00-\u9fff]", w):
                windows.add(w)
    hit_w = sum(1 for w in windows if w in prose)
    # 至少 2 个窗口命中，或短语短时 1 个即可
    need = 1 if len(p) <= 4 else 2
    return hit_w >= need


def detect_event_led(
    prose: str | None,
    drive: dict | None = None,
) -> dict[str, Any]:
    """写后事件驱动对齐检测（advisory only · 永不 blocking）。

    对 drive 的 inciting / opposition / hook 与正文做轻量词面/对白/冲突句对齐。
    与 soft_opener_event_trace 互补：本函数看全文事件履约，非仅开篇 15%。
    """
    text = prose or ""
    prose_cn = len(re.sub(r"\s+", "", text))
    anchors = _drive_anchor_phrases(drive)
    gaps: list[str] = []
    quotes: list[str] = []
    hits: list[str] = []

    has_drive_core = bool(
        anchors["inciting"] or anchors["opposition_who"] or anchors["opposition_wants"]
        or anchors["scene_turn"] or anchors["end_hook"]
    )

    if not text.strip():
        if has_drive_core:
            gaps.extend(["empty_prose", "missing_inciting_trace", "missing_opposition_trace"])
        else:
            gaps.append("empty_prose")
        return {
            "ok_soft": False,
            "gaps": gaps,
            "quotes": quotes,
            "hits": hits,
            "advisory": True,
            "severity": "advisory",
            "detector": "event_led_detect",
            "type": "event_led_detect",
            "prose_cn": prose_cn,
            "anchors_present": has_drive_core,
            "note": "无正文可对齐事件驱动（advisory）",
        }

    # 对白痕迹
    has_dialogue = bool(_DIALOGUE_MARK_RE.search(text)) or text.count("说") >= 2
    if has_dialogue:
        hits.append("dialogue_marks")
        quotes.append("dialogue")

    # 冲突词
    conflict_hits = [w for w in _CONFLICT_LEX if w in text]
    if conflict_hits:
        hits.append("conflict_lex")
        quotes.extend(conflict_hits[:4])

    # 外力/威胁词（复用全局 _THREAT_LEX）
    threat_hits = [w for w in _THREAT_LEX if w in text]
    if threat_hits:
        hits.append("threat_lex")

    # drive 锚对齐
    if anchors["inciting"]:
        if _phrase_in_prose(anchors["inciting"], text):
            hits.append("inciting_aligned")
            quotes.append(anchors["inciting"][:24])
        else:
            gaps.append("missing_inciting_trace")
    elif has_drive_core:
        pass  # 无 inciting 字段不硬 gap

    opp_blob = " ".join(
        x for x in (anchors["opposition_who"], anchors["opposition_wants"]) if x
    )
    if opp_blob:
        if (
            _phrase_in_prose(anchors["opposition_who"], text)
            or _phrase_in_prose(anchors["opposition_wants"], text)
            or any(w in text for w in conflict_hits[:3])
        ):
            hits.append("opposition_aligned")
        else:
            # 有对白+威胁词也可 soft 过对立
            if has_dialogue and threat_hits:
                hits.append("opposition_soft_via_dialogue_threat")
            else:
                gaps.append("missing_opposition_trace")

    if anchors["end_hook"] or anchors["scene_turn"]:
        hook_ok = (
            _phrase_in_prose(anchors["end_hook"], text)
            or _phrase_in_prose(anchors["scene_turn"], text)
        )
        if hook_ok:
            hits.append("hook_or_turn_aligned")
        elif prose_cn >= 200 and not (has_dialogue or threat_hits or conflict_hits):
            gaps.append("missing_hook_or_turn_trace")

    # 无 drive 时：仅检查正文是否有事件感
    if not has_drive_core:
        if not (has_dialogue or threat_hits or conflict_hits):
            gaps.append("no_event_signal_in_prose")
        hits.append("no_drive_advisory")

    ok_soft = not gaps
    note_bits = []
    if ok_soft:
        note_bits.append("事件驱动 soft 对齐可过")
    else:
        note_bits.append("事件驱动对齐有缺口：" + "、".join(gaps))
    return {
        "ok_soft": ok_soft,
        "gaps": gaps,
        "quotes": quotes[:12],
        "hits": hits[:16],
        "advisory": True,
        "severity": "advisory",
        "detector": "event_led_detect",
        "type": "event_led_detect",
        "prose_cn": prose_cn,
        "anchors_present": has_drive_core,
        "has_dialogue": has_dialogue,
        "note": "；".join(note_bits) + "（advisory only，不硬停）",
    }


def maybe_event_led_detect(
    prose: str | None,
    drive: dict | None = None,
    *,
    seq: int | None = None,
) -> dict[str, Any] | None:
    """旗 SCRIBE3_EVENT_LED_DETECT 开时跑 detect；关则 None。永不 park。"""
    try:
        from scribe3.novel_quality_flags import event_led_detect_enabled
        if not event_led_detect_enabled():
            return None
    except Exception:
        return None
    finding = detect_event_led(prose, drive)
    _log.info(
        "event_led_detect seq=%s ok_soft=%s gaps=%s hits=%s",
        seq,
        finding.get("ok_soft"),
        finding.get("gaps"),
        finding.get("hits"),
    )
    return finding


# ── OI-5 · 开篇 soft 痕迹（净新建；与 EVENT_LED 互补）──────────────────────

_OPENER_FORCE_LEX: tuple[str, ...] = (
    "债", "禁", "讨", "到期", "若不", "否则", "逼", "胁", "钥", "匙",
    "门闩", "索", "欠", "规矩", "代价", "对立", "威胁", "收", "夺",
)


def head_span_text(prose: str) -> str:
    """对齐设计：max(ceil(0.15*n), first_two_paras 长度) 的前缀。"""
    import math
    t = prose or ""
    if not t.strip():
        return ""
    # 前两段
    paras = [p for p in re.split(r"\n\s*\n", t.strip()) if p.strip()]
    first_two = "\n\n".join(paras[:2]) if paras else t
    n = len(re.sub(r"\s+", "", t))
    need = max(int(math.ceil(0.15 * max(n, 1))), len(re.sub(r"\s+", "", first_two)))
    # 按字符粗截（含空白），保证覆盖 need 可见字
    acc = []
    cn = 0
    for ch in t:
        acc.append(ch)
        if not ch.isspace():
            cn += 1
        if cn >= need:
            break
    return "".join(acc)


def soft_opener_event_trace(prose: str, drive: dict | None = None) -> dict[str, Any]:
    """开篇 15% 是否有外力/对立痕迹（确定性 soft）。永不 blocking。"""
    head = head_span_text(prose or "")
    hits = [w for w in _OPENER_FORCE_LEX if w in head]
    # drive 锚
    if isinstance(drive, dict):
        inc = _s((drive.get("inciting_force") or {}).get("summary"))
        if inc and len(inc) >= 2 and inc[:4] in head:
            hits.append("drive_inciting_span")
    force_felt = bool(hits)
    return {
        "type": "opener_soft_trace",
        "severity": "advisory",
        "detector": "opener_soft_trace",
        "force_felt": force_felt,
        "hits": hits[:12],
        "head_len": len(re.sub(r"\s+", "", head)),
        "note": (
            "开篇可感外力/对立痕迹" if force_felt else "开篇偏空；可更早落地冲突/事件（advisory）"
        ),
    }


def maybe_log_opener_soft_trace(
    prose: str,
    drive: dict | None = None,
    *,
    seq: int | None = None,
) -> dict[str, Any] | None:
    """旗 SCRIBE3_OPENER_SOFT_TRACE=1 时 logging；永不 park。"""
    try:
        from scribe3.novel_quality_flags import opener_soft_trace_enabled
        if not opener_soft_trace_enabled():
            return None
    except Exception:
        return None
    finding = soft_opener_event_trace(prose, drive)
    _log.info(
        "opener_soft_trace seq=%s force_felt=%s hits=%s note=%s",
        seq,
        finding.get("force_felt"),
        finding.get("hits"),
        finding.get("note"),
    )
    return finding


# ── OI-6 · 比喻密度 soft ──────────────────────────────────────────────────

_METAPHOR_RE = re.compile(r"像|仿佛|宛如|好似|如同|恍若")


def metaphor_density_per_1k(prose: str) -> float:
    t = prose or ""
    cn = len(re.sub(r"\s+", "", t))
    if cn <= 0:
        return 0.0
    return round(1000.0 * len(_METAPHOR_RE.findall(t)) / cn, 2)


def soft_metaphor_density_trace(prose: str, *, threshold: float = 6.0) -> dict[str, Any]:
    dens = metaphor_density_per_1k(prose)
    over = dens > float(threshold)
    return {
        "type": "metaphor_soft",
        "severity": "advisory",
        "detector": "metaphor_soft",
        "density_per_1k": dens,
        "threshold": float(threshold),
        "over": over,
        "note": (
            f"比喻约 {dens}/千字，超过建议阈值 {threshold}（advisory）"
            if over
            else f"比喻约 {dens}/千字"
        ),
    }


def maybe_log_metaphor_soft(
    prose: str,
    *,
    seq: int | None = None,
) -> dict[str, Any] | None:
    """SCRIBE3_METAPHOR_SOFT_PER_1K>0 时 logging；0=关。"""
    try:
        from scribe3.novel_quality_flags import metaphor_soft_per_1k
        thr = metaphor_soft_per_1k()
        if thr <= 0:
            return None
    except Exception:
        return None
    finding = soft_metaphor_density_trace(prose, threshold=float(thr))
    if finding.get("over"):
        _log.info(
            "metaphor_soft seq=%s density=%s thr=%s",
            seq,
            finding.get("density_per_1k"),
            thr,
        )
    return finding

