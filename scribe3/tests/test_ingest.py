"""S7⑤ · 章节回写 ingest —— 闭合写循环(对话写作→存→回写→下章限知反映新知)。

apply_delta 纯应用(不连网);ingest_chapter 走注入的 complete_fn。
P18: apply_delta 要求角色已存在(不再自动建,防幻觉角色污染)。
"""
from scribe3.ingest import apply_delta, ingest_chapter
from scribe3.knowledge import project_frame
from scribe3.ontology import Entity


def _ensure_chars(store, *names):
    for n in names:
        oid = f"role:{n}"
        if store.entity(oid) is None:
            store.add_entity(Entity(oid, "character", n))


def test_learned_makes_knower_know(store):
    _ensure_chars(store, "焦三")
    apply_delta(store, {"learned": [{"who": "焦三", "fact": "老道是流云观追索者"}], "did": []}, seq=3)
    fr = project_frame(store, "role:焦三", 3)
    assert any("追索者" in f.value for f in fr.facts), "焦三第3章起知道"


def test_did_witnesses_know(store):
    _ensure_chars(store, "焦三", "阿萤")
    apply_delta(store, {"learned": [], "did": [{"who": "焦三", "action": "取出尸丹", "seen_by": ["阿萤"]}]}, seq=2)
    assert any("尸丹" in f.value for f in project_frame(store, "role:焦三", 2).facts), "当事人知道"
    assert any("尸丹" in f.value for f in project_frame(store, "role:阿萤", 2).facts), "在场者也知道"


def test_non_witness_does_not_know(store):
    _ensure_chars(store, "焦三", "老道")
    apply_delta(store, {"learned": [], "did": [{"who": "焦三", "action": "取出尸丹", "seen_by": []}]}, seq=2)
    assert not project_frame(store, "role:老道", 2).knows("fact:d2-0"), "不在场者不知"


def test_ingest_chapter_end_to_end(store):
    _ensure_chars(store, "焦三")
    store.save_chapter(1, "焦三在乱岗取出尸丹。", focalizer="role:焦三")
    fake = lambda _p: '{"learned":[{"who":"焦三","fact":"尸丹能聚魂"}],"did":[]}'
    r = ingest_chapter(store, 1, fake)
    assert r["applied"] == 1
    assert any("聚魂" in f.value for f in project_frame(store, "role:焦三", 1).facts)


def test_apply_delta_writes_voice_flag(store):
    _ensure_chars(store, "焦三")
    from scribe3.ingest import apply_delta
    delta = {"learned": [], "did": [],
             "voice_shift": [{"who": "焦三", "reason": "被师父背叛"}]}
    apply_delta(store, delta, 10)
    flags = store.list_voice_flags("open")
    assert any(f["character"] == "焦三" and f["trigger_chapter"] == 10 for f in flags)


# ── P0 数据丢失修复测试 ────────────────────────────────────────────────────────

def test_parse_knowledge_delta_signals_failure_on_garbage():
    from scribe3.critique import parse_knowledge_delta
    # 坏 JSON / 截断 → 返回失败信号(None),而非静默空 delta
    assert parse_knowledge_delta("这不是JSON{截断") is None


def test_parse_knowledge_delta_ok_empty():
    from scribe3.critique import parse_knowledge_delta
    d = parse_knowledge_delta('{"learned":[],"did":[],"voice_shift":[]}')
    # arc 是可选新字段(旧 JSON 不含时默认空列表);核心三字段必须存在
    assert d is not None
    assert d["learned"] == []
    assert d["did"] == []
    assert d["voice_shift"] == []
    assert d.get("arc", []) == []  # 向后兼容:旧响应无 arc 时也返回空列表


def test_ingest_chapter_parse_fail_does_not_purge(store):
    from scribe3.ingest import ingest_chapter
    from scribe3.ontology import Fact
    # 先种一条本章既有 ingest 命题
    _ensure_chars(store, "甲")
    store.save_chapter(5, "正文内容五", focalizer=None)
    store.add_fact(Fact("fact:k5-0", "role:甲", "获知", "旧知识", valid_from=5), ingest_seq=5)
    # complete_fn 返回坏 JSON → 解析失败
    r = ingest_chapter(store, 5, lambda *a, **k: "坏的不是JSON{")
    assert r.get("parse_failed") is True
    # 既有 ingest 命题未被删
    facts = store.facts_at(5)
    assert any(f.id == "fact:fact:k5-0" or "k5-0" in f.id for f in facts), \
        "解析失败不应 purge 既有知识"


def test_ingest_chapter_ok_empty_still_purges(store):
    from scribe3.ingest import ingest_chapter
    from scribe3.ontology import Fact
    _ensure_chars(store, "乙")
    store.save_chapter(6, "正文六", focalizer=None)
    store.add_fact(Fact("fact:k6-0", "role:乙", "获知", "将被清", valid_from=6), ingest_seq=6)
    r = ingest_chapter(store, 6, lambda *a, **k: '{"learned":[],"did":[],"voice_shift":[]}')
    assert r.get("parse_failed") is not True
    assert r["applied"] == 0
    # 合法空 delta 仍幂等 purge+重写 → 旧的被清
    facts = store.facts_at(6)
    assert not any("k6-0" in f.id for f in facts), "合法空 delta 应 purge 旧 ingest 命题"


# ── P2-E1 reader_knows 自动回写测试 ──────────────────────────────────────────

def test_ingest_auto_records_reader_knows(store):
    """ingest 一章后,该章的命题应出现在 reader 帧里(叙述揭示即读者已知)。"""
    _ensure_chars(store, "焦三")
    store.save_chapter(4, "焦三发现老道持有尸丹。", focalizer="role:焦三")
    fake = lambda _p: '{"learned":[{"who":"焦三","fact":"老道持有尸丹"}],"did":[],"voice_shift":[]}'
    r = ingest_chapter(store, 4, fake)
    assert r["applied"] == 1, "ingest 应写入 1 条命题"

    # reader 帧应包含该命题
    from scribe3.knowledge import project_frame, dramatic_irony
    reader_frame = project_frame(store, "reader", 4)
    assert any("尸丹" in f.value for f in reader_frame.facts), \
        "ingest 后 reader 帧应含被 ingest 的 fact"


def test_ingest_reader_knows_did_facts(store):
    """did 类事件(行动)同样应写入 reader_knows。"""
    _ensure_chars(store, "焦三", "阿萤")
    store.save_chapter(5, "焦三在阿萤面前取出尸丹。", focalizer="role:焦三")
    fake = lambda _p: ('{"learned":[],'
                       '"did":[{"who":"焦三","action":"取出尸丹","seen_by":["阿萤"]}],'
                       '"voice_shift":[]}')
    r = ingest_chapter(store, 5, fake)
    assert r["applied"] == 1

    from scribe3.knowledge import project_frame
    reader_frame = project_frame(store, "reader", 5)
    assert any("尸丹" in f.value for f in reader_frame.facts), \
        "did 类 fact 也应出现在 reader 帧"


def test_ingest_reader_knows_idempotent(store):
    """同一章 ingest 两次,reader_knows 边不重复叠加。"""
    _ensure_chars(store, "焦三")
    store.save_chapter(7, "焦三知道了秘密。", focalizer="role:焦三")
    fake = lambda _p: '{"learned":[{"who":"焦三","fact":"秘密内容"}],"did":[],"voice_shift":[]}'

    ingest_chapter(store, 7, fake)
    ingest_chapter(store, 7, fake)  # 第二次 ingest 同一章

    # reader 帧里该命题只出现一次(不重复)
    from scribe3.knowledge import project_frame
    reader_frame = project_frame(store, "reader", 7)
    matching = [f for f in reader_frame.facts if "秘密" in f.value]
    assert len(matching) == 1, \
        f"同章二次 ingest 后 reader_knows 应只有 1 条,实际 {len(matching)} 条"


def test_dramatic_irony_uses_reader_knows(store):
    """戏剧反讽:reader 知道、焦三不知道 → dramatic_irony 能检出。"""
    _ensure_chars(store, "焦三", "阿萤")
    store.save_chapter(8, "叙述者(全知)揭示阿萤是奸细。", focalizer="role:焦三")
    # 只让 reader 知道"阿萤是奸细",焦三未获任何 learned 边
    fake = lambda _p: ('{"learned":[{"who":"阿萤","fact":"阿萤是奸细"}],'
                       '"did":[],"voice_shift":[]}')
    ingest_chapter(store, 8, fake)

    from scribe3.knowledge import dramatic_irony
    irony = dramatic_irony(store, "role:焦三", 8)
    assert any("奸细" in f.value for f in irony), \
        "reader 已知阿萤是奸细,焦三不知 → 应出现在戏剧反讽列表"


# ── P2-E3 accept_unverified 回放 ingest 回填被阻塞的知识 ──────────────────────

def test_accept_unverified_replays_chapter(store):
    """P2-E3: accept_unverified 应重放该章 ingest,回填因角色不存在而被跳过的知识边。

    流程:
    1) 存一章正文,其中有"无名客"的 learned 和 did 项
    2) ingest 时 role:无名客 不存在 → _resolve_char 返回 None,知识边被跳过,
       同时 add_unverified_ref 登记一条 pending 行
    3) accept_unverified(uid, complete_fn=fake) → 建角色 + 重放 ingest →
       role:无名客 的 fact/knows 边现在存在
    """
    # 存章节(无名客 在场,另有已知角色焦三作对照)
    store.save_chapter(9, "无名客在乱岗拾得尸丹。", focalizer=None)

    # 首次 ingest: role:无名客 不存在 → 知识被跳过
    fake_llm = lambda _p: ('{"learned":[{"who":"无名客","fact":"尸丹能聚魂"}],'
                           '"did":[{"who":"无名客","action":"拾得尸丹","seen_by":[]}],'
                           '"voice_shift":[]}')
    r1 = ingest_chapter(store, 9, fake_llm)
    # applied==0:两条都因角色不存在而跳过
    assert r1["applied"] == 0, f"首次 ingest 应全部跳过,实际 applied={r1['applied']}"

    # 此时应有一条 pending 记录
    pending = store.list_unverified("pending")
    wm_pending = [p for p in pending if p["name"] == "无名客" and p["seq"] == 9]
    assert wm_pending, "ingest 应登记无名客的 pending 待确认行"
    uid = wm_pending[0]["id"]

    # accept_unverified 传入 fake_llm 触发重放
    result = store.accept_unverified(uid, complete_fn=fake_llm)
    assert result["created"] is True, "应建 role:无名客 实体"
    assert result["replayed"] is True, "应回放 ingest"

    # 验证知识边已回填
    fr = project_frame(store, "role:无名客", 9)
    values = [f.value for f in fr.facts]
    assert any("聚魂" in v for v in values), \
        f"learned 知识应回填到无名客,实际 facts={values}"
    assert any("尸丹" in v for v in values), \
        f"did 行动应回填到无名客,实际 facts={values}"


def test_accept_unverified_no_complete_fn_skips_replay(store):
    """没有 complete_fn 时,accept 仍建角色,replayed=False,不抛异常。"""
    store.save_chapter(10, "神秘人出现。", focalizer=None)
    fake_llm = lambda _p: '{"learned":[{"who":"神秘人","fact":"持有令牌"}],"did":[],"voice_shift":[]}'
    ingest_chapter(store, 10, fake_llm)

    pending = store.list_unverified("pending")
    target = [p for p in pending if p["name"] == "神秘人" and p["seq"] == 10]
    assert target, "应有 pending 行"
    uid = target[0]["id"]

    result = store.accept_unverified(uid)   # 不传 complete_fn
    assert result["created"] is True
    assert result["replayed"] is False, "无 complete_fn 应跳过 replay"
    # 角色实体已建
    assert store.entity("role:神秘人") is not None


def test_accept_unverified_replay_error_is_soft(store):
    """replay 抛异常时,角色建立 + status=accepted 仍保留,replayed=False。"""
    store.save_chapter(11, "影者现身。", focalizer=None)
    bad_llm = lambda _p: '{"learned":[{"who":"影者","fact":"来历不明"}],"did":[],"voice_shift":[]}'
    ingest_chapter(store, 11, bad_llm)

    pending = store.list_unverified("pending")
    target = [p for p in pending if p["name"] == "影者" and p["seq"] == 11]
    assert target
    uid = target[0]["id"]

    exploding_fn = lambda _p: (_ for _ in ()).throw(RuntimeError("模拟 LLM 崩溃"))
    result = store.accept_unverified(uid, complete_fn=exploding_fn)
    assert result["created"] is True, "角色应已建立"
    assert result["replayed"] is False, "replay 崩溃应 soft-fail"
    # status 已更新为 accepted
    accepted = store.list_unverified("accepted")
    assert any(r["id"] == uid for r in accepted), "status 应已置 accepted"


# ── G4: 自动弧光抽取(char_state ingest)───────────────────────────────────────

def test_ingest_auto_records_char_state(store):
    """apply_delta 带 arc 条目时,char_state 应自动写入,char_state_at 能读出能力快照。"""
    _ensure_chars(store, "甲")
    delta = {
        "learned": [],
        "did": [],
        "voice_shift": [],
        "arc": [{"who": "甲", "change_type": "ability",
                 "summary": "习得御剑", "snapshot": {"御剑": "初成"}}],
    }
    apply_delta(store, delta, seq=3)
    snap = store.char_state_at("role:甲", 5)
    assert "御剑" in str(snap.get("abilities")), \
        f"char_state_at 应含御剑能力,实际 abilities={snap.get('abilities')}"


def test_ingest_char_state_idempotent(store):
    """同一章 apply_delta(含 arc)连续两次,char_state 不应重复叠加。"""
    _ensure_chars(store, "甲")
    delta = {
        "learned": [],
        "did": [],
        "voice_shift": [],
        "arc": [{"who": "甲", "change_type": "ability",
                 "summary": "习得御剑", "snapshot": {"御剑": "初成"}}],
    }
    apply_delta(store, delta, seq=3)
    apply_delta(store, delta, seq=3)  # 第二次 — purge_ingest 应先清再重写

    # char_state_at 合并后御剑只应出现一次
    from scribe3.store import SurrealStore
    rows = store._query(
        "SELECT * FROM char_state WHERE character_id=$cid AND chapter=$ch AND ingest_seq=$iseq",
        {"cid": "role:甲", "ch": 3, "iseq": 3})
    assert len(rows) == 1, \
        f"同章二次 apply_delta 后 char_state 应只有 1 条,实际 {len(rows)} 条"


def test_ingest_char_state_relation(store):
    """relation 类弧光快照应写入 relation_snapshot 并能在 char_state_at 的 relations 读到。"""
    _ensure_chars(store, "焦三")
    delta = {
        "learned": [], "did": [], "voice_shift": [],
        "arc": [{"who": "焦三", "change_type": "relation",
                 "summary": "与阿萤建立信任", "snapshot": {"阿萤": "信任同行"}}],
    }
    apply_delta(store, delta, seq=4)
    snap = store.char_state_at("role:焦三", 4)
    assert "阿萤" in str(snap.get("relations")), \
        f"relation 弧光应写入 relations,实际={snap.get('relations')}"


def test_ingest_char_state_no_arc_still_works(store):
    """delta 不含 arc 字段(旧格式)时,apply_delta 仍正常运行不报错。"""
    _ensure_chars(store, "焦三")
    delta = {"learned": [{"who": "焦三", "fact": "老道是追索者"}], "did": [], "voice_shift": []}
    n = apply_delta(store, delta, seq=5)
    assert n == 1, "旧格式 delta(无 arc)仍应正常写知识边"


# ── S3: learned 语义去重测试(W3#6) ────────────────────────────────────────────

def test_learned_dedup_same_text_two_chars_one_proposition(store):
    """同一 learned 文本被两个角色在不同章学到 → 只建 1 条命题,两人各有 knows 边。"""
    _ensure_chars(store, "焦三", "阿萤")
    # 第1章: 焦三学到"尸丹能聚魂"
    apply_delta(store, {
        "learned": [{"who": "焦三", "fact": "尸丹能聚魂"}],
        "did": [],
    }, seq=1)
    # 第2章: 阿萤学到完全相同的文本"尸丹能聚魂"
    apply_delta(store, {
        "learned": [{"who": "阿萤", "fact": "尸丹能聚魂"}],
        "did": [],
    }, seq=2)

    # 命题层:只应有 1 条"尸丹能聚魂"命题
    all_props = store.facts_at(99)
    judan_props = [f for f in all_props if "聚魂" in f.value]
    assert len(judan_props) == 1, \
        f"相同 learned 文本应只建 1 条命题,实际 {len(judan_props)} 条: {[f.id for f in judan_props]}"

    # 知识边层:焦三和阿萤都应知道这条命题
    fr_jiao = project_frame(store, "role:焦三", 1)
    fr_ying = project_frame(store, "role:阿萤", 2)
    assert any("聚魂" in f.value for f in fr_jiao.facts), "焦三应知道该命题"
    assert any("聚魂" in f.value for f in fr_ying.facts), "阿萤应知道该命题"


def test_learned_dedup_same_char_two_chapters_idempotent(store):
    """同一角色在两章学到相同文本 → 命题只有 1 条,第2章不重建。"""
    _ensure_chars(store, "焦三")
    apply_delta(store, {
        "learned": [{"who": "焦三", "fact": "老道是流云观追索者"}],
        "did": [],
    }, seq=3)
    apply_delta(store, {
        "learned": [{"who": "焦三", "fact": "老道是流云观追索者"}],
        "did": [],
    }, seq=4)

    all_props = store.facts_at(99)
    matching = [f for f in all_props if "追索者" in f.value]
    assert len(matching) == 1, \
        f"相同 learned 文本不同章应只建 1 条命题,实际 {len(matching)} 条"


def test_learned_dedup_different_text_creates_new_proposition(store):
    """文本实质不同 → 必须各自建独立命题,不能误合并。"""
    _ensure_chars(store, "焦三")
    apply_delta(store, {
        "learned": [{"who": "焦三", "fact": "尸丹能聚魂"}],
        "did": [],
    }, seq=1)
    apply_delta(store, {
        "learned": [{"who": "焦三", "fact": "灵龙镇煞钉封印三百年"}],
        "did": [],
    }, seq=2)

    all_props = store.facts_at(99)
    assert any("聚魂" in f.value for f in all_props), "第一条命题应存在"
    assert any("镇煞钉" in f.value for f in all_props), "第二条命题应存在"
    # 且是 2 条独立命题
    unique = [f for f in all_props if "聚魂" in f.value or "镇煞钉" in f.value]
    assert len(unique) == 2, f"不同文本应建 2 条独立命题,实际 {len(unique)} 条"


def test_learned_dedup_fail_safe_creates_proposition(store):
    """去重查找失败(store 方法异常)时,fall-back 到新建命题,不丢失知识。"""
    _ensure_chars(store, "焦三")
    # 先建一条可能被搜索到的命题
    apply_delta(store, {
        "learned": [{"who": "焦三", "fact": "尸丹能聚魂"}],
        "did": [],
    }, seq=1)

    # 模拟 facts_at 异常(去重查找路径内部可能用到)
    import unittest.mock as mock
    original_facts_at = store.facts_at

    call_count = {"n": 0}
    def patched_facts_at(ch):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("模拟查找异常")
        return original_facts_at(ch)

    # 注入异常路径,验证 apply_delta 仍能成功(fall-back 建新命题)
    with mock.patch.object(store, "facts_at", patched_facts_at):
        # 不应抛异常
        n = apply_delta(store, {
            "learned": [{"who": "焦三", "fact": "尸丹能聚魂"}],
            "did": [],
        }, seq=5)
    assert n == 1, f"fall-safe 路径应成功写入 1 条,实际 n={n}"


def test_ingest_char_state_unknown_char_skipped(store):
    """arc 里引用了库外角色(未建实体)时,该条目被跳过,已知角色不受影响。"""
    _ensure_chars(store, "焦三")
    delta = {
        "learned": [], "did": [], "voice_shift": [],
        "arc": [
            {"who": "幻觉角色", "change_type": "ability",
             "summary": "莫须有能力", "snapshot": {"???": "???"}},
            {"who": "焦三", "change_type": "personality",
             "summary": "性格内敛", "snapshot": "变得沉默"},
        ],
    }
    apply_delta(store, delta, seq=6)
    snap = store.char_state_at("role:焦三", 6)
    assert snap.get("personality"), "焦三的 personality 弧光应写入"
    # 幻觉角色的 char_state 不应存在
    rows = store._query("SELECT * FROM char_state WHERE character_id=$cid",
                        {"cid": "role:幻觉角色"})
    assert not rows, "未登记角色的 char_state 不应写入"


# ── R3: learned 去重 × purge 防悬挂边(第三轮 P1-b)──────────────────────────────

def test_learned_dedup_reingest_source_chapter_no_dangling_knows(store):
    """核心守卫:B 章复用 A 章命题,重 ingest A 章不得让 B 的 knows 边悬空。

    复现路径:
    1. A 章(seq=20) ingest → 建命题 + 焦三 knows 边
    2. B 章(seq=21) ingest 相同文本 → _find_existing_learned_prop 复用同一命题,
       只发 阿萤 knows 边(ingest_seq=21),命题 ingest_seq 仍=20
    3. 重 ingest A 章(seq=20) → purge_ingest(20) 原来会 DELETE proposition WHERE ingest_seq=20
       修复后:检测到命题被 seq=21 的 knows 边引用,保留命题,只删 seq=20 的 knows 边
    4. B 章的阿萤 knows 边应仍指向存在的命题(不悬空)
    """
    _ensure_chars(store, "焦三", "阿萤")
    fact_text = "尸丹能让亡魂附体"

    # A 章:焦三学到命题
    apply_delta(store, {
        "learned": [{"who": "焦三", "fact": fact_text}],
        "did": [],
    }, seq=20)

    # 确认 A 章建了命题
    all_props = store.facts_at(99)
    matching = [f for f in all_props if fact_text in f.value]
    assert len(matching) == 1, f"A 章应建 1 条命题,实际 {len(matching)}"
    prop_id = matching[0].id

    # B 章:阿萤学到相同文本 → 复用 A 章命题
    apply_delta(store, {
        "learned": [{"who": "阿萤", "fact": fact_text}],
        "did": [],
    }, seq=21)

    # 确认 B 章没有新建命题(仍只有 1 条)
    all_props2 = store.facts_at(99)
    matching2 = [f for f in all_props2 if fact_text in f.value]
    assert len(matching2) == 1, f"B 章复用后应仍只有 1 条命题,实际 {len(matching2)}"

    # 确认 B 章的阿萤 knows 该命题
    fr_ying_before = project_frame(store, "role:阿萤", 21)
    assert any(fact_text in f.value for f in fr_ying_before.facts), \
        "B 章 ingest 后阿萤应知道该命题"

    # 重 ingest A 章 ——这是触发悬挂边的操作
    apply_delta(store, {
        "learned": [{"who": "焦三", "fact": fact_text}],
        "did": [],
    }, seq=20)

    # 命题应仍存在(未被 purge_ingest(20) 删除)
    all_props3 = store.facts_at(99)
    matching3 = [f for f in all_props3 if fact_text in f.value]
    assert len(matching3) >= 1, \
        f"重 ingest A 章后命题应仍存在(B 章还在引用),实际 {len(matching3)} 条"

    # B 章的阿萤 knows 边不得悬空——阿萤帧里仍能看到该命题
    fr_ying_after = project_frame(store, "role:阿萤", 21)
    assert any(fact_text in f.value for f in fr_ying_after.facts), \
        "重 ingest A 章后 B 章阿萤的 knows 边不应悬空,阿萤帧仍应含该命题"


# ── 批0 D-2:learned 去重去包含匹配,防相反语义误合并 ────────────────────────────

def test_learned_dedup_forward_inclusion_opposite_semantics_not_merged(store):
    """『X』与『X,但那只是假消息』互为包含关系但语义相反 → 必须是 2 条独立命题。

    修前(包含匹配 bug):否定/限定版被并到肯定版一条,获知否定版的角色被挂到
    未否定命题,限知帧显示与正文相反。
    """
    _ensure_chars(store, "焦三", "阿萤")
    base = "长老会早已知道血月之夜将举行大祭之事"     # 18 字 ≥15
    assert len(base) >= 15
    # 焦三先获知肯定版
    apply_delta(store, {"learned": [{"who": "焦三", "fact": base}], "did": []}, seq=1)
    # 阿萤后获知否定/限定版(文本包含肯定版)
    negated = base + ",但那只是放出的假消息"
    apply_delta(store, {"learned": [{"who": "阿萤", "fact": negated}], "did": []}, seq=2)

    all_props = store.facts_at(99)
    # 完全相等各一条:肯定版与否定版都应作为独立命题存在
    has_base = any(f.value == base for f in all_props)
    has_negated = any(f.value == negated for f in all_props)
    assert has_base and has_negated, \
        f"包含关系的相反语义命题不得合并;has_base={has_base} has_negated={has_negated} " \
        f"实际命题={[f.value for f in all_props if base in f.value]}"

    # 语义正确:阿萤知道的应是否定版,而非被挂到未否定命题
    fr_ying = project_frame(store, "role:阿萤", 2)
    assert any(f.value == negated for f in fr_ying.facts), \
        "阿萤应知道否定/限定版命题(不得被并到肯定版)"


def test_learned_dedup_reverse_inclusion_not_merged(store):
    """反向包含(短命题是长命题的子串,二者均 ≥15 字)也不得合并。"""
    _ensure_chars(store, "焦三", "阿萤")
    short = "御史台密报朝廷城主暗中通敌一事"     # 15 字 ≥15
    assert len(short) >= 15
    long = short + "已被彻查坐实"                  # 包含 short,长度更长
    apply_delta(store, {"learned": [{"who": "焦三", "fact": long}], "did": []}, seq=1)
    apply_delta(store, {"learned": [{"who": "阿萤", "fact": short}], "did": []}, seq=2)

    all_props = store.facts_at(99)
    has_long = any(f.value == long for f in all_props)
    has_short = any(f.value == short for f in all_props)
    assert has_long and has_short, \
        f"反向包含不得合并;has_long={has_long} has_short={has_short}"


def test_learned_dedup_exact_equal_still_reused(store):
    """去包含匹配后仍须保留:完全相等命题跨角色/跨章复用同一条(正确性 + 去重不回退)。"""
    _ensure_chars(store, "焦三", "阿萤")
    fact_text = "血月之夜将举行大祭"
    apply_delta(store, {"learned": [{"who": "焦三", "fact": fact_text}], "did": []}, seq=1)
    apply_delta(store, {"learned": [{"who": "阿萤", "fact": fact_text}], "did": []}, seq=2)
    all_props = store.facts_at(99)
    matching = [f for f in all_props if f.value == fact_text]
    assert len(matching) == 1, \
        f"完全相等命题应复用为 1 条,实际 {len(matching)} 条"


# ── 伏笔母题章感知:ingest 抽本章母题 → motif_instance ──────────────────────────

def test_apply_delta_motif_resolves_and_records(store):
    """delta.motif → 解析到已立母题 → 落 motif_instance;解析不到的名跳过不报错。"""
    store.add_motif("铜炉", theme="宿命")
    mid = store.list_motifs()[0]["id"]
    delta = {"learned": [], "did": [], "voice_shift": [], "arc": [],
             "motif": [
                 {"motif": "铜炉", "evidence": "炉火忽明忽暗"},
                 {"motif": "不存在的母题", "evidence": "x"},
             ]}
    apply_delta(store, delta, seq=5)
    got = store.list_motif_instances(5)
    assert len(got) == 1
    assert got[0]["motif_id"] == mid
    assert got[0]["evidence"] == "炉火忽明忽暗"


def test_parse_knowledge_delta_includes_motif():
    from scribe3.critique import parse_knowledge_delta
    d = parse_knowledge_delta('{"learned":[],"did":[],"motif":[{"motif":"铜炉","evidence":"炉火"}]}')
    assert d is not None
    assert d["motif"] == [{"motif": "铜炉", "evidence": "炉火"}]


def test_build_prompt_lists_existing_motifs():
    from scribe3.critique import build_knowledge_extract_prompt
    p = build_knowledge_extract_prompt("正文", motif_names=["铜炉", "纸命"])
    assert "铜炉" in p and "纸命" in p and "motif" in p
    p2 = build_knowledge_extract_prompt("正文")
    assert "motif" not in p2


# ── 伏笔触及抽取联动:ingest 抽本章推进的已埋伏笔 → promise_touch ────────────────

def test_extract_prompt_contains_promises():
    from scribe3.critique import build_knowledge_extract_prompt
    p = build_knowledge_extract_prompt("正文", promise_items=[
        {"id": "promise:abc", "text": "井底的名字"}])
    assert "promise_touch" in p and "井底的名字" in p
    # Task5-B②:排除条款——相近意象/字眼不指向该悬念的不算触及
    assert "不算触及" in p
    # 不传 promise_items 时不出现 promise 段(与 motif 段同范式)
    p2 = build_knowledge_extract_prompt("正文")
    assert "promise_touch" not in p2


def test_apply_delta_promise_touch(store):
    store.plant_promise("井底的名字", setup_chapter=1)
    pid = [x for x in store.list_promises()][0]["id"]
    from scribe3.ingest import apply_delta
    apply_delta(store, {"promise_touch": [
        {"text": "井底的名字", "evidence": "她又梦见那口井"},
        {"text": "不存在的伏笔", "evidence": "x"},   # 解析不到 → 跳过不建
    ]}, seq=3)
    touches = store.list_promise_touches(pid)
    assert len(touches) == 1 and touches[0]["chapter"] == 3


def test_ingest_chapter_passes_open_promises(store):
    """ingest_chapter 应收集 open 伏笔传入抽取 prompt,并把 promise_touch 落表(ingest_seq=seq 可 purge)。"""
    store.plant_promise("井底的名字", setup_chapter=1)
    pid = [x for x in store.list_promises()][0]["id"]
    store.save_chapter(3, "她又梦见那口井。", focalizer=None)
    seen_prompts = []

    def fake(p):
        seen_prompts.append(p)
        return ('{"learned":[],"did":[],"voice_shift":[],'
                '"promise_touch":[{"text":"井底的名字","evidence":"她又梦见那口井"}]}')

    ingest_chapter(store, 3, fake)
    assert "井底的名字" in seen_prompts[0] and "promise_touch" in seen_prompts[0]
    touches = store.list_promise_touches(pid)
    assert len(touches) == 1 and touches[0]["chapter"] == 3
    # 幂等:re-ingest 不双计(ingest_seq=seq 必须显式传,缺省=手动登记不可 purge)
    ingest_chapter(store, 3, fake)
    assert len(store.list_promise_touches(pid)) == 1


def test_resolve_promise_truncated_unique_match(store):
    """Task5-B①:>40字伏笔,LLM 只回 prompt 里的 40 字截断键 → 唯一命中仍解析成功。"""
    long_text = "老宅地窖里那半页烧残的族谱上记着一个被全族除名的名字这些年没有任何人敢当面提起它半个字"
    assert len(long_text) > 40
    store.plant_promise(long_text, setup_chapter=1)
    pid = [x for x in store.list_promises()][0]["id"]
    apply_delta(store, {"promise_touch": [
        {"text": long_text[:40], "evidence": "她又翻出那半页族谱"},
    ]}, seq=3)
    touches = store.list_promise_touches(pid)
    assert len(touches) == 1 and touches[0]["chapter"] == 3


def test_resolve_promise_truncated_ambiguous_skipped(store):
    """Task5-B①:两条 open 伏笔共享同一前 40 字 → 截断键歧义,跳过不落(零误匹配)。"""
    base = "城南义庄第三口棺材底下压着的那封旧信迟迟没有人来取走它上面的火漆印从未被人拆开过"
    assert len(base) == 40
    store.plant_promise(base + ",甲结尾", setup_chapter=1)
    store.plant_promise(base + ",乙结尾", setup_chapter=1)
    pids = [x["id"] for x in store.list_promises()]
    apply_delta(store, {"promise_touch": [{"text": base, "evidence": "x"}]}, seq=3)
    for pid in pids:
        assert store.list_promise_touches(pid) == []


# ── Task5:ingest 抽 lie_belief 位移(弧光进度压成可监控标量)────────────────────

def test_extract_prompt_contains_belief_seg():
    from scribe3.critique import build_knowledge_extract_prompt
    p = build_knowledge_extract_prompt("正文", belief_chars=[
        {"name": "柳怀玉", "lie": "官法大过阴律"}])
    assert "belief" in p and "官法大过阴律" in p
    # 空列表/不传时无 belief 段(与 motif/promise 段同范式)
    p2 = build_knowledge_extract_prompt("正文", belief_chars=[])
    assert "belief" not in p2
    p3 = build_knowledge_extract_prompt("正文")
    assert "belief" not in p3


def test_parse_knowledge_delta_includes_belief():
    from scribe3.critique import parse_knowledge_delta
    d = parse_knowledge_delta(
        '{"learned":[],"did":[],"belief":[{"who":"柳怀玉","value":62,"why":"目睹师门弃卒"}]}')
    assert d is not None
    assert d["belief"] == [{"who": "柳怀玉", "value": 62, "why": "目睹师门弃卒"}]


def test_apply_delta_lie_belief(store):
    """delta.belief → 解析到已有角色 → char_state(change_type='belief', lie_belief=clamp值);
    幻觉角色跳过;值 clamp 到 [0,100]。"""
    _ensure_chars(store, "柳怀玉")
    cid = "role:柳怀玉"
    store.set_char_anchors(cid, {"lie": "恩义终会被辜负"})
    apply_delta(store, {"belief": [
        {"who": "柳怀玉", "value": 62, "why": "目睹师门弃卒"},
        {"who": "幻觉角色", "value": 10, "why": "x"},   # 解析不到 → 跳过
    ]}, seq=3)
    assert store.latest_lie_belief(cid, 3) == 62
    # clamp:超界值入库前钳到 [0,100]
    apply_delta(store, {"belief": [{"who": "柳怀玉", "value": 130, "why": "y"}]}, seq=4)
    assert store.latest_lie_belief(cid, 4) == 100


def test_ingest_chapter_passes_belief_chars(store):
    """ingest_chapter 应收集有 lie 锚的角色传入抽取 prompt,并把 belief 落 char_state。"""
    _ensure_chars(store, "柳怀玉")
    cid = "role:柳怀玉"
    store.set_char_anchors(cid, {"lie": "官法大过阴律"})
    store.save_chapter(3, "柳怀玉判牍,见冤不能雪。", focalizer=None)
    seen_prompts = []

    def fake(p):
        seen_prompts.append(p)
        return ('{"learned":[],"did":[],"voice_shift":[],'
                '"belief":[{"who":"柳怀玉","value":58,"why":"判牍见冤"}]}')

    ingest_chapter(store, 3, fake)
    assert "官法大过阴律" in seen_prompts[0] and "belief" in seen_prompts[0]
    assert store.latest_lie_belief(cid, 3) == 58


# ── Task7:Task5 审查跟进(②歧义 warning / ③belief re-ingest 幂等)────────────────

def test_resolve_promise_ambiguous_prefix_skips_with_warning(caplog):
    """Task5跟进②:截断键歧义(多条同前40字)跳过时应记一行 warning(与写失败日志对称)。"""
    import logging
    from scribe3.ingest import _resolve_promise
    prefix = "甲" * 40
    rows = [{"id": "promise:a", "text": prefix + "一支"},
            {"id": "promise:b", "text": prefix + "二支"}]
    with caplog.at_level(logging.WARNING, logger="scribe3.ingest"):
        assert _resolve_promise(rows, prefix) is None
    assert any("歧义" in r.message for r in caplog.records), \
        "歧义跳过应有 warning 日志"


def test_apply_delta_belief_reingest_idempotent(store):
    """Task5跟进③:同章两次 apply_delta belief,char_state belief 行只剩一份(purge 幂等)。"""
    _ensure_chars(store, "柳怀玉")
    cid = "role:柳怀玉"
    store.set_char_anchors(cid, {"lie": "恩义终会被辜负"})
    delta = {"belief": [{"who": "柳怀玉", "value": 62, "why": "目睹师门弃卒"}]}
    apply_delta(store, delta, seq=3)
    apply_delta(store, delta, seq=3)   # re-ingest 同章
    rows = store._query(
        "SELECT * FROM char_state WHERE character_id=$cid AND change_type='belief'",
        {"cid": cid})
    assert len(rows) == 1, f"同章二次 apply_delta 后 belief 行应只剩 1 条,实际 {len(rows)}"
    assert store.latest_lie_belief(cid, 3) == 62
