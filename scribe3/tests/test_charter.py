"""纲层契约：结构校验 + 与库对账。

这些用例钉的是 25 章实测撞出来的那堵墙——设定不长新东西。
判据全部可机器算，不含任何文笔类阈值。
"""

from __future__ import annotations

import json

import pytest

from scribe3.charter import (
    CharterError,
    audit_volume,
    build_charter_prompt,
    freshness,
    normalize_charter,
    parse_charters,
    persist_charters,
    validate_charter,
)
from scribe3.ontology import Fact, KnowledgeEdge


class FakeStore:
    """不带 `_query`，project_frame 会走 Python 边过滤路径。"""

    def __init__(self, facts, edges=(), promises=()):
        self._facts = list(facts)
        self._edges = list(edges)
        self._promises = list(promises)

    def facts_at(self, chapter):
        return [f for f in self._facts
                if f.valid_from <= chapter and (f.valid_to is None or f.valid_to > chapter)]

    def load_knowledge(self):
        return list(self._edges)

    def list_promises(self):
        return list(self._promises)

    def get_intent(self):
        return {"north_star": "北极星", "red_lines": "红线"}

    def __getattr__(self, name):
        # 立纲提示词要遍历一堆 list_xxx / characters()，这里一律给空。
        if name.startswith("list_") or name == "characters":
            return lambda *a, **k: []
        raise AttributeError(name)


def _fact(local, entity, attr, value, ch):
    return Fact(f"fact:{local}", entity, attr, value, ch, None, False, [])


# ---------- normalize / validate ----------

def test_normalize_accepts_json_string_and_bare_list():
    c = normalize_charter('{"duty":"办这件","introduces":["role:新人"],"pays":["旧线"]}')
    assert c["duty"] == "办这件"
    assert c["introduces"] == [{"oid": "role:新人", "why": ""}]
    assert c["pays"] == ["旧线"]
    assert c["knowledge_end"] == {"must_know": [], "must_not_know": []}
    assert c["thickens"] == []


def test_normalize_empty_and_bad_input():
    assert normalize_charter(None)["duty"] == ""
    assert normalize_charter("")["duty"] == ""
    with pytest.raises(CharterError):
        normalize_charter("{不是 json")
    with pytest.raises(CharterError):
        normalize_charter([1, 2, 3])


def _charter(**kw):
    # 6 章短卷：目标 3 + 余量 1 = 4。地板必须高于新鲜度目标。
    base = {"duty": "办这件",
            "introduces": ["role:甲", "role:乙", "org:丙", "place:渡口"],
            "thickens": ["role:老人", "place:旧镇", "org:旧会"],
            "pays": ["旧线"], "chapter_range": [1, 6],
            "knowledge_end": {
                "must_know": [{"key": "甲身份", "what": "知道甲是谁"}],
                "must_not_know": [{"key": "场核坐标", "what": "翻开得留到第三卷"}]}}
    base.update(kw)
    return base


def test_validate_flags_the_wall_we_hit():
    """引入太少要被拦——这正是 25 章打转的形态。"""
    problems = validate_charter(_charter(introduces=["role:甲"]))
    assert any("新实体" in p for p in problems)
    assert validate_charter(_charter()) == []


def test_required_introduces_scales_with_volume_length():
    """契约的地板必须和新鲜度判据同源，并且留出余量。

    真出过两件事：① 契约固定要 3 个、判据按每 10 章 5 个算，模型只点名三个；
    ② 地板正好等于目标（20 章点名 10 个）时，一个被前卷提前用掉就掉到 4.5。
    模型不会主动超过地板，所以地板必须高于目标。
    """
    from scribe3.charter import INTRODUCE_SLACK, MIN_NEW_ENTITIES_PER_10CH, required_introduces

    target_20 = round(20 / 10 * MIN_NEW_ENTITIES_PER_10CH)
    assert required_introduces(20) == target_20 + INTRODUCE_SLACK
    assert required_introduces(20) > target_20, "余量为零，提前占用就会掉线"
    assert required_introduces(10) == round(10 / 10 * MIN_NEW_ENTITIES_PER_10CH) + INTRODUCE_SLACK
    assert required_introduces(4) == 3, "短卷兜底 3 个，不能要 2 个"

    twenty = _charter(chapter_range=[1, 20])
    assert any("少于" in p and "新实体" in p for p in validate_charter(twenty))

    twenty["introduces"] = [f"role:人{i}" for i in range(required_introduces(20))]
    twenty["thickens"] = [f"role:旧{i}" for i in range(required_introduces(20))]
    assert validate_charter(twenty) == []


def test_validate_rejects_knowledge_without_key():
    """没有 key 就只能模糊匹配，那条路实测误报八条，立纲时就得拦。"""
    old_style = _charter(knowledge_end={
        "must_know": ["柳岸青知道忘川驿的清算名单包含那一夜"],
        "must_not_know": ["场核坐标"]})
    assert any("must_know" in p and "没给 key" in p for p in validate_charter(old_style))

    sentence_key = _charter(knowledge_end={
        "must_know": [{"key": "甲身份", "what": "知道甲"}],
        "must_not_know": [{"key": "柳岸青知道忘川驿的清算名单包含那一夜", "what": "留到后面"}]})
    assert any("太长" in p for p in validate_charter(sentence_key))


def test_generate_retries_with_the_problems_in_hand():
    """立纲不合格要带着问题清单退回重写，别让它一路落库到对账才炸。"""
    from scribe3.charter import generate_charters

    bad = json.dumps({"volumes": [dict(_charter(chapter_range=[1, 10]),
                                       sort_order=1, title="卷一",
                                       introduces=["role:甲"])]}, ensure_ascii=False)
    from scribe3.charter import required_introduces
    need = required_introduces(10)
    good = json.dumps({"volumes": [dict(_charter(chapter_range=[1, 10]), sort_order=1,
                                        title="卷一",
                                        introduces=[f"role:人{i}" for i in range(need)],
                                        thickens=[f"role:旧{i}" for i in range(need)])]},
                      ensure_ascii=False)
    seen: list[str] = []

    def complete(prompt: str) -> str:
        seen.append(prompt)
        return bad if len(seen) == 1 else good

    st = FakeStore([])
    charters, left = generate_charters(st, 1, 10, complete)
    assert left == [], "重写这一版是合格的"
    assert len(seen) == 2, "不合格必须重来一次"
    assert "新实体" in seen[1], "重写时得把问题告诉模型，否则它凭什么改"
    assert len(charters[0]["introduces"]) == need


def test_generate_gives_up_after_retries_but_still_reports():
    from scribe3.charter import generate_charters

    bad = json.dumps({"volumes": [dict(_charter(chapter_range=[1, 10]), sort_order=1,
                                       title="卷一", introduces=["role:甲"])]},
                     ensure_ascii=False)
    charters, left = generate_charters(FakeStore([]), 1, 10, lambda p: bad)
    assert charters and left, "改不好也要交出来，但问题得报上去"


def test_validate_requires_knowledge_end():
    problems = validate_charter({"duty": "办", "introduces": ["a", "b", "c"], "pays": ["线"]})
    assert any("知情终态" in p for p in problems)


# ---------- audit ----------

def _volume(charter):
    return {"id": "v1", "title": "卷一", "charter": charter}


def test_audit_catches_undeclared_stagnation():
    """声明引入三个新实体，实际一个没出现 —— 必须报出来。"""
    facts = [_fact(f"p{i}", "role:老人", f"attr{i}", "值", 11 + i) for i in range(10)]
    st = FakeStore(facts)
    vol = _volume({"duty": "办", "chapter_range": [11, 20],
                   "introduces": ["role:新甲", "role:新乙", "org:新丙"],
                   "pays": [], "knowledge_end": {}})
    a = audit_volume(st, vol, "role:老人")
    assert set(a.introduces_missing) == {"role:新甲", "role:新乙", "org:新丙"}
    assert a.new_entities_per_10ch == pytest.approx(1.0)
    assert not a.ok


def test_audit_passes_when_charter_is_honored():
    facts = ([_fact(f"n{i}", f"role:新{i}", f"a{i}", f"事{i}", 11 + i) for i in range(6)]
             + [_fact(f"m{i}", f"org:团{i}", f"b{i}", f"务{i}", 15 + i) for i in range(3)])
    promises = [{"text": "谁标的价", "resolution": "标价的人现身",
                 "setup_chapter": 4, "payoff_chapter": 18, "status": "paid"}]
    st = FakeStore(facts, promises=promises)
    vol = _volume({"duty": "办", "chapter_range": [11, 20],
                   "introduces": ["role:新0", "role:新1", "org:团0"],
                   "pays": ["谁标的价"], "knowledge_end": {}})
    a = audit_volume(st, vol, "role:新0")
    assert a.introduces_missing == []
    assert a.pays_short == 0
    assert a.new_entities_per_10ch >= 5.0


def test_introduces_missing_requires_exact_oid():
    """子串匹配会把短名算成长名已引入。必须精确相等。

    `place:门` 带前缀其实撞不上 `place:不署名门`；会误伤的是前缀关系：
    点名 `place:不署名`，库里只有 `place:不署名门`。
    """
    facts = [_fact("p", "place:不署名门", "位置", "在北峰", 11)]
    vol = _volume({"duty": "办", "chapter_range": [11, 20],
                   "introduces": ["place:不署名"], "pays": [], "knowledge_end": {}})
    a = audit_volume(FakeStore(facts), vol, "role:新0")
    assert a.introduces_missing == ["place:不署名"]


def test_introduces_missing_if_first_seen_before_this_volume():
    """点名实体必须在本卷首次出现。卷末「存在」不算引入。

    真误报：卷 2 点名 role:兰因，她第 13 章（卷 1）就出场了。
    旧判据查「到卷末存不存在」，报缺 0；真正的新实体只有 9 个，新鲜度 4.5。
    """
    # 兰因第 13 章已出场，卷 2 又立了一条——旧判据只看本卷有没有她，报缺 0。
    facts = ([_fact("early", "role:兰因", "身份", "早出场", 13),
              _fact("again", "role:兰因", "去向", "卷内又提一次", 25)]
             + [_fact(f"n{i}", f"role:新{i}", f"a{i}", f"事{i}", 21 + i) for i in range(9)])
    vol = _volume({"duty": "办", "chapter_range": [21, 40],
                   "introduces": ["role:兰因"] + [f"role:新{i}" for i in range(9)],
                   "pays": [], "knowledge_end": {}})
    a = audit_volume(FakeStore(facts), vol, "role:新0")
    assert "role:兰因" in a.introduces_missing, "前卷出场的不能算本卷引入"
    assert "role:新0" not in a.introduces_missing


def test_validate_charters_reject_oid_reserved_twice():
    """立纲时同一 oid 不许跨卷重名。一次性立完全书时，后卷预留的人会被前卷提前用掉。"""
    from scribe3.charter import validate_charters

    v1 = dict(_charter(chapter_range=[1, 20]), sort_order=1, title="卷一",
              introduces=[f"role:人{i}" for i in range(11)] + ["role:兰因"],
              thickens=[f"role:旧{i}" for i in range(11)])
    v2 = dict(_charter(chapter_range=[21, 40]), sort_order=2, title="卷二",
              introduces=[f"role:后{i}" for i in range(11)] + ["role:兰因"],
              thickens=[f"role:老{i}" for i in range(11)])
    problems = validate_charters([v1, v2])
    assert any("兰因" in p and "重名" in p for p in problems)

    v2["introduces"] = [f"role:后{i}" for i in range(12)]
    assert validate_charters([v1, v2]) == []


def test_audit_counts_payoffs_not_wording():
    """收线只数「收了几条更早埋的线」，不比文本。

    立纲发生在这些线存在之前，契约里的措辞必然和库里的 promise 对不上：
    实测十卷全报「说要收却没收」，而真实收线率 93%。判据错了不能怪书。
    """
    facts = [_fact(f"n{i}", f"role:新{i}", f"a{i}", f"事{i}", 11 + i) for i in range(6)]
    promises = [{"text": "库里的原话跟纲里写的完全两样", "setup_chapter": 4,
                 "payoff_chapter": 18, "status": "paid"}]
    vol = _volume({"duty": "办", "chapter_range": [11, 20],
                   "introduces": ["role:新0"], "pays": ["谁标的价"],
                   "knowledge_end": {}})
    a = audit_volume(FakeStore(facts, promises=promises), vol, "role:新0")
    assert a.cross_volume_payoffs == 1 and a.pays_short == 0, "措辞不同不该算没收"


def test_audit_reports_unpaid_line():
    facts = [_fact(f"n{i}", f"role:新{i}", f"a{i}", f"事{i}", 11 + i) for i in range(6)]
    promises = [{"text": "谁标的价", "setup_chapter": 4,
                 "payoff_chapter": None, "status": "open"}]
    st = FakeStore(facts, promises=promises)
    vol = _volume({"duty": "办", "chapter_range": [11, 20],
                   "introduces": ["role:新0"], "pays": ["谁标的价"],
                   "knowledge_end": {}})
    a = audit_volume(st, vol, "role:新0")
    assert a.pays_short == 1
    assert "只收掉 0 条" in a.report()


def test_first_volume_does_not_owe_cross_volume_payoffs():
    """第一卷没有更早的章，跨卷收线不该红。

    判据数的是 setup < 本卷起点。卷 1 起点是第 1 章，setup < 1 不可能，
    契约写了几条 pays 都会「差 N 条」——那是判据先天不可过，不是书没收线。
    """
    facts = [_fact(f"n{i}", f"role:新{i}", f"a{i}", f"事{i}", 1 + i) for i in range(6)]
    promises = [{"text": "种子线", "setup_chapter": 2,
                 "payoff_chapter": 8, "status": "paid"}]
    vol = _volume({"duty": "办", "chapter_range": [1, 10],
                   "introduces": ["role:新0"],
                   "pays": ["保护和监禁原来是同一件事", "金縢裂了"],
                   "knowledge_end": {}})
    a = audit_volume(FakeStore(facts, promises=promises), vol, "role:新0")
    assert a.pays_expected == 0, "没有更早的卷，不该按契约 pays 条数要跨卷收线"
    assert a.pays_short == 0
    assert a.cross_volume_payoffs == 0


def test_audit_ignores_lines_set_up_inside_the_volume():
    """卷内埋卷内收是小回环，不构成卷与卷之间的账。"""
    facts = [_fact(f"n{i}", f"role:新{i}", f"a{i}", f"事{i}", 11 + i) for i in range(6)]
    promises = [{"text": "本卷自埋自收", "setup_chapter": 12,
                 "payoff_chapter": 18, "status": "paid"}]
    vol = _volume({"duty": "办", "chapter_range": [11, 20],
                   "introduces": ["role:新0"], "pays": ["旧线"], "knowledge_end": {}})
    a = audit_volume(FakeStore(facts, promises=promises), vol, "role:新0")
    assert a.cross_volume_payoffs == 0 and a.pays_short == 1


def test_key_matches_where_wording_did_not():
    """同一件事、两种措辞，靠 key 对得上。

    实测的原样：契约要「记忆被改写后档案会留下空白，空白本身会被追索」，
    库里存的是「简篪没把北峰那一夜改写成赫斯掌纹的夜，只留下可被追索的档案空白」。
    实词重合三成，模糊匹配判成「卷末该知道却不知道」——十一条里八条是这么误报的。
    """
    f = _fact("k1", "role:主角", "档案空白",
              "简篪没把北峰那一夜改写成赫斯掌纹的夜，只留下可被追索的档案空白", 12)
    st = FakeStore([f], edges=[
        KnowledgeEdge("role:主角", "fact:k1", since_chapter=12, acquired_via="told")])
    ke = {"must_know": [{"key": "档案空白",
                         "what": "记忆被改写后档案会留下空白，空白本身会被追索"}]}
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [],
                   "pays": [], "knowledge_end": ke})
    assert audit_volume(st, vol, "role:主角").must_know_missing == []

    ke["must_know"][0]["key"] = "没写进去的属性"
    assert audit_volume(st, vol, "role:主角").must_know_missing != [], "真缺仍要报"


def test_key_red_line_ignores_narrative_negation():
    """红线按 key 比属性名，内容里的否定句不再喊破线。

    误报原样：主角有条命题叫「袖口标价」，内容是「……不能把场核坐标报给天龙座」。
    拿整条匹配「场核坐标」会命中，判成红线破了——可这句恰恰说明他不能报。
    """
    f = _fact("s1", "role:主角", "袖口标价", "他不能把场核坐标报给天龙座买办处", 12)
    st = FakeStore([f], edges=[
        KnowledgeEdge("role:主角", "fact:s1", since_chapter=12, acquired_via="told")])
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [], "pays": [],
                   "knowledge_end": {
                       "must_not_know": [{"key": "场核坐标", "what": "留到第三卷"}]}})
    a = audit_volume(st, vol, "role:主角")
    assert a.must_not_know_violated == [], "否定句不该算破线"
    assert a.must_not_know_suspect == ["留到第三卷"], "但要留个疑似，别把检出一起关掉"


def test_audit_catches_red_line_break():
    """红线第一次变成可自动检查的东西：说好主角看不见坐标，结果他知道了。"""
    coord = _fact("c1", "role:主角", "场核坐标", "坐标在华山北峰三指缝中心", 12)
    st = FakeStore([coord], edges=[
        KnowledgeEdge("role:主角", "fact:c1", since_chapter=12, acquired_via="saw")])
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [], "pays": [],
                   "knowledge_end": {"must_not_know": ["场核坐标"]}})
    a = audit_volume(st, vol, "role:主角")
    assert a.must_not_know_violated == ["场核坐标"]
    assert a.red_line_broken
    assert "红线" in a.report()


def test_audit_does_not_cry_wolf_on_negated_mention():
    """真实误报：主角有条「袖口标价」，内容写着「不能把场核坐标报给天龙座」。

    这句恰恰说明他不能报，却让十卷全部误报红线。属性名没撞上就不算破线，
    只记疑似——每卷都喊红线，人就不看了。
    """
    f = _fact("c1", "role:主角", "袖口标价",
              "三年前沈烛在袖口标开-3，让柳岸青不能把场核坐标报给天龙座", 12)
    st = FakeStore([f], edges=[
        KnowledgeEdge("role:主角", "fact:c1", since_chapter=12, acquired_via="told")])
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [], "pays": [],
                   "knowledge_end": {"must_not_know": ["场核坐标"]}})
    a = audit_volume(st, vol, "role:主角")
    assert a.must_not_know_violated == [], "属性名是「袖口标价」，不该判红线"
    assert a.must_not_know_suspect == ["场核坐标"]
    assert not a.red_line_broken
    assert "疑似" in a.report()


def test_audit_red_line_held_when_hero_kept_ignorant():
    """同一条事实存在，但主角没有知识边 —— 红线守住，不该误报。"""
    coord = _fact("c1", "role:配角", "场核坐标", "坐标在华山北峰三指缝中心", 12)
    st = FakeStore([coord], edges=[
        KnowledgeEdge("role:配角", "fact:c1", since_chapter=12, acquired_via="saw")])
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [], "pays": [],
                   "knowledge_end": {"must_not_know": ["场核坐标"]}})
    a = audit_volume(st, vol, "role:主角")
    assert a.must_not_know_violated == []
    assert not a.red_line_broken


def test_audit_reports_missing_must_know():
    st = FakeStore([_fact("x", "role:主角", "别的事", "无关", 12)])
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [], "pays": [],
                   "knowledge_end": {"must_know": [{"key": "母亲还活着", "what": "母亲还活着"}]}})
    a = audit_volume(st, vol, "role:主角")
    assert a.must_know_missing == ["母亲还活着"]


def test_must_know_without_key_is_undecidable():
    """旧契约全是人话、没有 key。模糊匹配误报率 8/11，这一项判不了。

    不算缺失，也不算过。报告里写无法判定。
    """
    st = FakeStore([_fact("x", "role:主角", "别的事", "无关", 12)])
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [], "pays": [],
                   "knowledge_end": {"must_know": ["母亲还活着"]}})
    a = audit_volume(st, vol, "role:主角")
    assert a.must_know_missing == []
    assert a.must_know_undecidable == ["母亲还活着"]
    assert "无法判定" in a.report() and "契约无 key" in a.report()


# ---------- freshness ----------

def test_freshness_reproduces_the_25_chapter_wall():
    """复刻实测形态：命题全堆在同一个实体上，卷内不长新东西。"""
    facts = [_fact(f"p{i}", "role:柳岸青", f"属性{i}", "袖口开-3 又扣了体温", 11 + i % 10)
             for i in range(30)]
    st = FakeStore(facts)
    fr = freshness(st, 11, 20)
    assert fr["new_entities_per_10ch"] == pytest.approx(1.0)


def test_freshness_healthy_volume():
    facts = [_fact(f"p{i}", f"role:人{i}", f"属性{i}", f"事{i}", 11 + i % 10)
             for i in range(20)]
    st = FakeStore(facts)
    fr = freshness(st, 11, 20)
    assert fr["new_entities_per_10ch"] >= 5.0


def test_keyword_share_is_reported_not_gated():
    """人写基线实测 62%、机器 50-70%，这个指标没有区分度，不许当门禁。

    《万界概率战争》校准：人写种子设定「自己」占 62%，模型段「柳岸」占 50-70%。
    主角名高频是长篇正常形态。这里钉住它只报告、不判定。
    """
    facts = [_fact(f"p{i}", f"role:人{i}", "属性", "柳岸青又一次按了裂口", 11 + i)
             for i in range(10)]
    st = FakeStore(facts)
    fr = freshness(st, 11, 20)
    assert fr["top_keyword_share"] > 0.9, "构造的就是高集中度数据"

    vol = _volume({"duty": "办", "chapter_range": [11, 20],
                   "introduces": [], "pays": [], "knowledge_end": {}})
    a = audit_volume(st, vol, "role:人0")
    assert a.top_keyword_share > 0.9
    assert a.ok, "集中度高不该导致不合格——它没有区分度"


def test_top_keyword_ignores_function_words():
    """虚词组不该盖过实词——「的」「了」这类切出来的 gram 要滤掉。"""
    facts = [_fact(f"p{i}", "role:甲", "属性", f"这是的了在{i}号渡口的事", 11)
             for i in range(10)]
    st = FakeStore(facts)
    fr = freshness(st, 11, 20)
    assert "的" not in fr["top_keyword"] and "了" not in fr["top_keyword"]


def test_freshness_excludes_prior_entities():
    """卷前就出现过的实体不算新。"""
    facts = ([_fact("old", "role:老人", "a", "早就有", 5)]
             + [_fact(f"n{i}", f"role:新{i}", f"a{i}", f"事{i}", 11 + i) for i in range(3)]
             + [_fact("again", "role:老人", "b", "又提一次", 12)])
    st = FakeStore(facts)
    fr = freshness(st, 11, 20)
    assert "role:老人" not in fr["new_entities"]
    assert len(fr["new_entities"]) == 3


# ---------- 生成侧：解析与落库 ----------

_RAW = """```json
{"volumes": [
  {"sort_order": 1, "title": "开场", "duty": "办第一件",
   "chapter_range": [1, 20], "introduces": [{"oid": "role:甲", "why": "要他"}],
   "pays": ["旧线一"], "knowledge_end": {"must_know": ["知道甲"], "must_not_know": ["真名"]}},
  {"sort_order": 2, "title": "转折", "duty": "办第二件",
   "chapter_range": [21, 40], "introduces": [{"oid": "place:渡口", "why": "要它"}],
   "pays": ["旧线二"], "knowledge_end": {"must_know": [], "must_not_know": ["真名"]}}
]}
```"""


class FakeVolStore:
    def __init__(self, volumes=()):
        self.volumes = [dict(v) for v in volumes]
        self.intent: dict = {}
        self._next = 100

    def list_volumes(self):
        return [dict(v) for v in self.volumes]

    def add_volume(self, title, sort_order=0, intro=""):
        self._next += 1
        vid = f"volume:{self._next}"
        self.volumes.append({"id": vid, "title": title,
                             "sort_order": sort_order, "intro": intro})
        return vid

    def update_volume(self, vid, patch):
        for v in self.volumes:
            if v["id"] == vid:
                v.update(patch)
                return
        raise KeyError(vid)

    def set_intent(self, patch):
        self.intent.update(patch)


def test_parse_charters_survives_fenced_json():
    """模型十次有三次会包代码块，解析不能因此炸。"""
    cs = parse_charters(_RAW)
    assert [c["sort_order"] for c in cs] == [1, 2]
    assert cs[0]["title"] == "开场"
    assert cs[0]["introduces"] == [{"oid": "role:甲", "why": "要他"}]
    assert cs[1]["chapter_range"] == [21, 40]


def test_parse_charters_rejects_non_json():
    with pytest.raises(CharterError):
        parse_charters("模型这次只回了一段道歉")


def test_persist_updates_existing_volume_instead_of_duplicating():
    """按 sort_order 认卷。重复建卷会让两卷抢同一段章号，生成时按章找卷就会找错。"""
    st = FakeVolStore([{"id": "volume:old", "title": "旧一卷",
                        "sort_order": 1, "intro": "旧的"}])
    r = persist_charters(st, parse_charters(_RAW), 40)

    assert r == {"volumes": 2, "new": 1, "updated": 1}
    assert len(st.volumes) == 2, "第 1 卷该被更新而不是再建一个"

    first = next(v for v in st.volumes if v["sort_order"] == 1)
    assert first["id"] == "volume:old"
    assert first["intro"] == "办第一件"
    assert first["charter"]["chapter_range"] == [1, 20]
    assert "sort_order" not in first["charter"], "契约体内不该混进卷字段"
    assert st.intent["book_charter"] == {"total_chapters": 40, "n_volumes": 2}


def test_sentence_shaped_forbid_does_not_cry_red_line():
    """契约把 must_not_know 写成句子时，不许输出高置信红线。

    匹配是双向的：属性名「清算名单」的实词全落在
    「柳岸青知道忘川驿的清算名单是否包含那一夜」里就算命中，
    于是任何沾边的设定都被判成越界——实测十卷里有六卷这么误报。
    输入不合格就把契约的毛病报回去，别报内容的错。
    """
    facts = [_fact("p1", "role:柳岸青", "清算名单", "名单上没有那一夜", 12)]
    st = FakeStore(facts, [KnowledgeEdge("role:柳岸青", "fact:p1", since_chapter=12)])
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [], "pays": [],
                   "knowledge_end": {
                       "must_not_know": ["柳岸青知道忘川驿的清算名单是否包含那一夜"]}})

    a = audit_volume(st, vol, "role:柳岸青")
    assert a.must_not_know_violated == [], "句子形态判不了，不许喊红线"
    assert a.must_not_know_unusable, "该把契约的毛病报出来"
    assert not a.red_line_broken


def test_short_forbid_still_catches_real_violation():
    """写成名字的仍要照抓——防误报不能把检出一起关掉。"""
    facts = [_fact("p1", "role:柳岸青", "场核坐标", "裂口三指缝中心", 12)]
    st = FakeStore(facts, [KnowledgeEdge("role:柳岸青", "fact:p1", since_chapter=12)])
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [], "pays": [],
                   "knowledge_end": {"must_not_know": ["场核坐标"]}})

    assert audit_volume(st, vol, "role:柳岸青").red_line_broken


def test_partly_overlapping_attribute_is_not_a_red_line():
    """属性名只沾一个词不算越界。

    真误报：属性名「坐标锁回」撞禁项「柳岸青看见场核坐标」，只中「坐标」就算过半，
    六卷全报红线。而那条命题写的是「双锁会不能借柳岸青开关位读取场核坐标」——
    说的恰恰是他读不到。
    """
    facts = [_fact("p1", "role:柳岸青", "坐标锁回",
                   "双锁会不能借柳岸青开关位读取场核坐标，只能读取断裂时的体温缺口", 12)]
    st = FakeStore(facts, [KnowledgeEdge("role:柳岸青", "fact:p1", since_chapter=12)])
    vol = _volume({"duty": "办", "chapter_range": [11, 20], "introduces": [], "pays": [],
                   "knowledge_end": {"must_not_know": ["场核坐标"]}})

    a = audit_volume(st, vol, "role:柳岸青")
    assert a.must_not_know_violated == [], "属性名缺「锁回」，不是同一件事"
    assert a.must_not_know_suspect, "内容里确实提到了，留给人看"


def test_single_word_attribute_is_only_a_suspect():
    """属性名只有一个词时判不了红线，降级为疑似。

    真误报：属性名就叫「坐标」，内容是「不署名门拒绝输出场核坐标」——他拿不到。
    """
    facts = [_fact("p1", "role:柳岸青", "坐标",
                   "不署名门拒绝输出场核坐标，任何坐标请求在门内变成地址空白", 190)]
    st = FakeStore(facts, [KnowledgeEdge("role:柳岸青", "fact:p1", since_chapter=190)])
    vol = _volume({"duty": "办", "chapter_range": [181, 200], "introduces": [], "pays": [],
                   "knowledge_end": {"must_not_know": ["场核坐标"]}})

    a = audit_volume(st, vol, "role:柳岸青")
    assert a.must_not_know_violated == [], "属性名「坐标」太泛，判不了"
    assert a.must_not_know_suspect, "内容提到了，交给人看"


def test_freshness_ignores_promise_bookkeeping():
    """伏笔账不算设定长出新东西——否则埋线越多分越高，指标就废了。

    `plant_promise` 每条线建一条 entity_id=promise:xxx 的命题，id 条条唯一。
    """
    facts = ([_fact(f"pr{i}", f"promise:{i:016x}", "伏笔", f"埋了{i}", 11 + i)
              for i in range(20)]
             + [_fact("real", "role:纪棠", "身份", "名讳司的人", 12)])
    st = FakeStore(facts)
    fr = freshness(st, 11, 20)

    assert fr["new_entities"] == ["role:纪棠"]
    assert fr["new_entities_per_10ch"] == 1.0, "20 条伏笔不该把新鲜度顶上去"

    vol = _volume({"duty": "办", "chapter_range": [11, 20],
                   "introduces": [], "pays": [], "knowledge_end": {}})
    assert audit_volume(st, vol, "role:纪棠").new_entities_per_10ch == 1.0


def test_prompt_names_used_entities_so_model_can_avoid_them():
    """提示词必须把已用实体喂回去，否则模型只会反复引入同一批人。"""
    st = FakeStore([_fact("p1", "role:柳岸青", "a", "v", 1)])
    st.get_intent = lambda: {"north_star": "北极星文", "red_lines": "红线文"}
    st.list_volumes = lambda: []
    st.list_world_rules = lambda: []
    st.characters = lambda: []
    st.list_factions = lambda: []

    p = build_charter_prompt(st, 10, 200)
    assert "role:柳岸青" in p
    assert "北极星文" in p and "红线文" in p
    assert "200" in p and "10 卷" in p
    assert "thickens" in p, "不写进契约模型就不会写厚已有实体"


def test_rolling_charter_prompt_sees_prior_volume_output():
    """后 N 卷立纲必须看见前面真长出了什么，不能只喂北极星。"""
    st = FakeStore([_fact("p1", "role:纪棠", "身份", "名讳司的人", 12)])
    st.get_intent = lambda: {"north_star": "北极星文", "red_lines": "红线文"}
    st.list_volumes = lambda: [{
        "id": "v1", "title": "开场", "sort_order": 1, "intro": "办完了",
        "charter": {"duty": "办完了", "chapter_range": [1, 20],
                    "introduces": [{"oid": "role:纪棠", "why": "要她"}],
                    "pays": [], "knowledge_end": {"must_know": [], "must_not_know": []}},
    }]
    st.list_world_rules = lambda: []
    st.characters = lambda: []
    st.list_factions = lambda: []
    p = build_charter_prompt(st, 2, 40, start_sort=2)
    assert "role:纪棠" in p
    assert "开场" in p
    assert "从第 2 卷" in p or "第2卷" in p or "sort_order\"： 2" in p or "只立后面" in p


def test_required_thickens_is_the_same_floor_as_introduces():
    """写厚数量必须和引入同源。契约是地板，没要的一点不给。"""
    from scribe3.charter import required_introduces, required_thickens

    assert required_thickens(20) == required_introduces(20)
    assert required_thickens(10) == required_introduces(10)
    assert required_thickens(4) == required_introduces(4)

    twenty = _charter(chapter_range=[1, 20], thickens=["role:老人"])
    twenty["introduces"] = [f"role:人{i}" for i in range(required_introduces(20))]
    assert any("写厚" in p or "thickens" in p for p in validate_charter(twenty))

    twenty["thickens"] = [f"role:旧{i}" for i in range(required_thickens(20))]
    assert validate_charter(twenty) == []


def test_normalize_thickens_like_introduces():
    c = normalize_charter({
        "duty": "办", "introduces": ["role:甲"],
        "thickens": ["role:柳岸青", {"oid": "loc:地球", "why": "北极星讲的就是它"}],
        "pays": ["线"],
    })
    assert c["thickens"][0]["oid"] == "role:柳岸青"
    assert c["thickens"][1]["oid"] == "place:地球", "loc 要归位，否则对账对不上"


def test_persist_keeps_thickens():
    raw = json.dumps({"volumes": [dict(_charter(chapter_range=[1, 6]),
                                       sort_order=1, title="开场",
                                       thickens=[{"oid": "role:柳岸青", "why": "主角还是空壳"}])]},
                     ensure_ascii=False)
    st = FakeVolStore()
    persist_charters(st, parse_charters(raw), 6)
    assert st.volumes[0]["charter"]["thickens"][0]["oid"] == "role:柳岸青"


def test_audit_reports_unthickened_named_entities():
    """点名写厚却还是空壳，必须报。用 duty 字段合同，不另发明一套。"""
    class Char:
        def __init__(self, name, traits):
            self.name, self.id, self.traits = name, f"role:{name}", traits

    facts = [_fact("p1", "role:新0", "a", "事", 11)]
    st = FakeStore(facts)
    st.characters = lambda: [Char("柳岸青", {})]
    vol = _volume({"duty": "办", "chapter_range": [11, 20],
                   "introduces": ["role:新0"], "thickens": ["role:柳岸青"],
                   "pays": [], "knowledge_end": {}})
    a = audit_volume(st, vol, "role:新0")
    assert "role:柳岸青" in a.thickens_missing
    assert not a.ok

    st.characters = lambda: [Char("柳岸青", {"surface_goal": "按回裂口", "fear": "被标成样本"})]
    a = audit_volume(st, vol, "role:新0")
    assert a.thickens_missing == []
