"""设定之间的一致性扫描。

千万字连载最怕设定崩了没法回收——第 300 章立的规则和第 2000 章立的规则打架，
系统不知道，直到读者读出来（读者会记得比作者清楚）。

而全库此前只有 **一个** 设定间校验器 `validate_faction_consistency`，只管势力。
`validate_setting` 看名字像，其实是「正文 vs 设定」，必须传 prose 才能跑。
三万条命题互相之间没有任何一致性保证。

这里补四类，全部客观可判，不含任何主观/文笔判断：

  value_conflict         同实体同属性，时间窗重叠，值却不一样
  knowledge_before_fact  谁在事实成立之前就知道了它
  bad_window             失效早于生效
  wide_secret            标了秘密，却几乎人人都知道

只读 store 公开方法，不碰 `_query`（分层锁）。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

#: 秘密被这么多角色知道以上就不算秘密了。四个人知道的事瞒不住，是常识不是文笔判断。
WIDE_SECRET_KNOWERS = 4


@dataclass(frozen=True)
class Contradiction:
    kind: str
    severity: str  # error = 逻辑上不可能；warn = 可能是有意为之
    entity: str
    detail: str
    chapters: tuple[int, ...] = ()

    def __str__(self) -> str:
        mark = "✗" if self.severity == "error" else "?"
        where = f"（第 {'/'.join(str(c) for c in self.chapters)} 章）" if self.chapters else ""
        return f"  {mark} [{self.kind}] {self.entity}{where}：{self.detail}"


def _overlaps(a_from: int, a_to, b_from: int, b_to) -> bool:
    """两个 [from, to) 窗口是否重叠。to=None 表示至今有效。"""
    a_end = a_to if a_to is not None else float("inf")
    b_end = b_to if b_to is not None else float("inf")
    return a_from < b_end and b_from < a_end


def scan_value_conflicts(facts) -> list[Contradiction]:
    """同实体同属性、窗口重叠、值不同。

    这是设定打架最常见的形态：第 300 章说门主姓王，第 2000 章说姓李，
    两条都还有效。真要改设定应当给旧条目设 valid_to（换代），而不是并存。
    """
    buckets: dict[tuple[str, str], list] = defaultdict(list)
    for f in facts:
        buckets[(f.entity_id, f.attribute)].append(f)

    out: list[Contradiction] = []
    for (entity, attr), group in buckets.items():
        if len(group) < 2:
            continue
        group = sorted(group, key=lambda f: f.valid_from)
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if str(a.value).strip() == str(b.value).strip():
                    continue
                if not _overlaps(a.valid_from, a.valid_to, b.valid_from, b.valid_to):
                    continue
                out.append(Contradiction(
                    "value_conflict", "error", f"{entity}·{attr}",
                    f"两条同时有效但说法不同：「{str(a.value)[:40]}」 / 「{str(b.value)[:40]}」",
                    (a.valid_from, b.valid_from)))
    return out


def scan_knowledge_before_fact(facts, edges) -> list[Contradiction]:
    """谁在事实成立之前就知道了它。硬逻辑错误，没有例外。"""
    by_id = {f.id: f for f in facts}
    out: list[Contradiction] = []
    for e in edges:
        f = by_id.get(e.proposition_id)
        if f is None or not getattr(e, "polarity", True):
            continue
        if e.since_chapter < f.valid_from:
            out.append(Contradiction(
                "knowledge_before_fact", "error", e.knower_id,
                f"第 {e.since_chapter} 章就知道了「{f.attribute}」，"
                f"可这件事第 {f.valid_from} 章才成立",
                (e.since_chapter, f.valid_from)))
    return out


def scan_bad_windows(facts) -> list[Contradiction]:
    """失效不能早于生效。"""
    out: list[Contradiction] = []
    for f in facts:
        if f.valid_to is not None and f.valid_to <= f.valid_from:
            out.append(Contradiction(
                "bad_window", "error", f"{f.entity_id}·{f.attribute}",
                f"第 {f.valid_from} 章生效，第 {f.valid_to} 章就失效了",
                (f.valid_from, f.valid_to)))
    return out


def scan_wide_secrets(facts, edges) -> list[Contradiction]:
    """标了 secret 却人人都知道。不是逻辑错，是提醒作者这条已经瞒不住了。"""
    knowers: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        if getattr(e, "polarity", True):
            knowers[e.proposition_id].add(e.knower_id)
    out: list[Contradiction] = []
    for f in facts:
        if not f.secret:
            continue
        who = {k for k in knowers.get(f.id, ()) if k != "reader"}
        if len(who) >= WIDE_SECRET_KNOWERS:
            out.append(Contradiction(
                "wide_secret", "warn", f"{f.entity_id}·{f.attribute}",
                f"标着秘密，却有 {len(who)} 个人知道：{'、'.join(sorted(who)[:5])}",
                (f.valid_from,)))
    return out


def scan(store, *, until_chapter: int | None = None) -> list[Contradiction]:
    """全库扫一遍。until_chapter 缺省扫到底。

    读的是未折叠命题：`facts_at` 会把同 (entity, attribute) 折成单真，
    冲突的一方在读取时就没了，`scan_value_conflicts` 会永远返回空。
    """
    ch = until_chapter if until_chapter is not None else 99999
    reader = getattr(store, "facts_unfolded_at", None) or store.facts_at
    facts = list(reader(ch) or [])
    try:
        edges = list(store.load_knowledge() or [])
    except Exception:
        edges = []
    return (scan_value_conflicts(facts)
            + scan_knowledge_before_fact(facts, edges)
            + scan_bad_windows(facts)
            + scan_wide_secrets(facts, edges))


def report(items: list[Contradiction]) -> str:
    if not items:
        return "没查到矛盾。"
    errors = [c for c in items if c.severity == "error"]
    warns = [c for c in items if c.severity == "warn"]
    lines = [f"查到 {len(errors)} 处矛盾、{len(warns)} 处提醒。"]
    for group, label in ((errors, "矛盾"), (warns, "提醒")):
        if not group:
            continue
        lines.append(f"\n{label}：")
        lines += [str(c) for c in group]
    return "\n".join(lines)
