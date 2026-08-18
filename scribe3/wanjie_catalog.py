"""万界设定库种子。store.add_term / add_item，禁止 add_entity(kind=term)。"""
from __future__ import annotations

from typing import Any

WANJIE_TERMS: tuple[tuple[str, str], ...] = (
    ("大遮蔽", "Lun-A 牢笼/摇篮/双向隐形；破损即大泄露"),
    ("成核点", "伪真空里的真真空泡 / 拓扑锚"),
    ("相位锚", "普罗米修斯同盟工程节点"),
    ("伪真空", "亚稳态泡，世界所在"),
    ("指针态", "环境冗余锁定的可复制状态"),
    ("逻辑豁免", "柳岸青自指闭环，异界无法叙事寄生"),
    ("场核", "拓扑锚；拔核=真空衰变"),
    ("冗余", "量子达尔文主义：环境复制即现实"),
    ("烛照", "微管高阶干涉，主动编排坍缩"),
)
WANJIE_ITEMS: tuple[tuple[str, str], ...] = (
    ("金縢之箱", "封印容器"),
    ("场核碎片", "穿越/锚定必需"),
    ("令牌", "守火人通行证物"),
)


def ensure_wanjie_catalog(st: Any) -> dict[str, int]:
    """幂等写入。无 add_term/add_item 则静默空。"""
    n_t = n_i = 0
    add_t = getattr(st, "add_term", None)
    add_i = getattr(st, "add_item", None)
    if not callable(add_t) and not callable(add_i):
        return {"terms": 0, "items": 0}
    if callable(add_t):
        for name, definition in WANJIE_TERMS:
            add_t(name, category="wanjie", definition=definition)
            n_t += 1
    if callable(add_i):
        for name, desc in WANJIE_ITEMS:
            add_i(name, category="wanjie", description=desc)
            n_i += 1
    return {"terms": n_t, "items": n_i}


WORLD_PHRASE = tuple(name for name, _ in WANJIE_TERMS)


def parse_axis_terms(axis_raw: Any) -> list[str]:
    if axis_raw is None:
        return []
    if isinstance(axis_raw, (list, tuple, set)):
        return [str(x).strip() for x in axis_raw if str(x).strip()]
    text = str(axis_raw).strip()
    if not text:
        return []
    import re
    return [p for p in re.split(r"[/、，,\s]+", text) if p]


def should_seed_wanjie(axis_terms: list[str] | None) -> bool:
    return bool(set(axis_terms or ()) & set(WORLD_PHRASE))


def maybe_seed_from_axis(st: Any, axis_raw: Any) -> dict[str, int]:
    if not should_seed_wanjie(parse_axis_terms(axis_raw)):
        return {"terms": 0, "items": 0}
    return ensure_wanjie_catalog(st)
