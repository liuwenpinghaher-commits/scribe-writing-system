"""Scene–Sequel 六元组 · 诊断与严格模式门闩。"""
from __future__ import annotations

from typing import Any

SCENE_KEYS = ("goal", "conflict", "disaster", "reaction", "dilemma", "decision")
SOURCES = ("author", "inferred", "empty")


def empty_scene_grid() -> dict[str, Any]:
    return {k: "" for k in SCENE_KEYS} | {"source": "empty"}


def normalize_scene_grid(raw: dict | None) -> dict[str, Any]:
    raw = raw or {}
    out = empty_scene_grid()
    for k in SCENE_KEYS:
        v = raw.get(k)
        out[k] = (str(v).strip() if v is not None else "")[:200]
    src = str(raw.get("source") or "").strip().lower()
    if src not in SOURCES:
        # 有任意非空字段 → author;否则 empty
        src = "author" if any(out[k] for k in SCENE_KEYS) else "empty"
    out["source"] = src
    if not any(out[k] for k in SCENE_KEYS):
        out["source"] = "empty"
    return out


def diagnose_scene_grid(grid: dict | None, *, seq: int | None = None) -> list[dict[str, Any]]:
    """返回断链列表。空 grid 返回 empty_grid 提示(advisory,非硬伤除非严格模式)。"""
    g = normalize_scene_grid(grid)
    issues: list[dict[str, Any]] = []
    filled = {k: bool(g.get(k)) for k in SCENE_KEYS}

    if g.get("source") == "empty" or not any(filled.values()):
        issues.append({
            "code": "empty_grid",
            "seq": seq,
            "message": "本场 Scene–Sequel 六格为空:默认不拦定稿;严格戏格下须补全。",
            "detail": "empty",
        })
        return issues

    if not filled["goal"]:
        issues.append({
            "code": "missing_goal",
            "seq": seq,
            "message": "场景缺目标(Goal):人物进场要什么?",
            "detail": "goal",
        })
    if filled["goal"] and not filled["conflict"]:
        issues.append({
            "code": "missing_conflict",
            "seq": seq,
            "message": "有目标无冲突(Conflict):阻力在哪?",
            "detail": "conflict",
        })
    if filled["disaster"] and not filled["reaction"]:
        issues.append({
            "code": "disaster_without_reaction",
            "seq": seq,
            "message": "有灾难/代价无反应(Reaction):人物如何消化?",
            "detail": "reaction",
        })
    if filled["reaction"] and not filled["dilemma"] and not filled["decision"]:
        issues.append({
            "code": "reaction_without_decision",
            "seq": seq,
            "message": "有反应无两难/决定:下一场目标从何而来?",
            "detail": "decision",
        })
    if filled["decision"] and not filled["disaster"] and not filled["conflict"]:
        # soft
        issues.append({
            "code": "decision_without_pressure",
            "seq": seq,
            "message": "有决定却缺少冲突/代价痕迹:决定是否赚来的?",
            "detail": "pressure",
        })
    return issues


def evaluate_strict_scene_gate(
    grid: dict | None,
    *,
    strict: bool,
    prose: str = "",
    min_prose_chars: int = 80,
) -> dict[str, Any]:
    """严格戏格:实质正文 + 空 grid → 不允许定稿。

    默认 strict=False → 始终 allowed。
    与 finalize_gate 正交;由 save 路径显式调用。
    """
    body = "".join((prose or "").split())
    if not strict:
        return {
            "allowed": True,
            "code": "strict_off",
            "detail": "严格戏格关闭,空 grid 不拦",
            "issues": diagnose_scene_grid(grid),
        }
    if len(body) < min_prose_chars:
        return {
            "allowed": True,
            "code": "short_prose",
            "detail": f"prose<{min_prose_chars},不强制 grid",
            "issues": [],
        }
    g = normalize_scene_grid(grid)
    issues = diagnose_scene_grid(g)
    empty = g.get("source") == "empty" or not any(g.get(k) for k in SCENE_KEYS)
    if empty:
        return {
            "allowed": False,
            "code": "strict_scene_empty",
            "detail": "严格戏格:实质正文须填写 Scene–Sequel 六格(或关闭严格模式)",
            "issues": issues,
        }
    # 严格模式: disaster_without_reaction 也拦
    hard = [i for i in issues if i.get("code") in (
        "missing_goal", "missing_conflict", "disaster_without_reaction")]
    if hard:
        return {
            "allowed": False,
            "code": "strict_scene_break",
            "detail": "严格戏格:场景动能硬断链未清",
            "issues": hard,
        }
    return {
        "allowed": True,
        "code": "ok",
        "detail": "严格戏格通过",
        "issues": issues,
    }
