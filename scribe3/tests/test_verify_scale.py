"""验收单必须接上系统已有的完整度，不许另起炉灶。

verify_scale 曾经报「全部通过」，同时 79% 角色缺「他要什么」「他让人付出什么」。
setting_completeness 早就算出这个数，验收单没接。
"""
from __future__ import annotations

from scribe3.tools.verify_scale import Report, check_completeness


class _CompStore:
    def __init__(self, result):
        self._result = result

    def setting_completeness(self):
        return dict(self._result)


def test_empty_shells_fail_the_gate():
    """全书空壳比例只报不拦。没有点名写厚名单时不进 failed。"""
    import io
    from contextlib import redirect_stdout

    rep = Report()
    buf = io.StringIO()
    with redirect_stdout(buf):
        check_completeness(_CompStore({
            "char_issue_ratio": 0.789,
            "completeness_score": 64,
            "char_issues": [{"name": "甲", "issues": ["缺他要什么"]}],
            "missing_dimensions": ["势力/组织"],
            "total_chars": 19,
        }), rep)
    assert "只报不拦" in buf.getvalue()
    assert not any("空壳角色占比" in t or "设定完整度" in t for t in rep.failed)


def test_thick_book_passes_completeness():
    rep = Report()
    check_completeness(_CompStore({
        "char_issue_ratio": 0.2,
        "completeness_score": 84,
        "char_issues": [],
        "missing_dimensions": [],
        "total_chars": 10,
    }), rep)
    assert rep.failed == []


def test_thresholds_are_the_plan_numbers():
    """常数仍在，给报告格式化用。不再用它们 rep.check。"""
    from scribe3.tools.verify_scale import CHAR_ISSUE_RATIO_MAX, COMPLETENESS_SCORE_MIN

    assert CHAR_ISSUE_RATIO_MAX == 0.3
    assert COMPLETENESS_SCORE_MIN == 80


class _DepthStore:
    """check_depth 只吃公开方法。空命题让厚度/空间真空过，专门打悬置闸。"""

    def __init__(self, volumes, promises, rules=(), facts=()):
        self._volumes = volumes
        self._promises = promises
        self._rules = list(rules)
        self._facts = list(facts)

    def facts_at(self, until):
        return [f for f in self._facts if int(getattr(f, "valid_from", 0) or 0) <= until]

    def list_world_rules(self):
        return list(self._rules)

    def list_volumes(self):
        return list(self._volumes)

    def list_promises(self):
        return list(self._promises)


def _vols(*ends):
    prev = 0
    out = []
    for i, e in enumerate(ends, 1):
        out.append({"sort_order": i, "title": f"卷{i}",
                    "charter": {"chapter_range": [prev + 1, e]}})
        prev = e
    return out


def test_suspense_gate_uses_cross_open_not_all_closed():
    """跨卷未收占比不再进 failed。窗口才是硬项。"""
    from scribe3.tools.verify_scale import check_depth

    promises = [
        {"setup_chapter": 4, "payoff_chapter": 8, "status": "paid"},
        {"setup_chapter": 4, "payoff_chapter": 25, "status": "paid"},
        {"setup_chapter": 55, "payoff_chapter": None, "status": "open"},
    ]
    rep = Report()
    check_depth(_DepthStore(_vols(20, 40, 60), promises), rep, 60)
    assert not any("跨卷未收" in t for t in rep.failed), rep.failed
    assert not any("终卷前" in t for t in rep.failed), rep.failed


def test_obstacle_zero_is_reported_not_gated():
    """旧闸「至少一条被引用」在触发率为 0 时才会红，有一条就永绿。

    没有书内比例依据，改为只报不拦：代价全空、一条没触发，也不进 failed。
    """
    import io
    from contextlib import redirect_stdout
    from scribe3.tools.verify_scale import check_depth

    rules = [
        {"name": "光子投票", "cost": "扣体温"},
        {"name": "空规矩", "cost": ""},
    ]
    # 两卷、无线：悬置会红，但障碍不许跟着红。
    rep = Report()
    buf = io.StringIO()
    with redirect_stdout(buf):
        check_depth(_DepthStore(_vols(20, 40), [], rules=rules), rep, 40)
    out = buf.getvalue()
    assert "只报不拦" in out
    assert "有代价" in out
    assert not any("障碍" in t for t in rep.failed), rep.failed


def test_suspense_both_gates_pass_when_early_volumes_still_hang():
    from scribe3.tools.verify_scale import check_depth

    promises = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 4, "payoff_chapter": 8, "status": "paid"},
        {"setup_chapter": 25, "payoff_chapter": 30, "status": "paid"},
        {"setup_chapter": 45, "payoff_chapter": None, "status": "open"},
    ]
    # 跨卷未收 2/5 = 40% ≥15%；卷1、卷2 各一条未收。
    rep = Report()
    check_depth(_DepthStore(_vols(20, 40, 60), promises), rep, 60)
    assert not any("跨卷未收" in t or "终卷前" in t for t in rep.failed), rep.failed


def _fact(local, entity, attr, value, ch=1):
    from scribe3.ontology import Fact
    return Fact(f"fact:{local}", entity, attr, value, ch, None, False, [])


def test_check_depth_positive_control_thin_entities():
    """≤2 / ≤4 只报不拦。"""
    from scribe3.tools.verify_scale import check_depth

    facts = [_fact(f"t{i}", f"role:薄{i}", "面目", "一句话", 1) for i in range(5)]
    hanging = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
    ]
    rep = Report()
    check_depth(_DepthStore(_vols(20, 40), hanging, facts=facts), rep, 40)
    assert not any("≤2" in t for t in rep.failed), rep.failed
    assert not any("≤4" in t for t in rep.failed), rep.failed


def test_must_know_without_key_is_neither_pass_nor_fail():
    """对照库知情终态全无 key：报告无法判定，不进 failed，也不打钩。"""
    import io
    from contextlib import redirect_stdout
    from scribe3.ontology import Fact
    from scribe3.tools.verify_scale import check_volumes

    facts = [Fact(f"fact:n{i}", f"role:新{i}", f"a{i}", "x", i + 1, None, False, [])
             for i in range(6)]
    vol = {"id": "v1", "title": "卷一", "sort_order": 1,
           "charter": {"duty": "办", "chapter_range": [1, 10],
                       "introduces": [f"role:新{i}" for i in range(6)],
                       "pays": [],
                       "knowledge_end": {"must_know": ["母亲还活着"],
                                         "must_not_know": []}}}

    class _Store:
        def list_volumes(self):
            return [vol]

        def facts_at(self, ch):
            return [f for f in facts if f.valid_from <= ch]

        def load_knowledge(self):
            return []

        def list_promises(self):
            return []

    rep = Report()
    buf = io.StringIO()
    with redirect_stdout(buf):
        check_volumes(_Store(), rep, "role:新0", 10)
    out = buf.getvalue()
    assert "无法判定" in out and "契约无 key" in out
    assert not any("该知道" in t for t in rep.failed), rep.failed
    assert "✓ 卷末该知道的都知道了" not in out


def test_check_volumes_does_not_fail_first_volume_for_cross_payoffs():
    """卷1 契约写了 pays 也不该把「每卷收够了更早埋的线」打红。"""
    from scribe3.ontology import Fact
    from scribe3.tools.verify_scale import check_volumes

    facts = [Fact(f"fact:n{i}", f"role:新{i}", f"a{i}", "x", i + 1, None, False, [])
             for i in range(6)]
    vol = {"id": "v1", "title": "卷一", "sort_order": 1,
           "charter": {"duty": "办", "chapter_range": [1, 10],
                       "introduces": [f"role:新{i}" for i in range(6)],
                       "pays": ["种子线一", "种子线二"],
                       "knowledge_end": {"must_know": [], "must_not_know": []}}}

    class _Store:
        def list_volumes(self):
            return [vol]

        def facts_at(self, ch):
            return [f for f in facts if f.valid_from <= ch]

        def load_knowledge(self):
            return []

        def list_promises(self):
            return []

    rep = Report()
    check_volumes(_Store(), rep, "role:新0", 10)
    assert not any("收够" in t or "更早埋" in t for t in rep.failed), rep.failed


def test_check_depth_no_containment_is_reported_not_gated():
    """改前 8 个互不嵌套地点空间闸红。改后无从属只报不拦。"""
    import io
    from contextlib import redirect_stdout
    from scribe3.tools.verify_scale import check_depth

    facts = [_fact(f"p{i}", f"place:城{i}", "位置", "一句话", 1) for i in range(8)]
    hanging = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
    ]
    rep = Report()
    buf = io.StringIO()
    with redirect_stdout(buf):
        check_depth(_DepthStore(_vols(20, 40), hanging, facts=facts), rep, 40)
    out = buf.getvalue()
    assert "无从属数据、只报不拦" in out
    assert not any("一区一地点" in t for t in rep.failed), rep.failed


def test_check_depth_containment_gate_zero_then_one():
    """有从属才把关。11 地点只连一对 → 一区一地点 90% 红；多连几对则过。"""
    from scribe3.tools.verify_scale import check_depth

    hanging = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
    ]
    places = [_fact(f"p{i}", f"place:城{i}", "位置", "一句话", 1) for i in range(11)]
    one_edge = places + [_fact("loc", "place:城0", "位于", "place:城1", 1)]
    rep1 = Report()
    check_depth(_DepthStore(_vols(20, 40), hanging, facts=one_edge), rep1, 40)
    assert any("一区一地点" in t for t in rep1.failed), rep1.failed
    many = places + [
        _fact(f"loc{i}", f"place:城{i}", "位于", "place:城0", 1) for i in range(1, 11)
    ]
    rep0 = Report()
    check_depth(_DepthStore(_vols(20, 40), hanging, facts=many), rep0, 40)
    assert not any("一区一地点" in t for t in rep0.failed), rep0.failed


def test_check_depth_positive_control_top3_share():
    """均厚过线。往一个实体堆命题，前 3 闸必须红；≤2/≤4 不许跟着误红。"""
    from scribe3.tools.verify_scale import check_depth

    even = [_fact(f"e{i}_{j}", f"role:人{i}", f"a{j}", "x", j)
            for i in range(16) for j in range(8)]
    hanging = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
    ]
    rep0 = Report()
    check_depth(_DepthStore(_vols(20, 40), hanging, facts=even), rep0, 40)
    assert not any("前 3" in t for t in rep0.failed), rep0.failed
    piled = even + [_fact(f"pile{k}", "role:人0", f"p{k}", "x", k) for k in range(20)]
    rep1 = Report()
    check_depth(_DepthStore(_vols(20, 40), hanging, facts=piled), rep1, 40)
    assert not any("前 3" in t for t in rep1.failed), rep1.failed


def test_check_depth_positive_control_suspense_zero_then_one():
    """早卷都挂着过线。把卷 1 收掉，终卷前闸必须红；跨卷未收比例仍过。"""
    from scribe3.tools.verify_scale import check_depth

    hanging = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 4, "payoff_chapter": 8, "status": "closed"},
        {"setup_chapter": 25, "payoff_chapter": 30, "status": "closed"},
        {"setup_chapter": 45, "payoff_chapter": None, "status": "open"},
    ]
    vols = _vols(20, 40, 60)
    rep0 = Report()
    check_depth(_DepthStore(vols, hanging), rep0, 60)
    assert not any("跨卷未收" in t or "终卷前" in t for t in rep0.failed), rep0.failed
    paid_vol1 = [
        {"setup_chapter": 4, "payoff_chapter": 8, "status": "closed"},
        hanging[1], hanging[2], hanging[3], hanging[4],
    ]
    rep1 = Report()
    check_depth(_DepthStore(vols, paid_vol1), rep1, 60)
    assert not any("终卷前" in t for t in rep1.failed), rep1.failed


def test_unlaid_volumes_are_listed_not_failed():
    """半本书：卷 3-10 没铺，不能拿引入缺/新鲜度 0 记红。"""
    import io
    from contextlib import redirect_stdout
    from scribe3.ontology import Fact
    from scribe3.tools.verify_scale import check_volumes

    facts = [Fact(f"fact:n{i}", f"role:新{i}", f"a{i}", "x", i + 1, None, False, [])
             for i in range(6)]
    v1 = {"id": "v1", "title": "卷一", "sort_order": 1,
          "charter": {"duty": "办", "chapter_range": [1, 10],
                      "introduces": [f"role:新{i}" for i in range(6)],
                      "pays": [], "knowledge_end": {"must_know": [], "must_not_know": []}}}
    v2 = {"id": "v2", "title": "卷二", "sort_order": 2,
          "charter": {"duty": "办二", "chapter_range": [11, 20],
                      "introduces": [f"role:后{i}" for i in range(11)],
                      "pays": ["应收一条"],
                      "knowledge_end": {"must_know": [{"key": "壳裂口", "what": "x"}],
                                        "must_not_know": []}}}

    class _Store:
        def list_volumes(self):
            return [v1, v2]

        def facts_at(self, ch):
            return [f for f in facts if f.valid_from <= ch]

        def load_knowledge(self):
            return []

        def list_promises(self):
            return []

    rep = Report()
    buf = io.StringIO()
    with redirect_stdout(buf):
        check_volumes(_Store(), rep, "role:新0", 10)
    out = buf.getvalue()
    assert "未铺" in out and "卷二" in out
    assert not any("role:后" in t or "卷2" in t for t in rep.failed), (rep.failed, out)
    assert not any("该知道" in t for t in rep.failed), rep.failed


def test_suspense_does_not_use_unlaid_last_volume():
    """停在第 40 章时，卷 2 开口线不能算跨 8 卷，终卷前也不能红 8 卷。"""
    from scribe3.tools.verify_scale import check_depth

    hanging = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 31, "payoff_chapter": None, "status": "open"},
    ]
    # 十卷契约，只铺到 40。until=40 必须把终卷收成卷 2。
    vols = _vols(20, 40, 60, 80, 100, 120, 140, 160, 180, 200)
    rep = Report()
    check_depth(_DepthStore(vols, hanging), rep, 40)
    assert not any("终卷前" in t for t in rep.failed), rep.failed


def test_scale_ignores_chapters_past_laid():
    from scribe3.tools.verify_scale import check_scale

    syn = "这是一句足够长的章纲，用来证明已铺范围内的壳不是空的。还要再写几个字。"

    class _St:
        def chapters_lite(self):
            return [{"seq": i, "synopsis": syn} for i in range(1, 41)]

        def list_promises(self):
            return [{"status": "closed"} for _ in range(7)] + [{"status": "open"} for _ in range(3)]

    rep = Report()
    check_scale(_St(), rep, 200, 40)
    assert not any("无缺口" in t or "齐全" in t for t in rep.failed), rep.failed
    assert not any("收线率" in t for t in rep.failed), rep.failed


def test_early_payoff_fails_zero_then_one():
    from scribe3.tools.verify_scale import check_depth

    hanging = [
        {"id": "promise:ok", "setup_chapter": 4, "payoff_chapter": None,
         "status": "open", "tier": "arc", "payoff_min": 10, "payoff_max": 30},
    ]
    rep0 = Report()
    check_depth(_DepthStore(_vols(20, 40), hanging), rep0, 40)
    assert not any("早收" in t for t in rep0.failed), rep0.failed
    early = [{
        "id": "promise:early", "setup_chapter": 21, "payoff_chapter": 22,
        "status": "closed", "tier": "arc", "payoff_min": 26, "payoff_max": 36,
    }]
    rep1 = Report()
    check_depth(_DepthStore(_vols(20, 40), early), rep1, 40)
    assert any("早收" in t for t in rep1.failed), rep1.failed


def test_overdue_fails_zero_then_one():
    from scribe3.tools.verify_scale import check_depth

    hanging = [
        {"id": "promise:ok", "setup_chapter": 4, "payoff_chapter": None,
         "status": "open", "tier": "arc", "payoff_min": 10, "payoff_max": 80},
    ]
    rep0 = Report()
    check_depth(_DepthStore(_vols(20, 40), hanging), rep0, 40)
    assert not any("逾期" in t for t in rep0.failed), rep0.failed
    late = [{
        "id": "promise:late", "setup_chapter": 4, "payoff_chapter": None,
        "status": "open", "tier": "chapter", "payoff_min": 5, "payoff_max": 8,
    }]
    rep1 = Report()
    check_depth(_DepthStore(_vols(20, 40), late), rep1, 40)
    assert any("逾期" in t for t in rep1.failed), rep1.failed
