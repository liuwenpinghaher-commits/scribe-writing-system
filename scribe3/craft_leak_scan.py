"""成稿侧工艺泄露：侧门开法 / 炉契全文 / 无铺垫的「怎知」。

纯函数。供 find_leaks 与 post-check 复用。
"""
from __future__ import annotations

import re
from typing import Any

# A7：非知情 POV 不得写操作步骤
SIDE_DOOR_MARKERS = ("铜签", "锁眼", "拨锁", "门轴")
# 炉契全文惩罚
FURNACE_MARKERS = ("填炉底", "炉契全文", "拿自个儿去填炉底")
# 无因果全知
OMNISCIENT_MARKERS = ("军中", "一条人命")

# 断刀鞘互斥来历（现行真：霍三刀之物，沈拾灯暂扣，还到炉前）
SHEATH_CANON = "断刀鞘是霍三刀之物，沈拾灯暂扣，须还到炉前。禁止改写成爹的遗物、郭家三刀或霍不知谁拾。"
SHEATH_FORBIDDEN = ("爹的东西", "你爹的东西", "郭家三刀", "霍不知谁拾", "不知道谁拾")

_KNOWERS_SIDE_DOOR = ("老桂", "role:老桂")


def _has_any(text: str, marks: tuple[str, ...]) -> list[str]:
    hit = []
    for m in marks:
        if m and m in (text or ""):
            hit.append(m)
    return hit


def focalizer_is_side_door_knower(focalizer: str) -> bool:
    foc = (focalizer or "").strip()
    if not foc:
        return False
    for k in _KNOWERS_SIDE_DOOR:
        if k in foc or foc.endswith(k):
            return True
    return False


def scan_craft_leaks(prose: str, focalizer: str = "") -> list[dict[str, Any]]:
    """返回 [{id, marker, kind, range}]。"""
    text = prose or ""
    out: list[dict[str, Any]] = []

    def _add(kind: str, marker: str, eid: str) -> None:
        i = text.find(marker)
        if i < 0:
            return
        out.append({
            "id": eid,
            "marker": marker,
            "kind": kind,
            "range": (i, i + len(marker)),
        })

    if not focalizer_is_side_door_knower(focalizer):
        for m in _has_any(text, SIDE_DOOR_MARKERS):
            _add("side_door", m, "craft:side_door")
    for m in _has_any(text, FURNACE_MARKERS):
        _add("furnace_covenant", m, "craft:furnace_covenant")
    if not focalizer_is_side_door_knower(focalizer):
        # 阿绣点破军中人命：无铺垫全知
        if "军中" in text and "人命" in text:
            _add("unearned_knowing", "军中", "craft:unearned_knowing")
    for m in _has_any(text, SHEATH_FORBIDDEN):
        _add("sheath_contradiction", m, "craft:sheath_canon")
    return out


def sheath_canon_block() -> str:
    return "\n\n## 物件现行真\n" + SHEATH_CANON + "\n"


def revelation_furnace_line() -> str:
    return "不得揭破炉契全文惩罚（头一个名字填炉底）；只写人物此刻能感到的火与怕。"
