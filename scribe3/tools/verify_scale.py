#!/usr/bin/env python3
"""铺完一批章之后的验收单，一条命令跑完。

铺 200 章要几个钟头，不能跑一次查一项、发现问题再跑一次。这里把所有客观判据
集中成一份报告：任何一项不过就退非零，不用人去逐条翻日志。

判据只收能机器算的。文笔类的一律不进（`top_keyword_share` 实测对人写和机器写
没有区分度，已经废掉，不要再加回来）。

用法：
    scribe3/.venv/bin/python -m scribe3.tools.verify_scale --db wanjie_scale
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scribe3.charter import audit_volume, normalize_charter  # noqa: E402
from scribe3.ontology import SUBJECT_PREFIXES, Fact  # noqa: E402
from scribe3.store import SurrealStore  # noqa: E402

OK, BAD = "  ✓", "  ✗"

# 方案书第六节。不许为了让现库通过而调低。
CHAR_ISSUE_RATIO_MAX = 0.3
COMPLETENESS_SCORE_MIN = 80


class Report:
    def __init__(self) -> None:
        self.failed: list[str] = []

    def check(self, passed: bool, title: str, detail: str = "") -> None:
        print(f"{OK if passed else BAD} {title}" + (f"　{detail}" if detail else ""))
        if not passed:
            self.failed.append(title)


def laid_until(st) -> int:
    seqs = [int(c.get("seq") or 0) for c in (st.chapters_lite() or [])]
    return max(seqs) if seqs else 0


def volume_starts_after(v, laid: int) -> bool:
    rng = normalize_charter(v.get("charter"))["chapter_range"]
    return bool(rng) and int(rng[0]) > laid


def laid_volume_ends(st, laid: int) -> list[int]:
    """已铺范围内的卷末。没铺到的卷不算终卷，否则卷 2 的开口线会被当成跨 8 卷。"""
    ends: list[int] = []
    for v in sorted(st.list_volumes() or [], key=lambda x: int(x.get("sort_order") or 0)):
        rng = normalize_charter(v.get("charter"))["chapter_range"]
        if not rng or int(rng[0]) > laid:
            continue
        ends.append(min(int(rng[1]), laid))
    return ends or ([laid] if laid else [])


def check_volumes(st, rep: Report, hero: str, laid: int) -> None:
    print("\n【逐卷对账】")
    vols = [v for v in (st.list_volumes() or [])
            if normalize_charter(v.get("charter"))["chapter_range"]]
    if not vols:
        rep.check(False, "库里没有带契约的卷")
        return
    unlaid = [v for v in vols if volume_starts_after(v, laid)]
    vols = [v for v in vols if not volume_starts_after(v, laid)]
    if unlaid:
        print("  未铺（不计入红项）："
              + "、".join(f"卷{v.get('sort_order')}《{v.get('title')}》"
                          f"{normalize_charter(v.get('charter'))['chapter_range'][0]}-"
                          f"{normalize_charter(v.get('charter'))['chapter_range'][1]}"
                          for v in unlaid))
    if not vols:
        print("  （已铺范围内没有带契约的卷）")
        return
    bad_fresh, bad_intro, bad_pays, red, missing_know, undecidable_know = [], [], [], [], [], []
    keyed_know = False
    for v in sorted(vols, key=lambda x: int(x.get("sort_order") or 0)):
        a = audit_volume(st, v, hero)
        so = v.get("sort_order")
        print(f"  卷{so}《{v.get('title')}》{a.chapter_range[0]}-{a.chapter_range[1]}："
              f"新鲜度 {a.new_entities_per_10ch:.1f}／10章"
              f"　引入缺 {len(a.introduces_missing)}"
              f"　跨卷收线 {a.cross_volume_payoffs}/{a.pays_expected}"
              f"　该知道缺 {len(a.must_know_missing)}"
              f"　知情无法判定 {len(a.must_know_undecidable)}"
              f"　破红线 {len(a.must_not_know_violated)}")
        if a.new_entities_per_10ch < 5.0:
            bad_fresh.append(f"卷{so} {a.new_entities_per_10ch:.1f}")
        if a.introduces_missing:
            bad_intro.append(f"卷{so} 缺 {'、'.join(a.introduces_missing)}")
        if a.pays_short:
            bad_pays.append(f"卷{so} 差 {a.pays_short} 条")
        if a.must_not_know_violated:
            red.append(f"卷{so} {'、'.join(a.must_not_know_violated)}")
        n_keyed = (len(normalize_charter(v.get("charter"))["knowledge_end"]["must_know"])
                   - len(a.must_know_undecidable))
        if n_keyed > 0:
            keyed_know = True
        if a.must_know_missing:
            missing_know.append(f"卷{so} {len(a.must_know_missing)} 条")
        if a.must_know_undecidable:
            undecidable_know.append(f"卷{so} {len(a.must_know_undecidable)} 条")
        if a.must_not_know_unusable:
            print(f"    （契约这几条写不了，核对时跳过：{'、'.join(a.must_not_know_unusable)}）")

    print()
    rep.check(not bad_fresh, "每卷新鲜度 ≥5.0／10章", "；".join(bad_fresh))
    rep.check(not bad_intro, "契约点名的新实体都引入了", "；".join(bad_intro))
    rep.check(not bad_pays, "每卷收够了更早埋的线", "；".join(bad_pays))
    rep.check(not red, "红线一条没破", "；".join(red))
    if undecidable_know:
        print(f"  · 无法判定（契约无 key）　{'；'.join(undecidable_know)}")
    if missing_know:
        rep.check(False, "卷末该知道的都知道了", "；".join(missing_know))
    elif keyed_know:
        rep.check(True, "卷末该知道的都知道了", "")


def check_prefixes(st, rep: Report, until: int) -> None:
    print("\n【实体归位】")
    # 除了本体里的三个主语前缀，`promise:` 也是系统自己写的（`advance_promise`
    # 给每条兑现的伏笔立一条命题）。它不是故事实体，不进新鲜度，但也不是野前缀。
    allowed = set(SUBJECT_PREFIXES) | {"promise"}
    facts = list(st.facts_at(until) or [])
    wild: dict[str, int] = {}
    for f in facts:
        oid = f.entity_id or ""
        prefix = oid.split(":", 1)[0] if ":" in oid else "(无前缀)"
        if prefix not in allowed:
            wild[prefix] = wild.get(prefix, 0) + 1
    rep.check(not wild, "命题主语全在本体内",
              "、".join(f"{k}×{v}" for k, v in wild.items()))

    dangling = [f.entity_id for f in facts
                if f.entity_id.startswith(("role:", "place:")) and not st.entity(f.entity_id)]
    rep.check(not dangling, "没有悬挂实体",
              "、".join(sorted(set(dangling))[:5]))


def check_consistency(st, rep: Report, until: int, hero: str) -> None:
    """扫一致性，并且带阳性对照。

    「什么都没查出来」有两种可能：库是干净的，或者扫描器坏了。真出过后者——
    `scan` 走 `facts_at`，而它读的时候就把同键冲突折掉了，那条检查在真库上
    从来没查出过任何东西。所以归零之后必须插一条真矛盾、确认扫得出来、再删掉。
    """
    from scribe3.setting_audit import scan

    print("\n【一致性】")
    found = scan(st, until_chapter=until)
    for c in found[:10]:
        print(f"  · {c.kind}｜{c.detail}")
    rep.check(not found, "全库无矛盾", f"{len(found)} 条" if found else "")

    # 数条数，不认文案：矛盾的 detail 里只有两个冲突的值，没有属性名。
    probes = ["fact:__verify_probe0__", "fact:__verify_probe1__"]
    try:
        for pid, (value, ch) in zip(probes, [("甲", 1), ("乙", 2)]):
            st.add_fact(Fact(id=pid, entity_id=hero, attribute="验证探针",
                             value=value, valid_from=ch), supersede_open=False)
        after = scan(st, until_chapter=until)
        rep.check(len(after) > len(found), "阳性对照：插进去的矛盾能被扫出来",
                  f"{len(found)} → {len(after)}")
    finally:
        for pid in probes:
            try:
                st.delete_fact(pid)
            except Exception as e:
                print(f"  ! 探针 {pid} 没删掉，手工清一下：{e}")


def check_depth(st, rep: Report, until: int) -> None:
    """StoryScope 能当门的四项。监控项（说教/感官）绝对不进这里，也不进提示词。"""
    from scribe3.charter import normalize_charter, story_entities
    from scribe3.setting_depth import (
        CROSS_OPEN_MIN, LE2_RATIO_MAX, LE4_RATIO_MAX, THICKNESS_RUNWAY, TOP3_SHARE_MAX,
        obstacle_rate, spatial_spread, suspense_rate, thickness_distribution,
    )

    print("\n【内容深度】")
    facts = list(st.facts_at(until) or [])
    t_all = thickness_distribution(facts)
    t = thickness_distribution(facts, until=until, min_runway=THICKNESS_RUNWAY)
    print(f"  全部实体 {t_all['n_entities']}　命题 {t_all['n_facts']}"
          f"　≤2 {t_all['le2']}（{t_all['le2_ratio']:.0%}）"
          f"　≤4 {t_all['le4']}（{t_all['le4_ratio']:.0%}）"
          f"　前3占 {t_all['top3_share']:.0%}（只报）")
    print(f"  ≥{THICKNESS_RUNWAY}章时间 {t['n_entities']}　命题 {t['n_facts']}"
          f"　≤2 {t['le2']}（{t['le2_ratio']:.0%}）"
          f"　≤4 {t['le4']}（{t['le4_ratio']:.0%}）"
          f"　前3占 {t['top3_share']:.0%}（把关）")
    for oid, n in t["top3"]:
        print(f"    {oid} ×{n}")
    tail = sorted(((n, oid) for oid, n in t["counts"].items() if n <= 2), reverse=True)[:8]
    if tail:
        print("  长尾 ≤2：" + "、".join(f"{oid}×{n}" for n, oid in tail))
    # 改前：全部实体一起把关。改后：把关用有 ≥20 章时间的实体。全部那行只报。
    # 第 55 章出场的只有 5 章攒命题，和第 5 章出场的放一起算不是同一件事。
    rep.check(t["le2_ratio"] <= LE2_RATIO_MAX,
              f"实体命题数 ≤2 的占比 ≤{LE2_RATIO_MAX:.0%}",
              f"{t['le2']}/{t['n_entities']} = {t['le2_ratio']:.0%}")
    rep.check(t["le4_ratio"] <= LE4_RATIO_MAX,
              f"实体命题数 ≤4 的占比 ≤{LE4_RATIO_MAX:.0%}",
              f"{t['le4']}/{t['n_entities']} = {t['le4_ratio']:.0%}")
    rep.check(t["top3_share"] <= TOP3_SHARE_MAX,
              f"前 3 个实体占故事命题 ≤{TOP3_SHARE_MAX:.0%}",
              f"{t['top3_share']:.0%}")

    place_names = [oid.split(":", 1)[1] for oid in story_entities(facts)
                   if oid.startswith("place:")]
    sp = spatial_spread(place_names, facts)
    print(f"  地点 {sp['n_places']}　区域 {sp['n_regions']}"
          f"　一区一地点 {sp['singleton_regions']}（{sp['singleton_ratio']:.0%}）"
          f"　从属 {sp['n_containment']}")
    nested = sum(1 for v in sp["regions"].values() if len(v) >= 2)
    # 改前：用名字前缀认区域，测的是命名习惯。改后：读位于/从属命题算连通分量。
    # 无从属时只报不拦——现有 60 章没有这条数据，那是正确状态，不是失败。
    if not sp["has_containment"]:
        print("  无从属数据、只报不拦")
    else:
        spread_ok = sp["n_places"] < 8 or sp["singleton_ratio"] < 0.9
        rep.check(spread_ok, "一区一地点 <90%（地点≥8 时）",
                  f"{sp['n_places']} 地点 / {sp['n_regions']} 区域 / "
                  f"一区一地点 {sp['singleton_ratio']:.0%} / 多地点区域 {nested}")

    rules = st.list_world_rules() or []
    ob = obstacle_rate(rules, facts)
    print(f"  世界规则 {ob['n_rules']}　有代价 {ob['with_cost']}"
          f"　有代价且被点名 {ob['costed_triggered']}（障碍 {ob['obstacle_ratio']:.0%}）"
          f"　被点名 {ob['triggered']}（{ob['triggered_ratio']:.0%}）")
    if ob["triggered_names"]:
        print("    触发：" + "、".join(ob["triggered_names"][:8]))
    # 只报不拦。StoryScope 11.1% 搬不过来（故事级取值 ≠ 书内规则触发率）；
    # 「至少一条」有一条就永绿。没有依据就不设门。
    print("  设定当障碍比例只报不拦（无书内触发率依据，不设门）")

    ends = laid_volume_ends(st, until)
    print(f"  悬置口径：已铺到第 {until} 章，卷末 {ends or [until]}")
    su = suspense_rate(st.list_promises() or [], volume_ends=ends or [until])
    print(f"  悬置（跨卷未收）{su['cross_open']}/{su['n']} = {su['rate']:.0%}")
    if su["by_volume"]:
        barren = su["barren_volumes"]
        hung = [f"{v['lo']}-{v['hi']}×{v['cross_open']}"
                for v in su["by_volume"] if not v["is_last"]]
        print("    终卷前各卷未收：" + "、".join(hung))
        if barren:
            print("    无悬置：" + "、".join(barren))
    print(f"  跨≥3卷 {su['long_span']}/{su['n']} = {su['long_span_ratio']:.0%}（只报不拦，无依据设门）")
    # 显示和把关同一口径：跨卷未收 / 总线数。15% 是作者连载口径，不是 StoryScope。
    rep.check(su["n"] > 0 and su["rate"] >= CROSS_OPEN_MIN,
              f"跨卷未收 ≥{CROSS_OPEN_MIN:.0%}（连载口径，非 StoryScope）",
              f"{su['cross_open']}/{su['n']} = {su['rate']:.0%}")
    rep.check(su["n"] > 0 and not su["barren_volumes"],
              "终卷前每一卷都有跨卷未收的线",
              "无悬置：" + "、".join(su["barren_volumes"]) if su["barren_volumes"] else "")


def check_completeness(st, rep: Report) -> None:
    """接系统已有的 setting_completeness，不许另起炉灶。

    验收单曾经报全部通过，同时 79% 角色是空壳。完整度早就算出这个数。
    """
    print("\n【设定厚度】")
    try:
        c = st.setting_completeness() or {}
    except Exception as e:
        rep.check(False, "setting_completeness 调得起来", str(e))
        return
    ratio = float(c.get("char_issue_ratio") or 0)
    score = int(c.get("completeness_score") or 0)
    n_issues = len(c.get("char_issues") or [])
    n_chars = int(c.get("total_chars") or 0)
    missing = c.get("missing_dimensions") or []
    print(f"  角色 {n_chars}　空壳 {n_issues}　char_issue_ratio {ratio:.3f}"
          f"　completeness_score {score}")
    if missing:
        print(f"  缺维：{'、'.join(str(x) for x in missing)}")
    for row in (c.get("char_issues") or [])[:8]:
        print(f"  · {row.get('name')}：{'、'.join(row.get('issues') or [])}")
    if n_issues > 8:
        print(f"  · ……另有 {n_issues - 8} 人")
    rep.check(ratio <= CHAR_ISSUE_RATIO_MAX,
              f"空壳角色占比 ≤{CHAR_ISSUE_RATIO_MAX}",
              f"char_issue_ratio {ratio:.3f}（{n_issues}/{n_chars}）")
    rep.check(score >= COMPLETENESS_SCORE_MIN,
              f"设定完整度 ≥{COMPLETENESS_SCORE_MIN}",
              f"completeness_score {score}")


def check_scale(st, rep: Report, expect_chapters: int, laid: int) -> None:
    print("\n【规模】")
    print(f"  已铺到第 {laid} 章（目标 {expect_chapters}）")
    chs = st.chapters_lite() or []
    have = {int(c.get("seq") or 0) for c in chs}
    span = max(1, laid)
    gaps = sorted(set(range(1, span + 1)) - have)
    rep.check(not gaps, f"已铺 1-{laid} 章无缺口",
              f"缺 {len(gaps)} 章：{gaps[:12]}" if gaps else "")
    if laid < expect_chapters:
        print(f"  · 未铺 {laid + 1}-{expect_chapters}（不计入红项）")

    thin = [c.get("seq") for c in chs if len(str(c.get("synopsis") or "")) < 40]
    rep.check(not thin, "每章都有像样的梗概", f"过短 {len(thin)} 章：{thin[:10]}")

    ps = st.list_promises() or []
    closed = [p for p in ps if str(p.get("status") or "open") != "open"]
    rate = len(closed) / len(ps) if ps else 0
    rep.check(rate >= 0.7, "收线率 ≥70%",
              f"{len(closed)}/{len(ps)} = {rate:.0%}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8123/rpc")
    ap.add_argument("--ns", default="scribe3")
    ap.add_argument("--db", default="wanjie_scale")
    ap.add_argument("--chapters", type=int, default=200)
    ap.add_argument("--hero", default="role:柳岸青")
    a = ap.parse_args()

    st = SurrealStore(url=a.url, ns=a.ns, db=a.db)
    rep = Report()
    try:
        laid = laid_until(st)
        print(f"已铺到第 {laid} 章（--chapters 目标 {a.chapters}）。"
              "未铺的卷单独列出，不计入红项；跨卷指标只在已铺范围内算。")
        check_scale(st, rep, a.chapters, laid)
        check_volumes(st, rep, a.hero, laid)
        check_prefixes(st, rep, laid or a.chapters)
        check_consistency(st, rep, laid or a.chapters, a.hero)
        check_completeness(st, rep)
        check_depth(st, rep, laid or a.chapters)
    finally:
        st.close()

    print("\n" + "=" * 56)
    if rep.failed:
        print(f"不过关 {len(rep.failed)} 项：")
        for t in rep.failed:
            print(f"  - {t}")
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
