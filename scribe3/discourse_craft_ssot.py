"""话语层工艺 tip / product_label SSOT（Week-1 · advisory only）。

禁止并入 L0 structure_diversity；生成前长文仍归 craft.py。
"""
from __future__ import annotations

from typing import Any

# 写前注入默认句（Week-2 discourse_soft 用；W1 仅 soft 可复述）
MESO_DEFAULT = "讲法：贴本章焦点者限知；慎用叙述者越界全知点破因果。"
SERIAL_DEFAULT = "连载：章末留未决或动作定格；本章相对近章须有可感知信息增量。"

TIPS: dict[str, dict[str, str]] = {
    "telling": {
        "product_label": "情绪贴标",
        "tip": "少用「感到/觉得」直贴情绪；改写动作、生理反应或对话外泄。",
    },
    "god_view": {
        "product_label": "越界全知",
        "tip": "当前句像叙述者越界点破因果；收回到焦点者可感知的信息。",
    },
    "rhythm": {
        "product_label": "节奏过匀",
        "tip": "句长过于整齐时易窒息；交错长短句与对白/动作段。",
    },
    "oversat": {
        "product_label": "意象/解释过密",
        "tip": "删一层比喻或解释，留白给读者推断。",
    },
    "ending_formula": {
        "product_label": "公式收束",
        "tip": "短句+意象回扣≠真钩子；改为未决问题或动作定格。",
    },
    "hook_plan": {
        "product_label": "缺章末钩规划",
        "tip": "在节拍末拍 hook 或 beats_meta.chapter_hook 写清未决/定格。",
    },
    "hook_on_page": {
        "product_label": "钩子落地弱",
        "tip": "规划有钩、正文尾段痕迹弱（启发，可误报）；把钩子写进最后一段。",
    },
    "info_delta": {
        "product_label": "信息增量偏低",
        "tip": "本章大纲相对近章新字块偏少；补冲突新事实或立场变化。",
    },
    "stakes_on_page": {
        "product_label": "代价未上正文",
        "tip": "大纲有代价，正文未检出痕迹（启发，可误报）。",
    },
    "breath": {
        "product_label": "呼吸偏紧",
        "tip": "贴标/节奏/密度叠加时，优先改一句对白与一句留白。",
    },
}


def tip_for(family: str) -> dict[str, str]:
    row = TIPS.get(str(family or "").strip()) or {}
    return {
        "product_label": row.get("product_label") or family,
        "tip": row.get("tip") or "",
    }


def tip_text(family: str) -> str:
    return tip_for(family).get("tip") or ""


def product_label(family: str) -> str:
    return tip_for(family).get("product_label") or family


def soft_tip_list(*families: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in families:
        t = tip_for(f)
        if t.get("tip"):
            out.append({"family": f, **t})
    return out
