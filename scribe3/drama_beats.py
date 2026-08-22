from scribe3.feature_flags import get_flag
# scribe3/drama_beats.py
"""戏剧节拍校验 · 纯函数（PR-1）。

真源：``docs/plans/2026-08-10-novel-quality-first-pipeline-optimization.md``
（Issue 5 · ``validate_drama_beats`` / beats.v2）

本模块 **无** LLM / 网络 / Surreal；仅对 ``list[dict]`` 节拍做确定性门检。
PR-1：``validate_drama_beats`` / ``drama_score``。
PR-3：``extract_drama_gaps`` / ``format_drama_gate_park_reason`` / ``should_drama_gate_park``
（写前 park 接线在 ``pilot_runtime.expand_beats``，本模块仍纯函数）。
PR-4：``format_drama_block`` / ``beats_have_drama_gcd``（草稿/简报戏剧合同注入）。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

# ── 角色 / 词表（设计 § 初版；单测锁定）──────────────────────────────────

HIGH_ROLES = frozenset({"高压", "推进"})
LOW_ROLES = frozenset({"低压", "关系回收", "修炼", "信息整理"})

# 失败/两难/不可逆 · 初版最小中文词表（可增，单测锁定）
TURN_COST_LEX = (
    "失败", "没能", "未能", "两难", "要么", "不可逆", "空过", "代价",
    "暴露", "泄露", "被迫", "来不及", "来不及了", "收不回", "退则",
    "死", "伤", "血", "裂", "断", "锁死", "拒绝", "否认", "崩溃",
)
# 关系张力（低压）
REL_TENSION_LEX = (
    "误会", "疏远", "试探", "隐瞒", "愧疚", "对峙", "和解未成", "信任",
)
# 弱模型/夹具常见空壳 cost（不计为满足代价义务）
_COST_PLACEHOLDERS = frozenset({
    "无", "有", "n/a", "N/A", "na", "NA", "-", "—", "–",
    "无代价", "暂无", "待补", "TODO", "todo", "none", "None",
})

# 阈值
OVERLAP_FAKE_THRESHOLD = 0.72  # ≥ 且 全部缺 goal → drama_weak / 高压 ok=False
MIN_FIELD = 4  # goal/conflict/turn 最短字；meaningful cost 亦用
BEAT_TEXT_DRAMA_FLOOR = 80  # 场面纸够长即视为有戏，空 GCD 短字段不得再灌真空
MIN_HOOK = 2  # 章末钩子最短字（检测；severity 始终 advisory · KD-NQ-16）
DEFAULT_HARD_PRESSURE = 4  # 用户裁决 Open Q1；env SCRIBE3_DRAMA_HARD_PRESSURE 可覆盖


def _field(s: Any) -> str:
    return str(s or "").strip()


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def resolve_hard_pressure(explicit: int | None = None) -> int:
    """HARD_PRESSURE：显式参数 > env ``SCRIBE3_DRAMA_HARD_PRESSURE`` > 默认 4。"""
    if explicit is not None:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    # 优先轻量 env，避免纯测强依赖 settings/DB
    if (get_flag("SCRIBE3_DRAMA_HARD_PRESSURE") or "").strip():
        return _env_int("SCRIBE3_DRAMA_HARD_PRESSURE", DEFAULT_HARD_PRESSURE)
    try:
        from scribe3.novel_quality_flags import drama_hard_pressure
        return int(drama_hard_pressure())
    except Exception:
        return DEFAULT_HARD_PRESSURE


def resolve_compat_v1(explicit: bool | None = None) -> bool:
    """DRAMA_GATE_COMPAT：显式 > env > 代码默认 True（v1 弱通过）。"""
    if explicit is not None:
        return bool(explicit)
    if (get_flag("SCRIBE3_DRAMA_GATE_COMPAT") or "").strip():
        return _env_bool("SCRIBE3_DRAMA_GATE_COMPAT", True)
    try:
        from scribe3.novel_quality_flags import drama_gate_compat_enabled
        return bool(drama_gate_compat_enabled())
    except Exception:
        return True


def _cjk_bigrams(s: str) -> set[str]:
    s = "".join(c for c in (s or "") if "\u4e00" <= c <= "\u9fff")
    if len(s) >= 2:
        return {s[i : i + 2] for i in range(len(s) - 1)}
    return {s} if s else set()


def jaccard_cjk(a: str, b: str) -> float:
    """CJK bigram Jaccard；空集任一侧 → 0.0。"""
    sa, sb = _cjk_bigrams(a), _cjk_bigrams(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def synopsis_overlap_ratio(beat_texts: list[str], synopsis: str) -> float:
    """假节拍：全拍 text 与大纲的 Jaccard(CJK bigram)。"""
    bt = _cjk_bigrams("".join(beat_texts or []))
    sy = _cjk_bigrams(synopsis or "")
    if not bt or not sy:
        return 0.0
    return len(bt & sy) / len(bt | sy)


def _lex_hit(text: str, lexicon: tuple[str, ...] | list[str]) -> bool:
    t = text or ""
    if not t:
        return False
    return any(tok in t for tok in lexicon)


def _kind_of(beat: dict) -> str:
    raw = str(beat.get("kind") or "scene").strip()
    k = raw.lower()
    if raw in ("bridge", "桥", "过渡", "衔接") or k == "bridge":
        return "bridge"
    return "scene"


def _normalize_beats(beats: Any) -> list[dict]:
    if beats is None:
        return []
    if isinstance(beats, str):
        try:
            beats = json.loads(beats)
        except (ValueError, TypeError):
            return []
    if not isinstance(beats, list):
        return []
    out: list[dict] = []
    for i, b in enumerate(beats):
        if isinstance(b, str):
            out.append({"id": f"b{i+1}", "kind": "scene", "text": b})
        elif isinstance(b, dict):
            d = dict(b)
            d.setdefault("id", f"b{i+1}")
            out.append(d)
    return out


def _is_v1_text_only(beats: list[dict]) -> bool:
    """纯 v1：goal/conflict/turn/cost 全空（``list[{text}]``）。"""
    if not beats:
        return True
    for b in beats:
        for k in ("goal", "conflict", "turn", "cost"):
            if _field(b.get(k)):
                return False
    return True


def _all_missing_goal(beats: list[dict]) -> bool:
    """设计假节拍条件：全部缺 goal（允许空壳 cost/turn 仍判 fake）。"""
    if not beats:
        return True
    return all(not _field(b.get("goal")) for b in beats)


def _is_cost_placeholder(cost: str) -> bool:
    c = (cost or "").strip()
    if not c:
        return False
    if c in _COST_PLACEHOLDERS:
        return True
    # 过短且未命中代价词表 → 视为空壳
    if len(c) < MIN_FIELD and not _lex_hit(c, TURN_COST_LEX):
        return True
    return False


def _cost_meaningful(cost: str) -> bool:
    """非 bridge 代价义务：len≥MIN_FIELD 或命中 TURN_COST_LEX；拒 placeholder。"""
    c = (cost or "").strip()
    if not c or c in _COST_PLACEHOLDERS:
        return False
    return len(c) >= MIN_FIELD or _lex_hit(c, TURN_COST_LEX)


def _cost_obligation(norm: list[dict]) -> dict[str, bool]:
    """与 validate / drama_score 共用的代价义务判定。

    - ``has_cost``：非 bridge 拍上有 meaningful cost
    - ``turn_cost_lex``：任一拍 turn 或 cost 命中词表
    - ``cost_or_lex``：满足代价义务（has_cost **或** turn_cost_lex）
    - ``cost_placeholder``：出现过非空但非 meaningful 的 cost（观测用）
    """
    has_cost = False
    turn_cost_lex = False
    cost_placeholder = False
    for b in norm:
        kind = _kind_of(b)
        cost = _field(b.get("cost"))
        turn = _field(b.get("turn"))
        if _lex_hit(turn, TURN_COST_LEX) or _lex_hit(cost, TURN_COST_LEX):
            turn_cost_lex = True
        if kind == "bridge":
            continue
        if not cost:
            continue
        if _cost_meaningful(cost):
            has_cost = True
        else:
            cost_placeholder = True
    return {
        "has_cost": has_cost,
        "turn_cost_lex": turn_cost_lex,
        "cost_or_lex": has_cost or turn_cost_lex,
        "cost_placeholder": cost_placeholder,
    }


def _scene_gcd_ok(b: dict) -> bool:
    return (
        len(_field(b.get("goal"))) >= MIN_FIELD
        and len(_field(b.get("conflict"))) >= MIN_FIELD
        and len(_field(b.get("turn"))) >= MIN_FIELD
    )


def _goal_conflict_uniqueness_warnings(scenes: list[dict]) -> list[str]:
    """goal/conflict 两两 Jaccard ≥ 0.72 → warning（设计启发式 · 软）。"""
    warnings: list[str] = []
    goals = [(_field(s.get("goal")), s.get("id") or "?") for s in scenes if _field(s.get("goal"))]
    conflicts = [
        (_field(s.get("conflict")), s.get("id") or "?")
        for s in scenes
        if _field(s.get("conflict"))
    ]
    for i in range(len(goals)):
        for j in range(i + 1, len(goals)):
            g1, id1 = goals[i]
            g2, id2 = goals[j]
            if jaccard_cjk(g1, g2) >= OVERLAP_FAKE_THRESHOLD:
                warnings.append(
                    f"goal_overlap:{id1}/{id2}>={OVERLAP_FAKE_THRESHOLD}"
                )
    for i in range(len(conflicts)):
        for j in range(i + 1, len(conflicts)):
            c1, id1 = conflicts[i]
            c2, id2 = conflicts[j]
            if jaccard_cjk(c1, c2) >= OVERLAP_FAKE_THRESHOLD:
                warnings.append(
                    f"conflict_overlap:{id1}/{id2}>={OVERLAP_FAKE_THRESHOLD}"
                )
    return warnings


def _empty_metrics(
    *,
    overlap: float,
    is_high: bool,
    hp: int,
    cp: int,
    role_s: str,
) -> dict:
    return {
        "overlap": overlap,
        "scene_count": 0,
        "bridge_count": 0,
        "is_high": is_high,
        "v1_text_only": True,
        "all_missing_goal": True,
        "hard_pressure": hp,
        "chapter_pressure": cp,
        "role": role_s,
        "has_cost": False,
        "has_hook": False,
        "turn_cost_lex": False,
        "cost_or_lex": False,
        "cost_placeholder": False,
        "gcd_scene_count": 0,
    }


def validate_drama_beats(
    beats: list[dict] | None,
    *,
    chapter_pressure: int = 4,
    role: str = "推进",
    synopsis: str = "",
    chapter_hook: str = "",
    hard_pressure: int | None = None,
    compat_v1: bool | None = None,
    compat: bool | None = None,
) -> dict:
    """戏剧节拍门检。

    参数
    ----
    beats:
        ``list[dict]``，v2 字段 goal/conflict/turn/cost/hook/text/kind；v1 仅 text。
    chapter_pressure:
        章压力级 1–5。
    role:
        chapter_role；``高压``/``推进`` 走高压规则。
    synopsis:
        大纲全文；用于假节拍 Jaccard 重叠检测。
    chapter_hook:
        章末钩子（可与末拍 hook 二选一；**始终 advisory** · KD-NQ-16）。
    hard_pressure:
        高压门槛，默认 4 / env ``SCRIBE3_DRAMA_HARD_PRESSURE``。
    compat_v1 / compat:
        纯 v1 仅 text 时弱通过（``ok=True, drama_weak=True``）。默认 True（代码可达）。

    返回
    ----
    ``{ok, errors, warnings, drama_weak, metrics}``
    """
    hp = resolve_hard_pressure(hard_pressure)
    # compat 别名优先于 compat_v1 显式；皆空则 env/默认
    if compat is not None:
        use_compat = bool(compat)
    else:
        use_compat = resolve_compat_v1(compat_v1)

    try:
        cp = int(chapter_pressure)
    except (TypeError, ValueError):
        cp = 4
    role_s = str(role or "").strip()

    is_high = role_s in HIGH_ROLES or cp >= hp
    is_low_role = role_s in LOW_ROLES

    norm = _normalize_beats(beats)
    errors: list[str] = []
    warnings: list[str] = []
    drama_weak = False

    texts = [_field(b.get("text")) for b in norm]
    overlap = synopsis_overlap_ratio(texts, synopsis) if synopsis else 0.0

    scenes = [b for b in norm if _kind_of(b) == "scene"]
    bridges = [b for b in norm if _kind_of(b) == "bridge"]
    scene_count = len(scenes)
    v1_only = _is_v1_text_only(norm)
    missing_goal = _all_missing_goal(norm)

    # ── 空列表 ──────────────────────────────────────────────────────────
    if not norm:
        errors.append("beats_empty")
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings,
            "drama_weak": True,
            "metrics": _empty_metrics(
                overlap=overlap, is_high=is_high, hp=hp, cp=cp, role_s=role_s
            ),
        }

    # ── GCD：≥1 scene 且 G/C/T 各 ≥ MIN_FIELD ───────────────────────────
    gcd_ok_scenes = [b for b in scenes if _scene_gcd_ok(b)]
    gcd_scene_count = len(gcd_ok_scenes)
    if scene_count == 0:
        msg = "no_scene_beat"
        if is_high:
            errors.append(msg)
        else:
            warnings.append(msg)
    elif gcd_scene_count < 1:
        msg = f"scene_gcd_incomplete:need>={MIN_FIELD}"
        if is_high and not (use_compat and v1_only):
            errors.append(msg)
        else:
            warnings.append(msg)
            if v1_only or missing_goal:
                drama_weak = True

    # ── cost / turn 词表（全章；bridge 免 cost；与 drama_score 共用）────
    obl = _cost_obligation(norm)
    has_cost = obl["has_cost"]
    turn_cost_lex = obl["turn_cost_lex"]
    cost_or_lex = obl["cost_or_lex"]
    cost_placeholder = obl["cost_placeholder"]
    if cost_placeholder:
        warnings.append("cost_placeholder")
    if not cost_or_lex and scene_count > 0:
        msg = "cost_or_turn_lex_missing"
        if is_high and not (use_compat and v1_only):
            errors.append(msg)
        else:
            warnings.append(msg)

    # ── 章末钩子：始终 advisory（KD-NQ-16）──────────────────────────────
    last_hook = _field(norm[-1].get("hook")) if norm else ""
    ch_hook = _field(chapter_hook)
    hook_text = ch_hook if len(ch_hook) >= MIN_HOOK else last_hook
    has_hook = len(hook_text) >= MIN_HOOK
    if not has_hook:
        warnings.append("chapter_hook_missing")  # 永不进 errors

    # ── 假节拍：全部缺 goal 且与大纲 overlap ≥ 0.72（设计注释对齐）────
    # 即使塞了空壳 cost/turn 仍可触发（不只认纯 v1_only）
    if missing_goal and synopsis and overlap >= OVERLAP_FAKE_THRESHOLD:
        msg = f"synopsis_fake_overlap>={OVERLAP_FAKE_THRESHOLD}"
        if is_high and not use_compat:
            errors.append(msg)
        else:
            warnings.append(msg)
            drama_weak = True
    elif v1_only:
        # 纯 v1 无高重叠大纲可测：标弱
        drama_weak = True
        warnings.append("v1_text_only")

    # ── 低压 / LOW_ROLES：关系张力至少一拍 ──────────────────────────────
    if is_low_role or (not is_high and role_s):
        tension_ok = False
        for b in scenes or norm:
            g, c = _field(b.get("goal")), _field(b.get("conflict"))
            if _lex_hit(g, REL_TENSION_LEX) or _lex_hit(c, REL_TENSION_LEX):
                tension_ok = True
                break
            if len(c) >= MIN_FIELD:
                tension_ok = True
                break
        # 仅当明确 LOW_ROLES 时硬；其它低压章软
        if not tension_ok and is_low_role:
            msg = "rel_tension_missing"
            if not (use_compat and v1_only):
                errors.append(msg)
            else:
                warnings.append(msg)

    # ── goal/conflict 互相似（软）───────────────────────────────────────
    if gcd_scene_count >= 2:
        warnings.extend(_goal_conflict_uniqueness_warnings(scenes))

    # ── DRAMA_GATE_COMPAT：纯 v1 仅 text → 弱通过 ───────────────────────
    if use_compat and v1_only:
        drama_weak = True
        # 清掉会阻断兼容的硬错误，改记 warning（不 park）
        kept_errors: list[str] = []
        for e in errors:
            if e == "beats_empty":
                kept_errors.append(e)
            else:
                weak = f"compat_weak:{e}"
                if weak not in warnings and e not in warnings:
                    warnings.append(weak)
        errors = kept_errors
        if "v1_compat_weak_pass" not in warnings:
            warnings.append("v1_compat_weak_pass")

    ok = len(errors) == 0

    metrics = {
        "overlap": round(overlap, 4),
        "scene_count": scene_count,
        "bridge_count": len(bridges),
        "is_high": is_high,
        "v1_text_only": v1_only,
        "all_missing_goal": missing_goal,
        "hard_pressure": hp,
        "chapter_pressure": cp,
        "role": role_s,
        "has_cost": has_cost,
        "has_hook": has_hook,
        "turn_cost_lex": turn_cost_lex,
        "cost_or_lex": cost_or_lex,
        "cost_placeholder": cost_placeholder,
        "gcd_scene_count": gcd_scene_count,
        "compat_v1": use_compat,
        "drama_weak": drama_weak,
    }
    return {
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "drama_weak": drama_weak,
        "metrics": metrics,
    }


def drama_score(beats: list[dict] | None, *, chapter_hook: str = "") -> dict:
    """轻量戏剧完备分（供 beats_meta.drama_score；与 validate 代价义务对齐）。

    ``complete`` 要求：≥1 完整 GCD scene、代价义务满足（meaningful cost **或**
    turn/cost 命中 ``TURN_COST_LEX``）、以及章末钩子（chapter_hook 或末拍 hook）。
    """
    norm = _normalize_beats(beats)
    scenes = [b for b in norm if _kind_of(b) == "scene"]
    obl = _cost_obligation(norm)
    last_hook = _field(norm[-1].get("hook")) if norm else ""
    has_hook = len(_field(chapter_hook)) >= MIN_HOOK or len(last_hook) >= MIN_HOOK
    gcd_n = sum(1 for b in scenes if _scene_gcd_ok(b))
    complete = gcd_n >= 1 and obl["cost_or_lex"] and has_hook
    return {
        "complete": complete,
        "scene_count": len(scenes),
        "has_cost": obl["has_cost"],
        "turn_cost_lex": obl["turn_cost_lex"],
        "cost_or_lex": obl["cost_or_lex"],
        "has_hook": has_hook,
        "gcd_scene_count": gcd_n,
    }


def extract_drama_gaps(
    beats: list[dict] | None,
    *,
    validation: dict | None = None,
) -> dict:
    """结构化戏剧缺口清单（goal/conflict/turn/cost）· PR-3 API-first。

    - 非 bridge 拍：goal/conflict/turn 低于 ``MIN_FIELD`` → 缺字段
    - cost：拍级无 meaningful cost 记入 ``missing_cost``；若全章代价义务已满足
      （meaningful cost 或 turn/cost 词表）则清空拍级 cost 缺口（避免误杀）
    - 返回 ``per_beat`` / 字段 id 列表 / 可读 ``lines`` / 透传 ``errors``
    """
    norm = _normalize_beats(beats)
    missing_goal: list[str] = []
    missing_conflict: list[str] = []
    missing_turn: list[str] = []
    missing_cost: list[str] = []
    per_beat: list[dict] = []

    for b in norm:
        if _kind_of(b) == "bridge":
            continue
        bid = str(b.get("id") or "?")
        miss: list[str] = []
        if len(_field(b.get("goal"))) < MIN_FIELD:
            miss.append("goal")
            missing_goal.append(bid)
        if len(_field(b.get("conflict"))) < MIN_FIELD:
            miss.append("conflict")
            missing_conflict.append(bid)
        if len(_field(b.get("turn"))) < MIN_FIELD:
            miss.append("turn")
            missing_turn.append(bid)
        if not _cost_meaningful(_field(b.get("cost"))):
            miss.append("cost")
            missing_cost.append(bid)
        if miss:
            per_beat.append({"id": bid, "missing": list(miss)})

    obl = _cost_obligation(norm)
    if obl["cost_or_lex"]:
        # 全章代价义务已满足：去掉拍级 cost 缺口标记
        missing_cost = []
        for pb in per_beat:
            if "cost" in pb["missing"]:
                pb["missing"] = [m for m in pb["missing"] if m != "cost"]
        per_beat = [pb for pb in per_beat if pb["missing"]]
    else:
        # 全章仍无代价/词表：确保至少有一处 chapter 级 cost 提示
        if not missing_cost:
            missing_cost = ["*"]

    lines: list[str] = []
    for pb in per_beat:
        lines.append(f"{pb['id']}缺{'/'.join(pb['missing'])}")
    if not obl["cost_or_lex"] and not any("cost" in (pb.get("missing") or []) for pb in per_beat):
        lines.append("全章缺cost或turn代价词")

    errors = list((validation or {}).get("errors") or [])
    if not lines and errors:
        lines = [str(e) for e in errors[:8]]

    return {
        "missing_goal": missing_goal,
        "missing_conflict": missing_conflict,
        "missing_turn": missing_turn,
        "missing_cost": missing_cost,
        "per_beat": per_beat,
        "lines": lines,
        "errors": errors,
        "cost_or_lex": bool(obl["cost_or_lex"]),
    }


def format_drama_gate_park_reason(
    gaps: dict | None,
    *,
    advisory: bool = True,
) -> str:
    """拼 ``pilot_park`` 文案：``drama_incomplete`` + 可读缺口 + 紧凑 JSON。

    advisory=True 时附「可补字段继续」（PR-3 默认 advisory 模式）。
    """
    g = gaps or {}
    head = "drama_incomplete:高压章戏剧门未过"
    if advisory:
        head += "（可补字段继续）"
    lines = [str(x) for x in (g.get("lines") or []) if str(x).strip()]
    errs = [str(x) for x in (g.get("errors") or []) if str(x).strip()]
    body = "；".join(lines[:8]) if lines else ("；".join(errs[:6]) if errs else "GCD字段不完整")
    compact = {
        "missing_goal": list(g.get("missing_goal") or []),
        "missing_conflict": list(g.get("missing_conflict") or []),
        "missing_turn": list(g.get("missing_turn") or []),
        "missing_cost": list(g.get("missing_cost") or []),
    }
    try:
        j = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        j = "{}"
    # 指引：节拍已落库，人补 PATCH / s3_patch_chapter_plan 后重推
    return (
        f"{head}。缺口：{body}。"
        f"清单:{j}。"
        f"节拍已保留，可用 PATCH beats 或 s3_patch_chapter_plan 补 goal/conflict/turn/cost 后继续。"
    )


def should_drama_gate_park(
    validation: dict | None,
    *,
    gate_enabled: bool,
) -> bool:
    """是否因戏剧门 park：旗开 + ok=False + 高压章（metrics.is_high）。"""
    if not gate_enabled:
        return False
    dv = validation or {}
    if dv.get("ok"):
        return False
    metrics = dv.get("metrics") or {}
    return bool(metrics.get("is_high"))


# ── PR-4：草稿注入戏剧合同块（≤400 字）────────────────────────────────

# 硬顶：与 PDC 注入同口径（Python len 字符）；冲突时裁字段不裁标题/限知免责
MAX_DRAMA_BLOCK = 400

# 戏剧真空警告（无 GCD 时注入；与 NQ DRAMA_GATE park 分工见设计 §7.1）
DRAMA_VACUUM_WARN_TEXT = (
    "\n\n【戏剧真空】本章缺目标与阻力；禁无外力地点句与章末假升华。"
    "过渡章请先标明过场并压短。\n"
)


def drama_vacuum_warn_enabled() -> bool:
    import os
    raw = (get_flag("SCRIBE3_DRAMA_VACUUM_WARN") or "1").strip().lower()
    return raw not in ("0", "false", "off", "no")


def should_inject_drama_vacuum(
    beats: list | None, *, chapter_hook: str = "",
) -> bool:
    """写路径真空：无实质 goal、无实质 conflict、且场面纸也不够长。

    冰山节拍常把戏写在 text（进场/事件/翻转），GCD 短字段空。
    只看 goal/conflict 会在已有场面时仍灌「缺目标」，和 drama_contract 对打。
    单钩/单字代价不得熄火。空列表仍算真空（给 draft/final 当「别逛」）。
    """
    has_goal = False
    has_conflict = False
    has_scene = False
    for b in beats or []:
        if isinstance(b, dict):
            if len(_field(b.get("goal"))) >= MIN_FIELD:
                has_goal = True
            if len(_field(b.get("conflict"))) >= MIN_FIELD:
                has_conflict = True
            text = _field(b.get("text") or b.get("prose"))
        else:
            text = _field(b)
        if len(text) >= BEAT_TEXT_DRAMA_FLOOR:
            has_scene = True
        if has_goal or has_conflict or has_scene:
            break
    _ = chapter_hook  # 钩子不算戏核
    return not has_goal and not has_conflict and not has_scene


def format_drama_vacuum_warn(
    beats: list | None = None, *, chapter_hook: str = "",
) -> str:
    """无 goal∧conflict 时的注入段；flag 关则空串。"""
    if not drama_vacuum_warn_enabled():
        return ""
    if beats is not None and not should_inject_drama_vacuum(
        beats, chapter_hook=chapter_hook,
    ):
        return ""
    return DRAMA_VACUUM_WARN_TEXT


# 固定 MRU 三行（短；动机-反应-行动微观节奏）
_MRU_LINES = (
    "1. 外在刺激→身体反应→言语/决定，分段写（动机-反应-行动）。",
    "2. 每场至少一次外在阻力动作（拦/拒/误/迟），禁只逛地点。",
    "3. 保留信息差；章末可未揭。",
)
_MRU_BAN = "禁：无目标地点句；比喻凑字；章末「他明白了/正是因为」点题。"
_LIMITED_KNOWLEDGE = (
    "（限知）以上为作者视角合同；只呈现焦点者可感知部分，帧外私密不得道破。"
)


def beats_have_drama_gcd(
    beats: list | None,
    *,
    chapter_hook: str = "",
) -> bool:
    """节拍是否含任何 GCD/钩子字段（供 length_steer / 勿仅因字数清稿）。"""
    if _field(chapter_hook):
        return True
    for b in beats or []:
        if not isinstance(b, dict):
            continue
        if any(_field(b.get(k)) for k in ("goal", "conflict", "turn", "cost", "hook")):
            return True
    return False


def _clip_field(s: Any, n: int) -> str:
    t = _field(s)
    return t if len(t) <= n else t[:n]


def _sanitize_drama_text(text: str) -> str:
    """压缩槽提取留下的双冒号残片。"""
    return (text or "").replace("：：", "：").replace("::", "：")


_TEXT_SLOT_RE = re.compile(
    r"\*\*(?P<h>进场|事件|翻转|出场|水下)\s*[：:]?\*\*\s*(?P<body>.+?)(?=\n\s*\*\*(?:进场|事件|翻转|出场|水下)|$)",
    re.DOTALL,
)


def _format_text_slots(
    beats: list | None, *, max_chars: int, focalizer: str = "",
) -> str:
    """冰山拍只有 text 槽时：事件/翻转优先，禁止只剩「进场：」半句。"""
    parsed: list[dict[str, str]] = []
    for b in beats or []:
        raw = _field(b.get("text") if isinstance(b, dict) else b)
        slots = {}
        for m in _TEXT_SLOT_RE.finditer(raw):
            body = _field(m.group("body")).split("\n", 1)[0]
            body = body.lstrip("：:").strip()
            if body:
                slots[m.group("h")] = body
        if slots:
            parsed.append(slots)
    if not parsed:
        return ""

    def _lines(field_cap: int, *, drop_enter: bool) -> list[str]:
        out: list[str] = []
        order = ("事件", "翻转", "水下", "出场") if drop_enter else ("事件", "翻转", "水下", "出场", "进场")
        for i, slots in enumerate(parsed, 1):
            chunks = [_clip_field(slots[k], field_cap) for k in order if slots.get(k)]
            if chunks:
                out.append(f"拍{i}：" + "；".join(chunks))
        return out

    def _assemble(lines: list[str], *, with_limited: bool) -> str:
        parts = ["## 本章必须发生"]
        parts.extend(f"- {ln}" for ln in lines)
        if with_limited and _field(focalizer):
            parts.append(_LIMITED_KNOWLEDGE)
        return "\n".join(parts)

    for cap, drop_enter, keep_n, limited in (
        (36, False, 99, True),
        (28, True, 99, True),
        (22, True, 3, True),
        (16, True, 2, False),
        (16, True, 1, False),
    ):
        lines = _lines(cap, drop_enter=drop_enter)[:keep_n]
        if not lines:
            continue
        text = _assemble(lines, with_limited=limited)
        if len(text) <= max_chars:
            return _sanitize_drama_text(text)
    text = _assemble(_lines(14, drop_enter=True)[:1], with_limited=False)
    out = text[:max_chars] if len(text) > max_chars else text
    return _sanitize_drama_text(out)


def _beat_walk_line(i: int, b: dict, field_cap: int) -> str:
    """一句无标签走法：谁拦/当场变了什么/留下什么痕。"""
    g = _clip_field(b.get("goal"), field_cap)
    c = _clip_field(b.get("conflict"), field_cap)
    t = _clip_field(b.get("turn"), field_cap)
    cost = _clip_field(b.get("cost"), field_cap)
    if not (g or c or t or cost):
        return ""
    chunks: list[str] = []
    if c:
        chunks.append(c)
    elif g:
        chunks.append(g)
    if t:
        chunks.append(t)
    if cost:
        chunks.append(cost)
    return f"拍{i}：" + "；".join(chunks)


def format_drama_block(
    beats: list | None,
    *,
    chapter_hook: str = "",
    focalizer: str = "",
    max_chars: int = MAX_DRAMA_BLOCK,
) -> str:
    """压缩「本章拍级走法」，≤``max_chars``（默认 400）。

    - 无 GCD/钩子 → 空串。
    - 超预算先不注入 MRU/禁令套话，再缩字段、再减拍；限知免责尽量留。
    - 自带前导 ``\\n\\n``。
    """
    if not beats_have_drama_gcd(beats, chapter_hook=chapter_hook):
        # 无 GCD 不回退千字拍文 / 进场
        return ""

    norm = _normalize_beats(beats) if beats else []
    hook = _field(chapter_hook)
    if not hook and norm:
        hook = _field(norm[-1].get("hook"))
    hook = _clip_field(hook, 36)
    limited = _LIMITED_KNOWLEDGE if _field(focalizer) else ""
    header = "## 本章拍级走法"

    def _lines(field_cap: int) -> list[str]:
        out: list[str] = []
        for i, b in enumerate(norm, 1):
            ln = _beat_walk_line(i, b, field_cap)
            if ln:
                out.append(ln)
        return out

    def _assemble(lines: list[str], *, with_hook: bool, with_limited: bool) -> str:
        parts = [header]
        parts.extend(f"- {ln}" for ln in lines)
        if with_hook and hook:
            parts.append(f"- 章末还悬着：{hook}")
        if with_limited and limited:
            parts.append(limited)
        return "\n".join(parts)

    # 先保冲突/代价走法；超帽再缩字段、减后拍，最后才动钩与限知
    for cap in (36, 22, 14):
        lines = _lines(cap)
        text = _assemble(lines, with_hook=True, with_limited=True)
        if len(text) <= max_chars:
            return "\n\n" + text
        for n in range(len(lines), 0, -1):
            text = _assemble(lines[:n], with_hook=True, with_limited=True)
            if len(text) <= max_chars:
                return "\n\n" + text
        text = _assemble(lines[:1], with_hook=False, with_limited=True)
        if len(text) <= max_chars:
            return "\n\n" + text

    emergency = _assemble(_lines(12)[:1], with_hook=False, with_limited=bool(limited))
    if len(emergency) <= max_chars:
        return "\n\n" + emergency
    if limited:
        room = max(0, max_chars - len(header) - 1)
        return "\n\n" + (header + "\n" + limited[:room])[:max_chars]
    return "\n\n" + header[:max_chars]
