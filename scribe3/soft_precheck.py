"""大纲/节拍软预检（P2 · O-12 · 纯 advisory）。

默认不 hard-park；返回 findings 列表供 UI/agent 展示。
``SCRIBE3_SOFT_PRECHECK=0``（默认）时仍可调用，行为相同（纯函数无副作用）。
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import os
from typing import Any


def soft_precheck_enabled() -> bool:
    """观测旗；关时调用方可不挂载，函数本身始终可跑。"""
    raw = (get_flag("SCRIBE3_SOFT_PRECHECK") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _beats_list(payload: Any) -> list:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("beats"), list):
            return payload["beats"]
        # plan 对象
        plan = payload.get("plan")
        if isinstance(plan, dict) and isinstance(plan.get("beats"), list):
            return plan["beats"]
        if isinstance(payload.get("outline"), str):
            return []
    return []


def soft_precheck_plan(payload: Any) -> dict[str, Any]:
    """对 outline/beats/plan 做 advisory 预检。

    永不默认 hard_park=True；仅列出空洞（空 conflict / 缺 GCD 等）。
    """
    findings: list[dict[str, Any]] = []
    beats = _beats_list(payload)
    if not beats:
        findings.append({
            "code": "beats_empty",
            "severity": "advisory",
            "message": "节拍为空或缺失，建议补全冲突链后再开写",
        })
    for i, b in enumerate(beats):
        if isinstance(b, str):
            if not b.strip():
                findings.append({
                    "code": "beat_empty_text",
                    "severity": "advisory",
                    "index": i,
                    "message": f"节拍 {i + 1} 文本为空",
                })
            continue
        if not isinstance(b, dict):
            findings.append({
                "code": "beat_bad_type",
                "severity": "advisory",
                "index": i,
                "message": f"节拍 {i + 1} 结构异常",
            })
            continue
        conflict = str(b.get("conflict") or b.get("disaster") or "").strip()
        goal = str(b.get("goal") or "").strip()
        text = str(b.get("text") or "").strip()
        if not conflict and not goal:
            # 纯 text 节拍：检查是否像无冲突
            if not text:
                findings.append({
                    "code": "beat_empty",
                    "severity": "advisory",
                    "index": i,
                    "message": f"节拍 {i + 1} 无目标/冲突/正文",
                })
            elif len(text) < 8:
                findings.append({
                    "code": "beat_thin",
                    "severity": "advisory",
                    "index": i,
                    "message": f"节拍 {i + 1} 过短，可能缺冲突",
                })
            continue
        if not conflict:
            findings.append({
                "code": "empty_conflict",
                "severity": "advisory",
                "index": i,
                "message": f"节拍 {i + 1} 冲突/灾难为空（GCD 洞）",
            })
        if not goal:
            findings.append({
                "code": "empty_goal",
                "severity": "advisory",
                "index": i,
                "message": f"节拍 {i + 1} 目标为空",
            })

    outline = ""
    if isinstance(payload, dict):
        outline = str(payload.get("outline") or payload.get("synopsis") or "")
    if outline and len(outline.strip()) < 12:
        findings.append({
            "code": "outline_thin",
            "severity": "advisory",
            "message": "大纲/提要过短",
        })

    return {
        "findings": findings,
        "hard_park": False,  # 默认永不硬停
        "mode": "advisory",
        "beat_count": len(beats),
        "finding_count": len(findings),
        "flag_soft_precheck": soft_precheck_enabled(),
        "not_a_kpi": "tokens_saved",
    }
