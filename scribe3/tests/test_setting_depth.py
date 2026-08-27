"""StoryScope 死穴：有唯一正确答案的才能当门。

空间铺开、设定当障碍、实体厚度分布、悬置率。
说教/感官密度/红鲱鱼不许进这里，更不许进提示词。
"""
from __future__ import annotations

from scribe3.ontology import Fact
from scribe3.setting_depth import (
    obstacle_rate,
    place_regions,
    spatial_spread,
    suspense_rate,
    thickness_distribution,
)


def _f(local, entity, attr, value, ch=1):
    return Fact(f"fact:{local}", entity, attr, value, ch, None, False, [])


def test_place_regions_nest_by_name_prefix():
    """地点没有 geography 上级字段。用名字前缀认区域，对这批名字有唯一答案。"""
    names = ["不署名门", "不署名门签押廊", "地球", "月球"]
    regions = place_regions(names)
    assert set(regions["不署名门"]) == {"不署名门", "不署名门签押廊"}
    assert regions["地球"] == ["地球"]
    assert regions["月球"] == ["月球"]


def test_spatial_spread_reports_singleton_ratio():
    s = spatial_spread(["不署名门", "不署名门签押廊", "地球", "月球"])
    assert s["n_places"] == 4
    assert s["n_regions"] == 3
    assert s["singleton_regions"] == 2  # 地球、月球
    assert s["singleton_ratio"] == 2 / 3


def test_thickness_buckets_and_top3_share():
    """总量会骗人。必须给分桶和长尾。口径写死：≤2 与 ≤4 分开。"""
    facts = (
        [_f(f"a{i}", "role:柳岸青", f"a{i}", "x", i) for i in range(10)]
        + [_f(f"b{i}", "role:沈烛", f"b{i}", "x", i) for i in range(5)]
        + [_f("c1", "org:天龙座", "面目", "一句话", 1)]
        + [_f("d1", "place:地球", "位置", "一句话", 1)]
        + [_f("d2", "place:月球", "位置", "一句话", 1)]
        + [_f("p1", "promise:abc", "伏笔", "不算故事实体", 1)]
    )
    t = thickness_distribution(facts)
    assert t["n_entities"] == 5
    assert t["n_facts"] == 18
    assert t["le2"] == 3  # 天龙座、地球、月球
    assert t["le4"] == 3
    assert t["le2_ratio"] == 3 / 5
    assert t["top3_share"] == (10 + 5 + 1) / 18
    assert t["counts"]["role:柳岸青"] == 10


def test_obstacle_needs_cost_and_a_fact_that_cites_the_rule():
    """有代价字段还不够，必须真被命题引用。装饰性规则不算障碍。"""
    rules = [
        {"name": "光子投票", "cost": "从体温里扣"},
        {"name": "没人用的规矩", "cost": "也有代价"},
        {"name": "空规矩", "cost": ""},
    ]
    facts = [_f("1", "role:甲", "投票", "他用光子投票盖过反对票", 3)]
    o = obstacle_rate(rules, facts)
    assert o["n_rules"] == 3
    assert o["with_cost"] == 2
    assert o["triggered"] == 1
    assert o["triggered_ratio"] == 1 / 3


def test_obstacle_matches_distinctive_part_of_long_rule_name():
    """全名对不上不等于没引用。真库「拓扑锚定与场核」一次没命中，场核在 43 条命题里。"""
    rules = [{"name": "拓扑锚定与场核", "cost": "反噬"}]
    facts = [_f("1", "role:柳岸青", "场核嗡鸣", "腕内倒计时随体温下降", 3)]
    assert obstacle_rate(rules, facts)["triggered"] == 1


def test_suspense_is_open_lines_that_crossed_a_volume():
    """全收完 = 把话说完 = 无悬念。悬置率不得为 0。"""
    promises = [
        {"text": "旧线", "setup_chapter": 4, "payoff_chapter": 18, "status": "paid"},
        {"text": "跨卷还开着", "setup_chapter": 18, "payoff_chapter": None, "status": "open"},
        {"text": "本卷刚埋", "setup_chapter": 195, "payoff_chapter": None, "status": "open"},
    ]
    # 卷界 20, 40, … 200
    bounds = list(range(20, 201, 20))
    s = suspense_rate(promises, volume_ends=bounds)
    assert s["n"] == 3
    assert s["cross_open"] == 1
    assert s["rate"] == 1 / 3
    assert s["all_closed"] is False
