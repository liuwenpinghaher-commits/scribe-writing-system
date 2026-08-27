"""设定内容深度：只有唯一正确答案的项。

空间铺开、设定当障碍、实体厚度、悬置。说教/感官密度/红鲱鱼不在这里。
本模块只吃公开数据结构，不碰 store 私有查询。
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from scribe3.charter import STORY_PREFIXES


def place_regions(names: Iterable[str]) -> dict[str, list[str]]:
    """用名字前缀认上级。地点表没有 geography 上级字段，对给定名单有唯一答案。"""
    names = [str(n).strip() for n in names if str(n or "").strip()]
    uniq = sorted(set(names), key=lambda n: (-len(n), n))
    parent: dict[str, str | None] = {n: None for n in uniq}
    for child in uniq:
        for cand in uniq:
            if cand != child and child.startswith(cand) and len(child) > len(cand):
                if parent[child] is None or len(cand) > len(parent[child] or ""):
                    parent[child] = cand
    regions: dict[str, list[str]] = {}
    for n in sorted(uniq):
        root = n
        seen: set[str] = set()
        while parent.get(root) and root not in seen:
            seen.add(root)
            root = parent[root]  # type: ignore[assignment]
        regions.setdefault(root, []).append(n)
    return regions


def spatial_spread(names: Iterable[str]) -> dict[str, Any]:
    regions = place_regions(names)
    n_places = sum(len(v) for v in regions.values())
    n_regions = len(regions)
    singleton = sum(1 for v in regions.values() if len(v) == 1)
    return {
        "n_places": n_places,
        "n_regions": n_regions,
        "singleton_regions": singleton,
        "singleton_ratio": (singleton / n_regions) if n_regions else 0.0,
        "regions": {k: sorted(v) for k, v in regions.items()},
    }


def thickness_distribution(facts) -> dict[str, Any]:
    """故事命题按实体分桶。promise: 不算。≤2 和 ≤4 口径分开，不许混用。"""
    story = [f for f in facts if str(getattr(f, "entity_id", "")).startswith(STORY_PREFIXES)]
    counts = Counter(f.entity_id for f in story)
    n_ent = len(counts)
    n_facts = sum(counts.values())
    le2 = sum(1 for n in counts.values() if n <= 2)
    le4 = sum(1 for n in counts.values() if n <= 4)
    top3 = sum(n for _, n in counts.most_common(3))
    return {
        "n_entities": n_ent,
        "n_facts": n_facts,
        "le2": le2,
        "le4": le4,
        "le2_ratio": (le2 / n_ent) if n_ent else 0.0,
        "le4_ratio": (le4 / n_ent) if n_ent else 0.0,
        "top3_share": (top3 / n_facts) if n_facts else 0.0,
        "top3": counts.most_common(3),
        "counts": dict(counts),
    }


def _rule_needles(name: str) -> list[str]:
    """规则名切成可查的实词。全名匹配会漏：拓扑锚定与场核 vs 命题只写场核。"""
    import re
    chunks = re.split(r"[与及和或、/]+", name or "")
    out: list[str] = []
    for chunk in chunks:
        parts = re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9()\-]+", chunk)
        for p in parts:
            if len(p) >= 2:
                out.append(p)
            if len(p) >= 4:
                out.append(p[:2])
    return out or ([name] if name else [])


def obstacle_rate(rules: Iterable[dict], facts) -> dict[str, Any]:
    """有 cost 且被命题点名的世界规则。装饰性规则（有代价没人触发）不算障碍。"""
    rows = [r for r in (rules or []) if r]
    with_cost = []
    triggered = []
    blob = " ".join(f"{getattr(f, 'attribute', '')} {getattr(f, 'value', '')}" for f in facts)
    for r in rows:
        name = str(r.get("name") or "").strip()
        cost = str(r.get("cost") or "").strip()
        if not name:
            continue
        if cost:
            with_cost.append(name)
        if any(n in blob for n in _rule_needles(name)):
            triggered.append(name)
    n = len(rows)
    return {
        "n_rules": n,
        "with_cost": len(with_cost),
        "triggered": len(triggered),
        "triggered_names": triggered,
        "triggered_ratio": (len(triggered) / n) if n else 0.0,
    }


def suspense_rate(promises: Iterable[dict], *, volume_ends: list[int]) -> dict[str, Any]:
    """埋下后跨过一卷仍未收的线。全收完 = 把话说完。"""
    ends = sorted(int(x) for x in volume_ends if x)
    rows = list(promises or [])
    n = 0
    cross_open = 0
    last = ends[-1] if ends else 0
    for p in rows:
        sc = p.get("setup_chapter")
        if sc is None:
            continue
        n += 1
        if str(p.get("status") or "open").lower() == "open":
            first_end = next((e for e in ends if e >= int(sc)), None)
            if first_end is not None and first_end < last:
                cross_open += 1
    return {
        "n": n,
        "cross_open": cross_open,
        "rate": (cross_open / n) if n else 0.0,
        "all_closed": n > 0 and cross_open == 0 and all(
            str(p.get("status") or "").lower() != "open" for p in rows if p.get("setup_chapter") is not None
        ),
    }


# 方案书第六节。不许为了现库通过而调低。
LE2_RATIO_MAX = 0.10
LE4_RATIO_MAX = 0.15
TOP3_SHARE_MAX = 0.20
