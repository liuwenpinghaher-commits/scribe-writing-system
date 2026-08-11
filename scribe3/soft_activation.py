"""软 lore 激活（P2 · O-3）。

旗 ``SCRIBE3_SOFT_ACTIVATION=1`` 时：material/reference/long-codex 类段
在激活键未命中时可降权或丢弃；must-link / drama / secret 红线类**永不**被挡。
默认关 = 注入行为与现网一致。
"""
from __future__ import annotations

import os
import re
from typing import Any

# 可软丢弃 / 降权（L2/L3 类）
SOFT_SEGMENT_NAMES: frozenset[str] = frozenset({
    "material_recall",
    "reference_craft",
    "codex",
    "volume_intro",
    "seed_words",
    "craft",
    "phase_role",
    "avoid",
    "author_prefs",
    "purpose",
    "outline",
})

# 红线 / 铁律：激活键缺失也不得省略
REDLINE_SEGMENT_NAMES: frozenset[str] = frozenset({
    "prefix",
    "event_drive",
    "drama_contract",
    "drama_vacuum",
    "envelope",
    "brief_must",
    "pressure_drive",
    "final_reminder",
    "scene_truth_proj",
    "deduction_final",
    "sincerity",
    "revelation_discipline",
    "secret_guard",
    "continue_snapshot",
})


def soft_activation_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_SOFT_ACTIVATION") or "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _norm_keys(keys: list[str] | None) -> list[str]:
    out: list[str] = []
    for k in keys or []:
        s = re.sub(r"\s+", "", str(k or "").lower())
        if len(s) >= 2:
            out.append(s)
    return out


def segment_matches_activation(text: str, keys: list[str]) -> bool:
    """正文是否命中任一激活键（空白归一后子串）。"""
    if not keys:
        # 无键 → 不强制丢弃（避免空 query 清空全部 soft 段）
        return True
    body = re.sub(r"\s+", "", (text or "").lower())
    if not body:
        return False
    return any(k in body for k in keys)


def is_redline_segment(name: str) -> bool:
    n = str(name or "")
    if n in REDLINE_SEGMENT_NAMES:
        return True
    # 名称提示
    if any(x in n for x in ("drama", "must", "secret", "reminder", "redline", "guard")):
        return True
    return False


def is_soft_segment(name: str) -> bool:
    n = str(name or "")
    if n in SOFT_SEGMENT_NAMES:
        return True
    if n in REDLINE_SEGMENT_NAMES:
        return False
    return n in ("codex", "material_recall", "reference_craft")


def apply_soft_activation(
    pieces: list[dict[str, Any]],
    *,
    activation_keys: list[str] | None = None,
    force: bool | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """对段列表做软激活。

    force=None 读环境旗；True/False 覆盖。
    返回 (kept_or_demoted_pieces, report)。
    红线段原样保留；soft 未命中 → 丢弃（text 清空不入 join 亦可，此处直接 omit）。
    """
    enabled = soft_activation_enabled() if force is None else bool(force)
    keys = _norm_keys(activation_keys)
    report: dict[str, Any] = {
        "enabled": enabled,
        "activation_keys": list(keys),
        "dropped": [],
        "kept_soft": [],
        "kept_redline": [],
        "primary_metric": "signal_density_for_drama",
        "not_a_kpi": "tokens_saved",
    }
    if not enabled:
        report["mode"] = "passthrough"
        return [dict(p) for p in pieces], report

    report["mode"] = "soft_activation"
    out: list[dict[str, Any]] = []
    for p in pieces:
        name = str(p.get("name") or "")
        text = str(p.get("text") or "")
        if is_redline_segment(name) or not is_soft_segment(name):
            out.append(dict(p))
            if is_redline_segment(name):
                report["kept_redline"].append(name)
            continue
        # soft class
        if segment_matches_activation(text, keys):
            out.append(dict(p))
            report["kept_soft"].append(name)
        else:
            report["dropped"].append(name)
            # 不加入 out = 丢弃；绝不碰 redline
    return out, report
