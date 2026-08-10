# scribe3/drama_beats.py
"""戏剧节拍校验 · 纯函数（PR-1）。

真源：``docs/plans/2026-08-10-novel-quality-first-pipeline-optimization.md``
（Issue 5 · ``validate_drama_beats`` / beats.v2）

本模块 **无** LLM / 网络 / Surreal；仅对 ``list[dict]`` 节拍做确定性门检。
写前门接线与 park 属后续 PR（3）；此处只产出 ``{ok, errors, warnings, drama_weak, metrics}``。
"""
from __future__ import annotations

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

# 阈值
OVERLAP_FAKE_THRESHOLD = 0.72  # ≥ 且 全部缺 goal → drama_weak / 高压 ok=False
MIN_FIELD = 4  # goal/conflict/turn 最短字
MIN_HOOK = 2  # 章末钩子最短字（检测；severity 始终 advisory · KD-NQ-16）
DEFAULT_HARD_PRESSURE = 4  # 用户裁决 Open Q1；env SCRIBE3_DRAMA_HARD_PRESSURE 可覆盖

_SCHEMA_V2_KEYS = frozenset({"goal", "conflict", "turn", "cost", "hook"})
_WS_RE = re.compile(r"\s+")


def _strip(s: Any) -> str:
    return _WS_RE.sub("", str(s or "").strip()) if s is not None else ""


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
    if (os.environ.get("SCRIBE3_DRAMA_HARD_PRESSURE") or "").strip():
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
    if (os.environ.get("SCRIBE3_DRAMA_GATE_COMPAT") or "").strip():
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
    k = str(beat.get("kind") or "scene").strip().lower()
    # 中文 kind 兼容
    raw = str(beat.get("kind") or "scene").strip()
    if raw in ("bridge", "桥", "过渡", "衔接"):
        return "bridge"
    if k == "bridge":
        return "bridge"
    return "scene"


def _normalize_beats(beats: Any) -> list[dict]:
    if beats is None:
        return []
    if isinstance(beats, str):
        try:
            import json
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
        else:
            continue
    return out


def _is_v1_text_only(beats: list[dict]) -> bool:
    """全部缺非空 goal（v1 ``list[{text}]`` 形态）。"""
    if not beats:
        return True
    for b in beats:
        if _field(b.get("goal")):
            return False
        # 任一 v2 结构字段非空则不算纯 v1
        for k in ("conflict", "turn", "cost"):
            if _field(b.get(k)):
                return False
    return True


def _has_v2_shape(beats: list[dict]) -> bool:
    for b in beats:
        if any(_field(b.get(k)) for k in _SCHEMA_V2_KEYS if k != "hook"):
            return True
    return False


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
        (_field(s.get("conflict")), s.get("id") or "?") for s in scenes if _field(s.get("conflict"))
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
        v1 仅 text 时弱通过（``ok=True, drama_weak=True``）。默认 True（代码可达）。

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
    v2_shape = _has_v2_shape(norm)

    # ── 空列表 ──────────────────────────────────────────────────────────
    if not norm:
        errors.append("beats_empty")
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings,
            "drama_weak": True,
            "metrics": {
                "overlap": overlap,
                "scene_count": 0,
                "bridge_count": 0,
                "is_high": is_high,
                "v1_text_only": True,
                "hard_pressure": hp,
                "chapter_pressure": cp,
                "role": role_s,
                "has_cost": False,
                "has_hook": False,
                "turn_cost_lex": False,
                "gcd_scene_count": 0,
            },
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
            if v1_only:
                drama_weak = True

    # ── cost / turn 词表（全章；bridge 免 cost 义务）────────────────────
    has_cost = False
    turn_cost_lex = False
    for b in norm:
        kind = _kind_of(b)
        cost = _field(b.get("cost"))
        turn = _field(b.get("turn"))
        if kind != "bridge" and cost:
            has_cost = True
        if _lex_hit(turn, TURN_COST_LEX) or _lex_hit(cost, TURN_COST_LEX):
            turn_cost_lex = True
            if cost:
                has_cost = True
    cost_or_lex = has_cost or turn_cost_lex
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

    # ── 假节拍：仅 text 且与大纲 overlap ≥ 0.72 ─────────────────────────
    if v1_only and synopsis and overlap >= OVERLAP_FAKE_THRESHOLD:
        msg = f"synopsis_fake_overlap>={OVERLAP_FAKE_THRESHOLD}"
        if is_high and not use_compat:
            errors.append(msg)
        else:
            warnings.append(msg)
            drama_weak = True
    elif v1_only and not v2_shape:
        # 纯 v1 无大纲可测：标弱
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

    # ── DRAMA_GATE_COMPAT：v1 仅 text → 弱通过 ──────────────────────────
    if use_compat and v1_only:
        drama_weak = True
        # 清掉会阻断兼容的硬错误，改记 warning（不 park）
        kept_errors: list[str] = []
        for e in errors:
            if e in (
                "beats_empty",
            ):
                kept_errors.append(e)
            else:
                if e not in warnings:
                    warnings.append(f"compat_weak:{e}")
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
        "hard_pressure": hp,
        "chapter_pressure": cp,
        "role": role_s,
        "has_cost": has_cost,
        "has_hook": has_hook,
        "turn_cost_lex": turn_cost_lex,
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
    """轻量戏剧完备分（供 beats_meta.drama_score；不改变 validate 结果）。"""
    norm = _normalize_beats(beats)
    scenes = [b for b in norm if _kind_of(b) == "scene"]
    has_cost = any(_field(b.get("cost")) for b in norm if _kind_of(b) != "bridge")
    last_hook = _field(norm[-1].get("hook")) if norm else ""
    has_hook = len(_field(chapter_hook)) >= MIN_HOOK or len(last_hook) >= MIN_HOOK
    gcd_n = sum(1 for b in scenes if _scene_gcd_ok(b))
    complete = gcd_n >= 1 and has_cost and has_hook
    return {
        "complete": complete,
        "scene_count": len(scenes),
        "has_cost": has_cost,
        "has_hook": has_hook,
        "gcd_scene_count": gcd_n,
    }
