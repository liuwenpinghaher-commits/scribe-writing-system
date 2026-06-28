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
