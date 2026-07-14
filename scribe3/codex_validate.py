# scribe3/codex_validate.py
"""设定层结构化一致性校验(CX-Task 6):把长文本时代做不到的事变成可计算断言。

spec `docs/superpowers/specs/2026-07-14-codex-layer-redesign.md` §4:
"一致性校验:新增 validate_faction_consistency——检测如'势力 A 的关系里说敌对 B,
而 B 的关系里说结盟 A'(除非显式标为'错误认知')、'key_figures 里 active 的持烛者
>1 但 structure.core_size=1'、'artifacts 的 decay_rate 与章节时间线矛盾'等结构化
断言"。

只读、不落库——供 `GET /faction-consistency`(app.py)与作者自检使用。放在独立模块
(而非 store.py 或 codex_schema.py)是有意为之:store.py 已 6000+ 行,是持久化/查询
原语的家;codex_schema.py 是字段元数据注册表。本文件是"业务规则"层,风格上更接近
verify.py 的 `causal_complete(world, chapter)`——纯函数,吃一个 store-like 对象,
只读它的公开方法,不碰内部状态,因此不必是 SurrealStore 的方法。
"""
from __future__ import annotations

import re

# relation_type 之间的"结构性矛盾对"——注意:这里只判定 relation_type 本身在两条
# 【独立】entity_relation 边上互斥,不管 perception_a/b(那是允许不对称的主观认知,
# 见 _relation_contradictions 的docstring)。任意两个不同 relation_type 都视为潜在
# 矛盾(entity_relation 词表本就精简为 8 个互斥范畴,不存在"同时敌对又结盟"这种
# 合理并存的语义),所以判据从简:同一(无向)对之间出现 >1 种 relation_type 即报。
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _is_faction_ref(ref: object) -> bool:
    return isinstance(ref, str) and ref.startswith("faction:")


def _relation_contradictions(store) -> list[dict]:
    """A 说敌对 B,B 侧独立一条边说结盟 A → 报冲突。

    perception_a/b 不对称是合法的(spec 决策 3:允许错误认知)——但那是【同一条边】
    内的主观认知差异,与本判据无关:entity_relation 每条边只有一个客观 relation_type
    (perception_a/b 只是双方对这同一个客观关系的主观解读文本)。矛盾只可能来自
    【两条独立的边】各自宣称不同的 relation_type——这才是结构层面"没对齐"的信号。

    只比较当前仍"开着"的边(until_chapter IS NONE):已被 end_entity_relation 终止
    的旧关系代表"过去如此,现已改变"的时间演化,不是同时矛盾,不应与新关系一起
    误判为冲突。

    范围:只处理两端都是 faction: 前缀的边(本函数名为 validate_faction_consistency,
    entity_relation 是通用表,character/item 端的关系不在"势力一致性"校验范围内)。
    """
    issues: list[dict] = []
    rows = store.list_entity_relations() or []
    open_rows = [r for r in rows
                 if r.get("until_chapter") is None
                 and _is_faction_ref(r.get("a")) and _is_faction_ref(r.get("b"))]

    by_pair: dict[frozenset, list[dict]] = {}
    for r in open_rows:
        a, b = r.get("a"), r.get("b")
        if not a or not b:
            continue
        by_pair.setdefault(frozenset((a, b)), []).append(r)

    for pair, group in by_pair.items():
        types = sorted({r.get("relation_type") for r in group if r.get("relation_type")})
        if len(types) > 1:
            a, b = tuple(pair)
            issues.append({
                "kind": "relation_contradiction",
                "severity": "high",
                "faction": a,
                "detail": (f"{a} 与 {b} 之间存在互相矛盾的关系类型声明: {types}"
                          "(各自独立记录的 relation_type 冲突,非同一条边内 "
                          "perception_a/b 的主观认知差异——那是允许不对称的)"),
            })
    return issues


def _key_figures_exceed_core_size(store) -> list[dict]:
    """key_figures 里 status=active 的人数 > structure.core_size → 报冲突。"""
    issues: list[dict] = []
    for row in store.list_factions() or []:
        structure = row.get("structure")
        if not isinstance(structure, dict):
            continue
        core_size = structure.get("core_size")
        if not isinstance(core_size, (int, float)):
            continue
        figures = row.get("key_figures") or []
        active = sum(1 for k in figures if isinstance(k, dict) and k.get("status") == "active")
        if active > core_size:
            name = row.get("name")
            issues.append({
                "kind": "key_figures_exceed_core_size",
                "severity": "medium",
                "faction": name,
                "detail": (f"{name}:key_figures 中 status=active 的人数({active})"
                          f"超过 structure.core_size({core_size})"),
            })
    return issues


def _artifacts_beyond_max_chapter(store) -> list[dict]:
    """artifacts 的 last_transfer_chapter > 当前最大章 → 报冲突。"""
    issues: list[dict] = []
    try:
        max_ch = store.max_chapter()
    except Exception:
        return issues
    for row in store.list_factions() or []:
        name = row.get("name")
        for art in (row.get("artifacts") or []):
            if not isinstance(art, dict):
                continue
            ltc = art.get("last_transfer_chapter")
            if isinstance(ltc, (int, float)) and ltc > max_ch:
                issues.append({
                    "kind": "artifact_transfer_beyond_max_chapter",
                    "severity": "medium",
                    "faction": name,
                    "detail": (f"{name}:信物「{art.get('artifact_name')}」的 "
                              f"last_transfer_chapter={ltc} 超过当前最大章 {max_ch}"),
                })
    return issues


def _parse_percent(value: object) -> float | None:
    """从 power_share(自由文本,如 '30%'/'约三成')里尽力解析出百分比数值。
    解析不出就返回 None(该条不计入总和,不误报——'约三成'这类模糊描述不该拖累
    结构化校验的确定性)。"""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    m = _PERCENT_RE.search(value)
    if m:
        return float(m.group(1))
    stripped = value.strip()
    if stripped.replace(".", "", 1).isdigit():
        return float(stripped)
    return None


def _power_share_over_total(store) -> list[dict]:
    """(可选)internal_factions 的 power_share 总和明显 >100% → 报提示。
    只对能解析出数值的条目求和;一条都解析不出时不报(没有足够信息判断)。"""
    issues: list[dict] = []
    for row in store.list_factions() or []:
        subs = row.get("internal_factions") or []
        total = 0.0
        parsed_any = False
        for s in subs:
            if not isinstance(s, dict):
                continue
            share = _parse_percent(s.get("power_share"))
            if share is not None:
                total += share
                parsed_any = True
        if parsed_any and total > 100.0 + 1e-6:
            name = row.get("name")
            issues.append({
                "kind": "power_share_over_total",
                "severity": "low",
                "faction": name,
                "detail": (f"{name}:internal_factions 的 power_share 总和约 "
                          f"{total:g}%,超过 100%"),
            })
    return issues


def validate_faction_consistency(store) -> list[dict]:
    """势力设定的结构化一致性校验——长文本时代做不到的事,注册表化之后可以了。

    只读,不落库。返回 `[{kind, severity, faction, detail}, ...]`,空列表表示未发现问题。
    规则:
    1. relation_contradiction(硬冲突,high):两条独立 entity_relation 边对同一对
       势力给出互斥的 relation_type(perception_a/b 的主观不对称不算,那是合法的
       错误认知)。
    2. key_figures_exceed_core_size(medium):key_figures 里 active 人数超过
       structure.core_size。
    3. artifact_transfer_beyond_max_chapter(medium):信物的 last_transfer_chapter
       超过当前全书最大章。
    4. power_share_over_total(low,可选/提示级):internal_factions 的 power_share
       总和明显超过 100%。
    """
    issues: list[dict] = []
    issues.extend(_relation_contradictions(store))
    issues.extend(_key_figures_exceed_core_size(store))
    issues.extend(_artifacts_beyond_max_chapter(store))
    issues.extend(_power_share_over_total(store))
    return issues
