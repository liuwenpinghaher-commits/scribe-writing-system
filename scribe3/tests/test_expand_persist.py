"""章节落库的两道坎，都是实测撞出来的。

一、实体 id 归位。提示词写死了只许用 `role:`/`place:`/`org:`，模型仍零星写 `loc:`。
旧代码打一行警告就继续 `add_fact`，于是命题带着 `loc:`/`world:`/`hist:` 进了库——
能被新鲜度统计到、却永远关联不上实体，一致性检查和限知帧全都照不到。

二、隐瞒不能共用属性名。`facts_at` 末尾要过 `resolve_injection_facts` 做同键折叠
（注入面单真），36-100 章把所有隐瞒都写成 `attribute="隐瞒"`，结果写进 71 条、
读回来只剩 7 条——每个角色一条。
"""

from __future__ import annotations

import pytest

from scribe3.ontology import Fact
from scribe3.tools.expand_wanjie_chapters import canon_oid, hide_attr, resolve_payoff


@pytest.mark.parametrize("raw,want", [
    ("role:纪棠", "role:纪棠"),
    ("place:共鸣塔", "place:共鸣塔"),
    ("org:名讳司", "org:名讳司"),
    ("loc:忘川驿", "place:忘川驿"),
    ("location:渡口", "place:渡口"),
    ("char:柳岸青", "role:柳岸青"),
    ("person:沈烛", "role:沈烛"),
    ("faction:共签会", "org:共签会"),
    ("ROLE:纪棠", "role:纪棠"),
    ("  place: 共鸣塔  ", "place:共鸣塔"),
])
def test_known_prefixes_land_in_ontology(raw, want):
    assert canon_oid(raw) == want


def test_seed_oid_maps_world_and_hist_without_aliasing_canon():
    """种子显式映射。canon_oid 仍拒 world:/hist:，模型写了照样拦。"""
    from scribe3.ontology import canon_oid
    from scribe3.tools.seed_wanjie_scale import seed_oid

    assert seed_oid("loc:月球") == "place:月球"
    assert seed_oid("world:地球") == "place:地球"
    assert seed_oid("world:修仙界") == "place:修仙界"
    assert seed_oid("hist:周公") == "role:周公"
    assert seed_oid("role:柳岸青") == "role:柳岸青"
    assert canon_oid("world:地球") is None
    assert canon_oid("hist:周公") is None


@pytest.mark.parametrize("raw", [
    "", None, "没有冒号", "world:地球", "hist:开元之乱", "ev:某事", "fact:某条",
    "role:", "  :  ",
])
def test_unrecognized_is_refused_not_guessed(raw):
    """认不出就返回 None，由调用方整条跳过。

    `world:` / `hist:` 是上一轮真混进库的两个，这里钉死它们不许再被放行。
    `ev:` / `fact:` 在本体里另有其表，不是命题主语，同样不接。
    """
    assert canon_oid(raw) is None


def _hide(local, who, what, ch):
    return Fact(f"fact:{local}", who, hide_attr(what),
                f"对外人瞒：{what}", ch, None, True, [])


def test_one_person_can_hide_many_things():
    """同时瞒多件事必须都读得回来——这是限知模型的日常，不是边界情况。"""
    from scribe3.fact_surface import resolve_injection_facts

    facts = [_hide(f"h{i}", "role:沈烛", f"第{i}件事", 36 + i) for i in range(5)]
    assert len(resolve_injection_facts(facts)) == 5


def test_hiding_the_same_thing_twice_still_folds():
    """同一件事重复瞒该单真——折叠语义本身是对的，不能因为修 bug 把它一起关掉。"""
    from scribe3.fact_surface import resolve_injection_facts

    facts = [_hide("h1", "role:沈烛", "裂纹温度", 36),
             _hide("h2", "role:沈烛", "裂纹温度", 40)]
    out = resolve_injection_facts(facts)
    assert len(out) == 1
    assert out[0].valid_from == 40, "留下的该是后面那条"


def test_hide_attr_is_stable_and_bounded():
    assert hide_attr("裂纹温度") == hide_attr("  裂纹温度  ") == "隐瞒·裂纹温度"
    assert hide_attr("很长" * 40).startswith("隐瞒·")
    assert len(hide_attr("很长" * 40)) <= len("隐瞒·") + 24


# ---------- 收线：编号引用优先于模糊匹配 ----------

class PromiseStore:
    def __init__(self, rows):
        self._rows = rows

    def list_promises(self):
        return list(self._rows)


_LINES = [
    {"id": "promise:abc123", "text": "谁在袖口标的价", "status": "open"},
    {"id": "promise:def456", "text": "北峰那一夜谁按的核", "status": "open"},
    {"id": "promise:ghi789", "text": "已经收过的线", "status": "paid"},
]


def test_payoff_resolves_by_reference():
    """提示词把编号发下去，收线就是精确引用，不看模型复述得准不准。"""
    st = PromiseStore(_LINES)
    assert resolve_payoff(st, {"ref": "Labc123"}) == "abc123"
    assert resolve_payoff(st, {"ref": "labc123"}) == "abc123", "大小写不该卡住"


def test_reference_wins_over_misleading_text():
    """编号在就认编号。模型抄错原话是常事，编号抄错少见。"""
    st = PromiseStore(_LINES)
    got = resolve_payoff(st, {"ref": "Ldef456", "text": "谁在袖口标的价"})
    assert got == "def456"


def test_falls_back_to_text_when_no_reference():
    st = PromiseStore(_LINES)
    assert resolve_payoff(st, {"text": "北峰那一夜谁按的核"}) == "def456"


def test_will_not_pay_a_line_that_is_already_closed():
    st = PromiseStore(_LINES)
    assert resolve_payoff(st, {"ref": "Lghi789"}) is None
    assert resolve_payoff(st, {"ref": "L不存在"}) is None


def test_chapter_prompt_lists_later_volume_reservations():
    """后卷预留的实体现在不许用。一次性立完全书时，铺前卷会把后卷的人提前引入。

    实测：卷 2 预留了 role:兰因，铺卷 1 时第 13 章就把她用了，卷 2 新鲜度掉到 4.5。
    章级提示已经发「已经登场过的」，没发「后面预留的」。选这条路而不是立纲查重名，
    因为重名检查拦不住「契约没点名、生成时自己提前用」。
    """
    from scribe3.tools.expand_wanjie_chapters import build_prompt

    class St:
        def get_intent(self):
            return {"north_star": "北极星", "red_lines": "红线"}

        def list_volumes(self):
            return [
                {"id": "v1", "title": "卷一", "intro": "办一",
                 "charter": {"duty": "办一", "chapter_range": [1, 20],
                             "introduces": [{"oid": "role:甲", "why": "要他"}],
                             "pays": [], "knowledge_end": {"must_know": [], "must_not_know": []}}},
                {"id": "v2", "title": "卷二", "intro": "办二",
                 "charter": {"duty": "办二", "chapter_range": [21, 40],
                             "introduces": [{"oid": "role:兰因", "why": "第二卷才出场"}],
                             "pays": [], "knowledge_end": {"must_know": [], "must_not_know": []}}},
            ]

        def chapters_lite(self):
            return []

        def list_promises(self):
            return []

        def facts_at(self, *_a, **_k):
            return []

        def characters(self):
            return []

        def list_world_rules(self):
            return []

        def list_factions(self):
            return []

        def list_items(self):
            return []

        def list_terms(self):
            return []

        def list_motifs(self):
            return []

    p = build_prompt(St(), "卷一", "办一", 11, 20, 40)
    assert "role:兰因" in p
    assert "现在别用" in p or "预留" in p


def test_chapter_prompt_lists_thickens():
    from scribe3.tools.expand_wanjie_chapters import build_prompt

    class St:
        def get_intent(self):
            return {"north_star": "星", "red_lines": "线"}

        def list_volumes(self):
            return [{"id": "v1", "title": "卷一", "intro": "办",
                     "charter": {"duty": "办", "chapter_range": [1, 20],
                                 "introduces": [{"oid": "role:甲", "why": "要"}],
                                 "thickens": [{"oid": "org:天龙座", "why": "反派还是空壳"}],
                                 "pays": [], "knowledge_end": {"must_know": [], "must_not_know": []}}}]

        def chapters_lite(self):
            return []

        def list_promises(self):
            return []

        def facts_at(self, *_a, **_k):
            return []

        def characters(self):
            return []

        def list_world_rules(self):
            return []

        def list_factions(self):
            return []

        def list_items(self):
            return []

        def list_terms(self):
            return []

        def list_motifs(self):
            return []

    p = build_prompt(St(), "卷一", "办", 11, 20, 20)
    assert "org:天龙座" in p
    assert "写厚" in p or "thickens" in p


def test_introduce_quota_splits_evenly_last_batch_takes_rest():
    from scribe3.tools.expand_wanjie_chapters import introduce_quota, remaining_batches

    assert remaining_batches(40, 21, 10) == 2
    assert remaining_batches(40, 31, 10) == 1
    assert introduce_quota(11, 2) == 5
    assert introduce_quota(6, 1) == 6
    assert introduce_quota(0, 2) == 0


def test_chapter_prompt_holds_later_batch_introduces():
    """点名 11 个不能全塞进前半批。本批 5，其余留给后批。"""
    from scribe3.ontology import Fact
    from scribe3.tools.expand_wanjie_chapters import build_prompt

    oids = [f"role:人{i}" for i in range(11)]

    class St:
        def get_intent(self):
            return {"north_star": "星", "red_lines": "线"}

        def list_volumes(self):
            return [{"id": "v2", "title": "卷二", "intro": "办",
                     "charter": {"duty": "办", "chapter_range": [21, 40],
                                 "introduces": [{"oid": o, "why": "要"} for o in oids],
                                 "pays": [], "knowledge_end": {"must_know": [], "must_not_know": []}}}]

        def chapters_lite(self):
            return []

        def list_promises(self):
            return []

        def facts_at(self, ch, *_a, **_k):
            if ch < 21:
                return []
            return [Fact(f"fact:{i}", oids[i], "面目", "已出场", 21, None, False, [])
                    for i in range(5)] if ch >= 21 else []

        def characters(self):
            return []

        def list_world_rules(self):
            return []

        def list_factions(self):
            return []

        def list_items(self):
            return []

        def list_terms(self):
            return []

        def list_motifs(self):
            return []

    first = build_prompt(St(), "卷二", "办", 21, 30, 200)
    assert "本批必须引入这 5 个" in first
    assert "role:人0" in first and "role:人4" in first
    assert "留给后面几批" in first
    assert "role:人5" in first and "role:人10" in first
    # 后半批：前 5 已出场，剩下 6 个本批收干净
    second = build_prompt(St(), "卷二", "办", 31, 40, 200)
    assert "本批必须引入这 6 个" in second
    assert "role:人5" in second and "role:人10" in second
    assert "**本卷还欠着、留给后面几批**" not in second


def test_thicken_named_entities_uses_codex_contract():
    """铺章末尾写厚走 thicken_codex，不另发明字段。"""
    from scribe3.tools.expand_wanjie_chapters import thicken_named_entities

    called = []

    class Char:
        def __init__(self, name):
            self.name, self.id, self.traits = name, f"role:{name}", {}

    class St:
        def characters(self):
            return [Char("柳岸青")]

        def list_factions(self):
            return [{"name": "天龙座"}]

        def list_world_rules(self):
            return []

        def list_items(self):
            return []

        def list_terms(self):
            return []

        def list_motifs(self):
            return []

        def list_voice_profiles(self):
            return []

        def facts_at(self, *_a, **_k):
            return []

        def entity_relations_at(self, *_a, **_k):
            return []

        def exists(self, oid):
            return True

        def update_record(self, oid, fields):
            called.append((oid, fields))
            return True

        def get_faction(self, n):
            return {"name": n} if n == "天龙座" else None

        def add_faction(self, n, **fields):
            called.append((n, fields))

    vol = {"charter": {
        "introduces": [{"oid": "role:新人", "why": ""}],
        "thickens": [{"oid": "role:柳岸青", "why": "主角空壳"},
                     {"oid": "org:天龙座", "why": "反派空壳"}],
    }}

    def llm(prompt, max_tokens=4096):
        if "不要填表" in prompt or "是谁" in prompt:
            return "柳岸青要把场核按回裂口。他会让世界认走心跳。"
        if "他要什么" in prompt:
            return "他要什么：把场核按回裂口\n他让人付出什么：世界认走心跳"
        if "势力" in prompt or "天龙座" in prompt:
            return "天龙座要主角交出坐标。公开互助，私下买办。"
        return '{"ideology": "买办坐标", "public_face": "互助", "recruitment": "标价进门", "leader": "赫斯", "goals": [{"target": "买坐标"}]}'

    out = thicken_named_entities(St(), vol, llm_fn=llm)
    names = {i.get("name") for i in out.get("items") or []}
    assert "柳岸青" in names or any("柳岸青" in str(c) for c in called)
    assert "天龙座" in names or any("天龙座" in str(c) for c in called)


def test_hero_knows_ranks_charter_keys_before_arbitrary_head():
    """第 200 章主角知道上百条时，前 25 条必须是这一卷用得上的，不是任意切片。"""
    from scribe3.ontology import Fact
    from scribe3.tools.expand_wanjie_chapters import rank_known_facts

    facts = [Fact(f"fact:{i}", "role:路人", f"杂{i}", f"无关{i}", i, None, False, [])
             for i in range(40)]
    facts.append(Fact("fact:k", "place:月球", "场核坐标",
                      "裂口在北峰", 12, None, False, []))
    ranked = rank_known_facts(facts, keys={"场核坐标"}, oids={"place:月球"}, cap=5)
    assert ranked[0].attribute == "场核坐标"


def test_expand_volume_accounts_persists_parsed_chapters():
    """产品路径铺章必须真写 synopsis，不能只返回章号列表。"""
    from scribe3.tools.expand_wanjie_chapters import expand_volume_accounts

    class St:
        def __init__(self):
            self.chapters = {}
            self.meta = {}
            self.facts = []

        def get_intent(self):
            return {"north_star": "星", "red_lines": "线"}

        def list_volumes(self):
            return [self.vol]

        def chapters_lite(self):
            return [{"seq": s, "title": c.get("title"), "synopsis": self.meta.get(s, {}).get("synopsis", "")}
                    for s, c in self.chapters.items()]

        def list_promises(self):
            return []

        def facts_at(self, *_a, **_k):
            return list(self.facts)

        def characters(self):
            return []

        def list_world_rules(self):
            return []

        def list_factions(self):
            return []

        def list_items(self):
            return []

        def list_terms(self):
            return []

        def list_motifs(self):
            return []

        def save_chapter(self, seq, prose, title="", focalizer=""):
            self.chapters[seq] = {"title": title, "prose": prose}

        def update_chapter_meta(self, seq, meta):
            self.meta[seq] = dict(meta)
            return True

        def entity(self, oid):
            return True

        def add_entity(self, *a, **k):
            return None

        def add_fact(self, fact, **k):
            self.facts.append(fact)

        def add_knowledge(self, *a, **k):
            return None

        def plant_promise(self, *a, **k):
            return None

        def advance_promise(self, *a, **k):
            return None

    st = St()
    st.vol = {"id": "v1", "title": "卷一", "intro": "办",
              "charter": {"duty": "办", "chapter_range": [11, 12],
                          "introduces": [{"oid": "role:甲", "why": "要"}],
                          "pays": [], "knowledge_end": {"must_know": [], "must_not_know": []}}}

    def llm(prompt, max_tokens=4096):
        return '''[
          {"seq": 11, "title": "第一笔", "synopsis": "甲在渡口被挡住，付了体温才过。",
           "new_facts": [{"entity": "role:甲", "attribute": "过河", "value": "付了体温", "secret": false}],
           "learns": [], "hides": [{"who": "role:甲", "from": "role:乙", "what": "体温缺口"}],
           "plant": [], "payoff": []},
          {"seq": 12, "title": "第二笔", "synopsis": "甲发现名单缺了一夜。",
           "new_facts": [{"entity": "role:甲", "attribute": "名单", "value": "缺了一夜", "secret": false}],
           "learns": [], "hides": [{"who": "role:甲", "from": "role:乙", "what": "缺名"}],
           "plant": [], "payoff": []}
        ]'''

    out = expand_volume_accounts(st, st.vol, llm_fn=llm, total=20, batch=10)
    assert st.meta[11]["synopsis"].startswith("甲在渡口")
    assert st.meta[12]["synopsis"].startswith("甲发现")
    assert out.get("chapters") == 2 or len(out.get("batches") or []) >= 1
    assert "thicken" in out
    assert all("thicken" not in b for b in out.get("batches") or [])


def test_pick_thickens_prefers_thin_and_skips_headliners():
    """开铺前重排：长尾已出场优先；柳岸青在前卷点过就不再占名额。"""
    from scribe3.ontology import Fact
    from scribe3.tools.expand_wanjie_chapters import pick_thickens

    facts = [
        Fact("fact:h1", "role:柳岸青", "a", "厚", 1, None, False, []),
        Fact("fact:h2", "role:柳岸青", "b", "更厚", 2, None, False, []),
        Fact("fact:h3", "role:柳岸青", "c", "还厚", 3, None, False, []),
        Fact("fact:t1", "role:验温嫂", "面目", "一句话", 13, None, False, []),
        Fact("fact:t2", "place:无名井", "位置", "一口井", 20, None, False, []),
        Fact("fact:n1", "role:新人", "面目", "本卷才点名", 50, None, False, []),
    ]

    class St:
        def facts_at(self, ch):
            return [f for f in facts if f.valid_from <= ch]

        def list_volumes(self):
            return [{"id": "v1", "charter": {"chapter_range": [1, 20],
                      "thickens": [{"oid": "role:柳岸青", "why": "主角"}]}}]

    vol = {"id": "v4", "charter": {"chapter_range": [61, 80],
                                   "introduces": [{"oid": "role:新人", "why": "本卷点名"}],
                                   "thickens": [{"oid": "role:柳岸青", "why": "立纲钉死"}]}}
    got = pick_thickens(St(), vol, 2)
    oids = [i["oid"] for i in got]
    assert "role:柳岸青" not in oids
    assert "role:新人" not in oids
    assert "role:验温嫂" in oids
    assert "place:无名井" in oids


def test_ensure_live_roster_skips_volume_one():
    from scribe3.tools.expand_wanjie_chapters import ensure_live_roster

    vol = {"id": "v1", "charter": {"duty": "办", "chapter_range": [1, 20],
                                   "thickens": [{"oid": "role:柳岸青", "why": "种子"}]}}
    c = ensure_live_roster(type("S", (), {"facts_at": lambda *_a, **_k: [],
                                           "list_volumes": lambda *_a, **_k: [],
                                           "list_promises": lambda *_a, **_k: []})(), vol)
    assert c["thickens"][0]["oid"] == "role:柳岸青"


def test_prompt_lists_holdovers_as_must_not_pay():
    from scribe3.tools.expand_wanjie_chapters import build_prompt

    class St:
        def get_intent(self):
            return {"north_star": "星", "red_lines": "线"}

        def list_volumes(self):
            return [{"id": "v4", "title": "卷四", "intro": "办",
                     "charter": {"duty": "办", "chapter_range": [61, 80],
                                 "introduces": [{"oid": "role:甲", "why": "要"}],
                                 "thickens": [],
                                 "holdovers": [{"ref": "Labc", "text": "旧欠温"}],
                                 "pays": ["该收的线"],
                                 "knowledge_end": {"must_know": [], "must_not_know": []}}}]

        def chapters_lite(self):
            return []

        def list_promises(self):
            return []

        def facts_at(self, *_a, **_k):
            return []

        def characters(self):
            return []

        def list_world_rules(self):
            return []

        def list_factions(self):
            return []

        def list_items(self):
            return []

        def list_terms(self):
            return []

        def list_motifs(self):
            return []

    p = build_prompt(St(), "卷四", "办", 61, 70, 200)
    assert "本卷不许收" in p and "Labc" in p
    assert "本卷该收" in p


def test_persist_skips_holdover_payoff():
    from scribe3.tools.expand_wanjie_chapters import persist

    paid = []

    class St:
        def list_volumes(self):
            return [{"id": "v4", "charter": {"holdovers": [{"ref": "Labc123", "text": "长线"}]}}]

        def list_promises(self):
            return [{"id": "promise:abc123", "text": "长线", "status": "open",
                     "setup_chapter": 4}]

        def save_chapter(self, *a, **k):
            return None

        def update_chapter_meta(self, *a, **k):
            return True

        def add_fact(self, *a, **k):
            return None

        def add_knowledge(self, *a, **k):
            return None

        def plant_promise(self, *a, **k):
            return None

        def advance_promise(self, pid, seq):
            paid.append((pid, seq))

        def entity(self, oid):
            return True

        def add_entity(self, *a, **k):
            return None

        def add_faction(self, *a, **k):
            return None

    persist(St(), [{
        "seq": 61, "title": "试", "synopsis": "x" * 40,
        "new_facts": [], "learns": [], "hides": [], "plant": [],
        "payoff": [{"ref": "Labc123", "how": "不该收"}],
    }], "v4")
    assert paid == []
