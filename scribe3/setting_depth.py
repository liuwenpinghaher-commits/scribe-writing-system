"""设定内容深度：只有唯一正确答案的项。

空间铺开、设定当障碍、实体厚度、悬置。说教/感官密度/红鲱鱼不在这里。
本模块只吃公开数据结构，不碰 store 私有查询。
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from scribe3.charter import STORY_PREFIXES


#: 地点从属用命题表达，不新开表。attribute 只认这几个，value 走 canon_oid。
PLACE_IN_ATTRS = frozenset({"位于", "从属"})
#: 厚度把关：实体从首现到已铺末章至少这么多章。改前把刚出场的和老实体混算。
THICKNESS_RUNWAY = 20


def place_containment(facts) -> list[tuple[str, str]]:
    """(子地点名, 上级地点名)。只认 place: 主语、位于/从属、value 能归到 place:。"""
    from scribe3.ontology import canon_oid

    edges: list[tuple[str, str]] = []
    for f in facts or []:
        eid = str(getattr(f, "entity_id", "") or "")
        if not eid.startswith("place:"):
            continue
        attr = str(getattr(f, "attribute", "") or "").strip()
        if attr not in PLACE_IN_ATTRS:
            continue
        raw = str(getattr(f, "value", "") or "").strip()
        parent = canon_oid(raw) if ":" in raw else canon_oid(f"place:{raw}")
        if not parent or not parent.startswith("place:"):
            continue
        child = eid.split(":", 1)[1]
        par = parent.split(":", 1)[1]
        if child and par and child != par:
            edges.append((child, par))
    return edges


def place_regions(names: Iterable[str], *, edges: Iterable[tuple[str, str]] | None = None) -> dict[str, list[str]]:
    """用从属边算连通分量。没有边就每个地点自己一区。不再用名字前缀冒充上级。"""
    names = [str(n).strip() for n in names if str(n or "").strip()]
    uniq = sorted(set(names))
    parent: dict[str, str] = {n: n for n in uniq}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for child, par in edges or []:
        if child in parent and par in parent:
            parent[find(child)] = find(par)
    regions: dict[str, list[str]] = {}
    for n in uniq:
        regions.setdefault(find(n), []).append(n)
    return regions


def spatial_spread(names: Iterable[str], facts=None) -> dict[str, Any]:
    edges = place_containment(facts or [])
    extra = [n for pair in edges for n in pair]
    regions = place_regions(list(names) + extra, edges=edges)
    n_places = sum(len(v) for v in regions.values())
    n_regions = len(regions)
    singleton = sum(1 for v in regions.values() if len(v) == 1)
    return {
        "n_places": n_places,
        "n_regions": n_regions,
        "singleton_regions": singleton,
        "singleton_ratio": (singleton / n_regions) if n_regions else 0.0,
        "regions": {k: sorted(v) for k, v in regions.items()},
        "has_containment": bool(edges),
        "n_containment": len(edges),
    }


def thickness_distribution(facts, *, until: int | None = None, min_runway: int = 0) -> dict[str, Any]:
    """故事命题按实体分桶。promise: 不算。≤2 和 ≤4 口径分开，不许混用。

    min_runway>0 时只留「到 until 已有这么多章时间」的实体。改前把第 55 章出场的
    和第 5 章出场的放一起算。until 缺省则不过滤。
    """
    story = [f for f in facts if str(getattr(f, "entity_id", "")).startswith(STORY_PREFIXES)]
    counts: Counter[str] = Counter()
    first: dict[str, int] = {}
    for f in story:
        eid = f.entity_id
        ch = int(getattr(f, "valid_from", 0) or 0)
        counts[eid] += 1
        prev = first.get(eid)
        if prev is None or ch < prev:
            first[eid] = ch
    if until is not None and min_runway > 0:
        keep = {e for e, fs in first.items() if int(until) - fs >= min_runway}
        counts = Counter({e: n for e, n in counts.items() if e in keep})
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
        "first": dict(first),
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
    """有 cost 且被命题点名的世界规则。装饰性规则（有代价没人触发）不算障碍。

    比例只报不拦。StoryScope SET_ATM_019 人 11.1% vs 模型 3–4% 是「整篇故事
    把设定当障碍」的取值占比，不是书内 world_rule 触发率。拿 11.1% 当下限，
    现库 5/6=83% 必过，等于挑一个让库通过的数。书内触发率没有实测，不设门。
    「至少一条被引用」更不可能红，已经废掉。
    _rule_needles 的 2 字匹配抽样是真命中，不许改。

    障碍比例的分母是有代价的规则，不是全部规则。没代价的被引用只是装饰，
    不能把分母拉大。无名规则不计条。
    """
    named: list[dict] = []
    for r in (rules or []):
        if not r:
            continue
        if str(r.get("name") or "").strip():
            named.append(r)
    with_cost: list[str] = []
    triggered: list[str] = []
    costed_triggered: list[str] = []
    blob = " ".join(f"{getattr(f, 'attribute', '')} {getattr(f, 'value', '')}" for f in facts)
    for r in named:
        name = str(r.get("name") or "").strip()
        cost = str(r.get("cost") or "").strip()
        if cost:
            with_cost.append(name)
        hit = any(n in blob for n in _rule_needles(name))
        if hit:
            triggered.append(name)
            if cost:
                costed_triggered.append(name)
    n = len(named)
    n_cost = len(with_cost)
    return {
        "n_rules": n,
        "with_cost": n_cost,
        "triggered": len(triggered),
        "triggered_names": triggered,
        "triggered_ratio": (len(triggered) / n) if n else 0.0,
        "costed_triggered": len(costed_triggered),
        "obstacle_ratio": (len(costed_triggered) / n_cost) if n_cost else 0.0,
    }


def _volume_index(ch: int, ends: list[int]) -> int | None:
    for i, e in enumerate(ends):
        if int(ch) <= e:
            return i
    return None


def suspense_rate(promises: Iterable[dict], *, volume_ends: list[int]) -> dict[str, Any]:
    """跨卷未收：仍开着、且埋在终卷之前的线。

    显示和把关必须用这一个数。曾经用 all_closed（开口线在不在末卷都算没全收）
    把关、用 cross_open 显示，于是「不得为 0」旁边写着 0 却判通过。

    跨 ≥3 卷只报不拦：没有依据说多少才对。

    只有 status=open 才算悬着。库里收线是 closed，弃置是 abandoned。
    曾经写 `open or payoff is None`：已关/已弃但没填收章的线会被当成跨卷未收。
    """
    ends = sorted(int(x) for x in volume_ends if x)
    rows = [p for p in (promises or []) if p.get("setup_chapter") is not None]
    n = len(rows)
    last_i = len(ends) - 1 if ends else 0
    by_volume: list[dict[str, Any]] = []
    prev = 0
    for i, e in enumerate(ends):
        by_volume.append({
            "index": i + 1,
            "lo": prev + 1,
            "hi": e,
            "cross_open": 0,
            "is_last": i == last_i,
        })
        prev = e

    cross_open = 0
    long_span = 0
    for p in rows:
        si = _volume_index(int(p["setup_chapter"]), ends)
        if si is None:
            continue
        status = str(p.get("status") or "open").lower()
        pc = p.get("payoff_chapter")
        still_open = status == "open"
        if still_open:
            ei = last_i
        elif pc is not None:
            ei = _volume_index(int(pc), ends)
            if ei is None:
                ei = last_i
        else:
            continue
        if ei - si >= 3:
            long_span += 1
        if still_open and si < last_i:
            cross_open += 1
            by_volume[si]["cross_open"] += 1

    barren = [f"{v['lo']}-{v['hi']}" for v in by_volume
              if not v["is_last"] and v["cross_open"] == 0]
    return {
        "n": n,
        "cross_open": cross_open,
        "rate": (cross_open / n) if n else 0.0,
        "by_volume": by_volume,
        "barren_volumes": barren,
        "long_span": long_span,
        "long_span_ratio": (long_span / n) if n else 0.0,
    }


# 方案书第六节。不许为了现库通过而调低。
LE2_RATIO_MAX = 0.10
LE4_RATIO_MAX = 0.15
TOP3_SHARE_MAX = 0.20
# 跨卷未收下限。作者定的连载口径，不是 StoryScope 推出来的。
# StoryScope 只说明模型默认把话说完；连载要留多少悬着没有实测，不许伪装。
CROSS_OPEN_MIN = 0.15
