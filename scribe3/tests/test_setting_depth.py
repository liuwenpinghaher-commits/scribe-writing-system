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
    # 障碍 = 有代价且被引用。没代价的引用只是装饰。
    assert o["costed_triggered"] == 1
    assert o["obstacle_ratio"] == 1 / 3


def test_obstacle_has_no_ratio_threshold():
    """找不到能搬家的依据，不许拍一个门。

    StoryScope SET_ATM_019 的 11.1% 是「这篇故事把设定当障碍」的取值占比，
    不是书内 world_rule 被引用的比例。拿 11.1% 当下限，现库 5/6=83% 必过，
    就是挑一个让库通过的数。书内触发率没有实测，只报不拦。
    """
    import scribe3.setting_depth as sd

    assert not hasattr(sd, "OBSTACLE_RATIO_MIN")


def test_obstacle_matches_distinctive_part_of_long_rule_name():
    """全名对不上不等于没引用。真库「拓扑锚定与场核」一次没命中，场核在 43 条命题里。"""
    rules = [{"name": "拓扑锚定与场核", "cost": "反噬"}]
    facts = [_f("1", "role:柳岸青", "场核嗡鸣", "腕内倒计时随体温下降", 3)]
    assert obstacle_rate(rules, facts)["triggered"] == 1


def test_suspense_is_open_lines_that_crossed_a_volume():
    """跨卷未收 = 仍开着且埋在终卷之前。末卷刚埋的不算跨卷。"""
    promises = [
        {"text": "旧线", "setup_chapter": 4, "payoff_chapter": 18, "status": "paid"},
        {"text": "跨卷还开着", "setup_chapter": 18, "payoff_chapter": None, "status": "open"},
        {"text": "本卷刚埋", "setup_chapter": 195, "payoff_chapter": None, "status": "open"},
    ]
    bounds = list(range(20, 201, 20))
    s = suspense_rate(promises, volume_ends=bounds)
    assert s["n"] == 3
    assert s["cross_open"] == 1
    assert s["rate"] == 1 / 3


def test_cross_open_min_is_author_serial_floor_not_storyscope():
    """15% 是作者定的连载口径，不是 StoryScope 推出来的。不许假装实测依据。"""
    from scribe3.setting_depth import CROSS_OPEN_MIN

    assert CROSS_OPEN_MIN == 0.15


def test_suspense_zero_cross_open_even_when_last_volume_still_has_open_lines():
    """假闸原样：18 条未收全在最后一卷，跨卷未收是 0，不能因 all_closed 为假而绿。"""
    promises = [
        {"setup_chapter": 4, "payoff_chapter": 18, "status": "paid"},
        {"setup_chapter": 18, "payoff_chapter": 45, "status": "paid"},
        {"setup_chapter": 195, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 198, "payoff_chapter": None, "status": "open"},
    ]
    s = suspense_rate(promises, volume_ends=list(range(20, 201, 20)))
    assert s["cross_open"] == 0
    assert s["rate"] == 0.0
    assert s["n"] == 4


def test_suspense_reports_which_volumes_have_zero_hanging_lines():
    """终卷之前每一卷都要有跨卷未收。末卷排除。报告要写出哪几卷是 0。"""
    bounds = [10, 20, 30]
    promises = [
        {"setup_chapter": 2, "payoff_chapter": 8, "status": "paid"},
        {"setup_chapter": 12, "payoff_chapter": 28, "status": "paid"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
    ]
    s = suspense_rate(promises, volume_ends=bounds)
    assert s["cross_open"] == 0
    barren = s["barren_volumes"]
    assert "1-10" in barren and "11-20" in barren
    assert "21-30" not in barren
    by = {f"{v['lo']}-{v['hi']}": v["cross_open"] for v in s["by_volume"]}
    assert by["1-10"] == 0 and by["11-20"] == 0
    assert by["21-30"] == 0
    last = [v for v in s["by_volume"] if v["is_last"]]
    assert len(last) == 1 and last[0]["hi"] == 30


def test_suspense_per_volume_gate_fails_if_early_volumes_are_cleared():
    """只有早卷还挂着的线才算。卷1 挂一条、卷2 一条没有 → 卷2 仍约。"""
    bounds = [10, 20, 30]
    promises = [
        {"setup_chapter": 3, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 12, "payoff_chapter": 18, "status": "paid"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
    ]
    s = suspense_rate(promises, volume_ends=bounds)
    assert s["cross_open"] == 1
    assert s["barren_volumes"] == ["11-20"]


def test_long_span_ratio_is_reported_not_a_gate_number():
    """跨 ≥3 卷只报。现库 9/256=4%，没有依据说多少才对，不设门。"""
    bounds = [10, 20, 30, 40]
    promises = [
        {"setup_chapter": 2, "payoff_chapter": 8, "status": "paid"},    # 同卷
        {"setup_chapter": 2, "payoff_chapter": 15, "status": "paid"},   # 跨 1 卷
        {"setup_chapter": 2, "payoff_chapter": 25, "status": "paid"},   # 跨 2 卷
        {"setup_chapter": 2, "payoff_chapter": 35, "status": "paid"},   # 跨 3 卷
        {"setup_chapter": 2, "payoff_chapter": None, "status": "open"},  # 开到终卷，跨 3 卷
    ]
    s = suspense_rate(promises, volume_ends=bounds)
    assert s["long_span"] == 2
    assert s["long_span_ratio"] == 2 / 5
    assert "LONG_SPAN" not in dir(__import__("scribe3.setting_depth", fromlist=["CROSS_OPEN_MIN"]))


# ---------- 阳性对照：已知缺陷必须抓得到，撤掉缺陷后数要掉 ----------

def test_thickness_positive_control_zero_then_thin():
    """空集 le2=0 不能当真干净。塞三个一句话实体，≤2 必须从 0 变成 3。"""
    from scribe3.setting_depth import LE2_RATIO_MAX, LE4_RATIO_MAX, TOP3_SHARE_MAX

    # 16 个均厚实体：前 3 占 3/16=18.75% ≤20%；每实体 8 条，≤2/≤4 都是 0。
    even = [_f(f"e{i}_{j}", f"role:人{i}", f"a{j}", "x", j) for i in range(16) for j in range(8)]
    t0 = thickness_distribution(even)
    assert t0["le2"] == 0 and t0["le2_ratio"] <= LE2_RATIO_MAX
    assert t0["le4"] == 0 and t0["le4_ratio"] <= LE4_RATIO_MAX
    assert t0["top3_share"] <= TOP3_SHARE_MAX

    probe = even + [
        _f("thin1", "org:天龙座", "面目", "一句话", 1),
        _f("thin2", "place:地球", "位置", "一句话", 1),
        _f("thin3", "place:月球", "位置", "一句话", 1),
    ]
    t1 = thickness_distribution(probe)
    assert t1["le2"] == t0["le2"] + 3
    assert t1["le2_ratio"] > LE2_RATIO_MAX
    assert t1["le4_ratio"] > LE4_RATIO_MAX


def test_spatial_positive_control_eight_singletons():
    """≥8 地点且一区一地点 ≥90% 才是铺不开。7 个全散不算，第 8 个才过线。"""
    seven = [f"城{i}" for i in range(7)]
    s0 = spatial_spread(seven)
    assert s0["n_places"] < 8
    s1 = spatial_spread(seven + ["城7"])
    assert s1["n_places"] == 8
    assert s1["singleton_ratio"] == 1.0
    assert s1["singleton_ratio"] >= 0.9
    nested = spatial_spread(["不署名门", "不署名门签押廊"] + [f"城{i}" for i in range(6)])
    assert nested["n_places"] == 8
    assert nested["singleton_ratio"] < 0.9


def test_obstacle_positive_control_zero_then_one():
    """有代价没人引用 → 0；塞一条点名命题 → 1。数条数，不认文案。"""
    rules = [{"name": "光子投票", "cost": "从体温里扣"}]
    o0 = obstacle_rate(rules, [])
    assert o0["costed_triggered"] == 0
    o1 = obstacle_rate(rules, [_f("1", "role:甲", "投票", "他用光子投票盖过反对票", 3)])
    assert o1["costed_triggered"] == o0["costed_triggered"] + 1


def test_suspense_positive_control_zero_then_one():
    """末卷开口线保持 0；早卷再挂一条，跨卷未收必须 0→1。"""
    bounds = [20, 40]
    last_only = [{"setup_chapter": 35, "payoff_chapter": None, "status": "open"}]
    s0 = suspense_rate(last_only, volume_ends=bounds)
    assert s0["cross_open"] == 0
    s1 = suspense_rate(
        last_only + [{"setup_chapter": 5, "payoff_chapter": None, "status": "open"}],
        volume_ends=bounds)
    assert s1["cross_open"] == s0["cross_open"] + 1
    assert s1["barren_volumes"] == []
