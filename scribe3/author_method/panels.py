"""钩类型 / 开篇 / 清单 / 大纲 / 日更·回炉 — 面板数据。勾选永不进 draft。"""
from __future__ import annotations

from typing import Any

# 清单项 id 禁止出现在组装段名与正文
CHECKLIST_SEGMENT_NAME = "quality_checklist"

HOOK_TYPES: tuple[tuple[str, str], ...] = (
    ("suspense", "悬念"),
    ("crisis", "危机"),
    ("reversal", "反转"),
    ("emotion", "情绪"),
    ("info", "信息"),
    ("countdown", "倒计时"),
    ("cost", "代价"),
    ("underdog", "弱者"),
)

CHECKLIST_ITEMS: tuple[tuple[str, str], ...] = (
    ("scene_goal", "这场戏谁要什么"),
    ("scene_obstacle", "谁/什么挡住了"),
    ("scene_change", "结束后什么变了"),
    ("hook_last_lines", "章末三行有未决"),
    ("no_weather_open", "开篇不是天气/醒来流水账"),
    ("one_scene_one_play", "一段一戏"),
    ("cost_on_page", "代价落在纸上"),
    ("info_delta", "本章有新信息"),
    ("pov_pipe", "新知有到达管道"),
    ("no_summary_exit", "场末不总结升华"),
)

OPENING_CHECKS: tuple[str, ...] = (
    "黄金三章内给出困境或优势切入",
    "开篇第一句钉人/地/未决之一",
    "禁纯天气、禁无冲突醒来",
    "前三章至少一次立场或代价翻转",
)

OUTLINE_STEPS: tuple[str, ...] = (
    "今天村里过什么日子 / 必须发生的一下",
    "主矛盾：谁挡谁、挡什么",
    "五步：起事→加压→假胜或失利→代价→钩",
    "升级感：本章比上章多一寸不可逆",
    "期待：读者要翻页的具体问题",
)

DAILY_STEPS: tuple[str, ...] = (
    "看昨日钩与今日合同四字段",
    "取一张招式（本意×绕法）或明确直线风险",
    "写场面，不灌清单全文",
    "章末留下未决，登记钩类型",
)

REVISION_STEPS: tuple[str, ...] = (
    "标出直线砸脸句，按招式公式改绕",
    "限知穿帮单独过一遍",
    "禁词/复读走 post-check，不在此重写词表",
    "回炉只改 span，不整章倾倒方法论",
)


def panel_payload() -> dict[str, Any]:
    return {
        "hook_types": [{"id": i, "label": l} for i, l in HOOK_TYPES],
        "checklist": [{"id": i, "label": l} for i, l in CHECKLIST_ITEMS],
        "opening": list(OPENING_CHECKS),
        "outline": list(OUTLINE_STEPS),
        "daily": list(DAILY_STEPS),
        "revision": list(REVISION_STEPS),
    }


def checklist_prompt_text(selected: list[str] | None) -> str:
    """写路径合同：无论勾选什么，永远返回空串。"""
    _ = selected
    return ""
