"""统一生产上下文引擎的设定圣经与限知 parity 合同。

背景:该系统 7-12 验收后 flag 全关沉睡;7-14/15 在【旧链】(_editor_system/
_editor_write_system/_codex_block)上加了 CX-Task 6(faction 28 字段设定进 prompt)与
三档限知门控(U-003)。统一写作链(app._assemble_write_instructions_v1)必须持续覆盖
以下两个历史缺口，否则唯一生产路径会发生功能回归/泄密:

缺口A(功能回归):v1 身份层刻意不走 _editor_system(防 facts/promises 重复),故完全
  不含设定圣经(faction 28 字段/世界规则/术语/物件/母题)——CX-6 后是旗舰能力,v1 一个
  字都没有。修法:v1 内直接调用 _codex_block(逐字复用旧链同一函数、同一 for_generation=True
  语义),不重新发明门控。

缺口B(安全,更重要):envelope canonical 的两条取数路径(retriever 候选 / store 降级)
  对 codex_secret_bridge 造的势力 secret 字段镜像(如 origin/secret_agenda)没有结构性
  过滤——store 降级路径(_canonical_all_facts)在全知章(focalizer 空,"正常模式")完全不
  掩码,直接裸值转储;retriever 候选路径虽有 secret 信号masking,但信号本身可退化
  (_secret_fact_ids fail-soft 空集 / 候选 provenance 未必带 secret 位)。与旧链 M6 转储
  泄露同型(app._is_faction_bridge_mirror 当年修的那个洞),只是发生在 context_assembler
  而非 _editor_system。修法:codex_secret_bridge.is_faction_bridge_mirror 领域谓词(单一
  真相源)+ context_assembler 两条路径无条件剔除 + app 嵌套谓词改薄委托。

不真调 LLM；真实 SurrealDB(conftest.py `store` 夹具,临时内存子进程)。
"""
import pytest

from scribe3.app import _assemble_write_instructions, _editor_write_system
from scribe3.codex_secret_bridge import is_faction_bridge_mirror, sync_faction_secrets
from scribe3.context_assembler import ContextAssembler, render_envelope_text
from scribe3.ontology import Entity, Fact, KnowledgeEdge

FACTION = "衔尾蛇秘会"
ENTITY_ID = f"faction:{FACTION}"


def _sync(store, name: str) -> dict:
    """回读势力行后跑命题桥(与 app.py POST /factions 落库后的调用方式一致,
    见 test_codex_prompt.py 同款辅助——不重新发明)。"""
    row = store.get_faction(name)
    assert row is not None, f"测试前置条件:势力 {name!r} 应已存在"
    return sync_faction_secrets(store, name, row)


def _bridge_fact_id(store, entity_id: str, attribute: str) -> str:
    """裸查桥接命题的 fact id(`fact:{local}`),供测试直接给它挂 KnowledgeEdge。"""
    rows = store._query(
        "SELECT meta::id(id) AS local FROM proposition "
        "WHERE entity_id=$eid AND attribute=$attr AND source='codex_bridge' LIMIT 1",
        {"eid": entity_id, "attr": attribute})
    assert rows, f"未找到桥接命题: {entity_id}/{attribute}(先调用 _sync)"
    return f"fact:{rows[0]['local']}"


def _patch_embed(monkeypatch):
    """确定性假 embedding(不加载真模型/服务)——MEMORY_FABRIC 开态测试用(与
    test_memory_trace.py 同款手法,防真加载本地 embedding 模型拖慢/搞崩测试)。"""
    def fake(texts):
        out = []
        for t in texts:
            v = [0.0] * 512
            for ch in (t or ""):
                if ch.strip():
                    v[ord(ch) % 512] += 1.0
            n = sum(x * x for x in v) ** 0.5 or 1.0
            out.append([x / n for x in v])
        return out
    monkeypatch.setattr("scribe3.embed.embed", fake)


def _v1(store, *, chapter=1, focalizer="", phase="draft", seed_words=None):
    """便捷包装:调用 chat_write 唯一完整组装链，不直接碰 _v1 私有函数。"""
    return _assemble_write_instructions(
        store, chapter=chapter, focalizer=focalizer, phase=phase,
        seed_words=seed_words or [], short_mode=False, with_tools=False, work="main")


# ============================================================
# ① 缺口A:v1 instructions 含设定圣经(此前完全缺席)
# ============================================================

def test_v1_instructions_include_codex_bible_block(store, monkeypatch):
    store.add_faction(
        FACTION, ideology="尾衔其首,生生不息", leader="老祖",
        structure={"type": "金字塔", "core_size": 7,
                   "decision_mechanism": "长老议事", "succession": "血脉相承"},
        goals=[{"phase": "潜伏期", "target": "夺回信物", "status": "ongoing"}],
    )
    out = _v1(store, chapter=1)
    assert "设定圣经" in out, "v1 instructions 必须含设定圣经块标签(缺口A)"
    assert "组织结构" in out and "长老议事" in out, "faction.structure 应结构化注入(CX-6 字段,不是旧的 name+ideology[:18])"
    assert "金字塔" in out, "faction.structure.type 应结构化注入"


def test_v1_codex_block_placeholder_when_no_codex_data(store, monkeypatch):
    """无设定数据时:仍出现"设定圣经"标签 + 占位文案,不是静默消失
    (与旧链 _editor_system 的 `or '(尚无设定)'` 兜底同语义)。"""
    out = _v1(store, chapter=1)
    assert "设定圣经" in out
    assert "尚无设定" in out


# ============================================================
# ② 三档可见性在 v1 同样成立(_codex_block 逐字复用带来的门控语义)
# ============================================================

def test_v1_secret_field_hidden_without_knows_edge(store, monkeypatch):
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True,
                      motto="公开的格言明文")
    _sync(store, FACTION)
    out = _v1(store, chapter=5, focalizer="role:不知情的旁观者")
    assert "源自前朝遗族的复国密谋" not in out, "secret 字段(无 knows 边)不得出现"
    assert "公开的格言明文" in out, "公开字段应正常出现,门控不能误伤"


def test_v1_secret_field_shown_when_focalizer_knows(store, monkeypatch):
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)
    fact_id = _bridge_fact_id(store, ENTITY_ID, "origin")
    store.add_entity(Entity("role:知情人", "character", "知情人"))
    store.add_knowledge(KnowledgeEdge("role:知情人", fact_id, since_chapter=1))

    out = _v1(store, chapter=5, focalizer="role:知情人")
    assert "源自前朝遗族的复国密谋" in out, "焦点者知情(project_frame 帧内)应正常注入该字段"


def test_v1_secret_agenda_never_appears_even_with_knows_edge(store, monkeypatch):
    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)
    fact_id = _bridge_fact_id(store, ENTITY_ID, "secret_agenda")
    store.add_entity(Entity("role:意外知情者", "character", "意外知情者"))
    store.add_knowledge(KnowledgeEdge("role:意外知情者", fact_id, since_chapter=1))

    out = _v1(store, chapter=5, focalizer="role:意外知情者")
    assert "连核心层都不知道的真相" not in out, (
        "secret_agenda(chief_only)生成/续写路径永不该出现,即便存在 knows 边")


def test_v1_public_field_unaffected_by_gating(store, monkeypatch):
    store.add_faction(FACTION, motto="尾衔其首,生生不息")
    out = _v1(store, chapter=1, focalizer="role:任何人")
    assert "尾衔其首,生生不息" in out, "非 secret 字段不应被限知门控误伤"


# ============================================================
# ③ 缺口B(安全,核心):全知(focalizer 空)下 canonical 不得裸泄命题桥镜像
# ============================================================

def test_gap_b_store_fallback_excludes_bridge_mirror_when_omniscient(store, monkeypatch):
    """核心回归钉·store 降级路径(MEMORY_FABRIC 关,当前生产默认状态):全知章
    (focalizer 空,"正常模式")envelope canonical 块本身(不含 codex 块,直接测
    ContextAssembler,隔离缺口A 的影响)不得含桥镜像明文。"""
    import scribe3.app as appmod
    store.add_faction(FACTION,
                      origin="源自前朝遗族的复国密谋", origin_secret=True,
                      secret_agenda="连核心层都不知道的真相", secret_agenda_secret=True)
    _sync(store, FACTION)

    snap = appmod._write_snapshot(store, chapter=5, focalizer=None, phase="draft", work="main")
    envelope = ContextAssembler(store, None).assemble(snap, "", "write")   # retriever=None → store 降级
    text = render_envelope_text(envelope)
    assert "源自前朝遗族的复国密谋" not in text, "origin 桥镜像不得以裸事实进 canonical"
    assert "连核心层都不知道的真相" not in text, "secret_agenda 桥镜像不得以裸事实进 canonical"


def test_gap_b_real_story_secret_still_shown_omniscient_not_over_filtered(store):
    """反向:普通(非桥)故事秘密在全知视角保持既有语义——别把真实故事秘密一起误杀
    (只滤 faction 桥镜像,与旧链 U-003 补洞注释同一条红线)。"""
    import scribe3.app as appmod
    store.add_entity(Entity("role:某人", "character", "某人"))
    store.add_fact(Fact("fact:真秘密", "role:某人", "真身", "其实是狐妖",
                        valid_from=1, secret=True))

    snap = appmod._write_snapshot(store, chapter=5, focalizer=None, phase="draft", work="main")
    envelope = ContextAssembler(store, None).assemble(snap, "", "write")
    text = render_envelope_text(envelope)
    assert "其实是狐妖" in text, "非桥接的真实故事秘密,全知视角应保持既有转储语义(私密标注但可见)"


def test_gap_b_frame_facts_path_excludes_bridge_mirror_attribute_name(store):
    """防御纵深(超出字面要求,zero 回归风险,见报告自审):限知章(focalizer 非空)下,
    project_frame 帧内命中桥镜像时,_canonical_frame_facts 此前虽已掩码 value
    (`mask = bool(f.secret)` 对桥镜像恒真),但仍会把 attribute 名(如 "secret_agenda")
    原样拼进那一行——value 掩码了,字段名本身仍是不该出现的元信息("这个 faction 有
    这个字段是秘密,且这个角色知道")。验证 canonical 文本里连 "secret_agenda" 这个词
    都不出现,不只是它的 value。"""
    import scribe3.app as appmod
    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)
    fact_id = _bridge_fact_id(store, ENTITY_ID, "secret_agenda")
    store.add_entity(Entity("role:知情人丙", "character", "知情人丙"))
    store.add_knowledge(KnowledgeEdge("role:知情人丙", fact_id, since_chapter=1))

    snap = appmod._write_snapshot(store, chapter=5, focalizer="role:知情人丙",
                                  phase="draft", work="main")
    envelope = ContextAssembler(store, None).assemble(snap, "", "write")
    text = render_envelope_text(envelope)
    assert "secret_agenda" not in text, (
        "桥镜像的属性名本身也不该在 canonical 出现(即便 value 已由既有 mask=bool(f.secret) 掩码)")


def test_gap_b_candidate_path_survives_secret_signal_degradation(store, monkeypatch):
    """P0 式对抗(仿 test_codex_prompt_adversarial.py 手法):即便 retriever 候选没打
    provenance.secret、且权威 secret 集因 store 抖动退化为空集(_secret_fact_ids 自己
    声明的 fail-soft 退化路径),结构性谓词(entity_id 前缀 + 字段名)仍必须独立兜底
    剔除桥镜像——不能依赖任何单一"secret 信号"是否完好。"""
    import scribe3.app as appmod
    import scribe3.context_assembler as ca

    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)
    fact_id = _bridge_fact_id(store, ENTITY_ID, "secret_agenda")

    monkeypatch.setattr(ca, "_secret_fact_ids", lambda st: set())

    class _NoSecretFlagCandidate:
        source_kind = "canonical"
        source_id = fact_id
        text = f"faction:{FACTION} secret_agenda 连核心层都不知道的真相"
        work = "main"
        provenance = [{"entity": ENTITY_ID, "attribute": "secret_agenda"}]  # 故意不带 secret 位
        revision = None

    class _FakeRetriever:
        def retrieve(self, work, snapshot_dict, query, k):
            return [_NoSecretFlagCandidate()]

    snap = appmod._write_snapshot(store, chapter=5, focalizer=None, phase="draft", work="main")
    envelope = ca.ContextAssembler(store, _FakeRetriever()).assemble(snap, "", "write")
    text = ca.render_envelope_text(envelope)
    assert "连核心层都不知道的真相" not in text, (
        "退化场景(secret 信号双双失效)下,结构性谓词仍须独立剔除桥镜像明文")


def test_gap_b_candidate_path_structurally_excludes_not_just_masks(store, monkeypatch):
    """非降级场景(真实 MemoryRetriever,secret 信号完好):桥镜像此前已经会被【掩码】
    为占位符(C1 修复,不是明文泄露),但要求是"无条件剔除"——canonical 根本不该承载
    桥镜像候选(占位行仍会暴露"这个 faction 有这个字段是秘密"的元信息;这些字段的
    授权注入通道是 _codex_block,不是 canonical)。验证桥镜像候选的 source_id 完全不
    出现在 canonical 块来源列表里,不只是 masked=True 的占位。"""
    _patch_embed(monkeypatch)
    import scribe3.app as appmod
    from scribe3.memory_retrieval import MemoryRetriever

    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)
    fact_id = _bridge_fact_id(store, ENTITY_ID, "origin")

    snap = appmod._write_snapshot(store, chapter=5, focalizer=None, phase="draft", work="main")
    envelope = ContextAssembler(store, MemoryRetriever(store)).assemble(snap, "秘会 起源", "write")
    canon = next(b for b in envelope.blocks if b.name == "canonical")
    source_ids = {s.source_id for s in canon.sources}
    assert fact_id not in source_ids, "桥镜像候选应被结构性剔除,而非仅仅 masked=True 占位残留"


@pytest.mark.parametrize("fabric_on", [False, True])
def test_v1_omniscient_end_to_end_never_leaks_bridge_mirror(store, monkeypatch, fabric_on):
    """端到端:全知写作(focalizer 空,"正常模式")下，MEMORY_FABRIC 开/关两态
    组装出的最终 instructions 都不得出现
    secret_agenda/origin 的明文——两条 canonical 取数路径都须过滤(与旧链 M6 修复对称)。"""
    if fabric_on:
        monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
        _patch_embed(monkeypatch)
    else:
        monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)

    store.add_faction(FACTION,
                      origin="源自前朝遗族的复国密谋", origin_secret=True,
                      secret_agenda="连核心层都不知道的真相", secret_agenda_secret=True,
                      motto="公开格言不受影响")
    _sync(store, FACTION)

    out = _v1(store, chapter=5, focalizer="", seed_words=["秘会", "复国"])

    assert "源自前朝遗族的复国密谋" not in out, f"origin 桥镜像明文泄露(fabric_on={fabric_on})"
    assert "连核心层都不知道的真相" not in out, f"secret_agenda 桥镜像明文泄露(fabric_on={fabric_on})"
    assert "公开格言不受影响" in out, "公开字段(经 _codex_block 正常通道注入)不应被误伤"


# ============================================================
# ④ 谓词单一真相源:app 嵌套谓词真委托 codex_secret_bridge.is_faction_bridge_mirror,
#    防两处各自实现漂移
# ============================================================

def test_bridge_mirror_predicate_is_single_source_of_truth(store, monkeypatch):
    """打断 codex_secret_bridge.is_faction_bridge_mirror(让它恒判 False)后,
    _editor_system 全知转储的 M6 过滤必须随之失效——证明 app 侧是【真委托调用】,
    不是在 app.py 里独立抄一份同款逻辑(独立抄的两份实现可能各自改动却互不知晓,
    渐行渐远,正是本任务要根治的漂移风险)。"""
    import scribe3.codex_secret_bridge as bridge_mod

    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)

    baseline = _editor_write_system(store, focalizer="", chapter=1)
    assert "连核心层都不知道的真相" not in baseline, "打断前:既有 M6 过滤应生效(回归基线)"

    monkeypatch.setattr(bridge_mod, "is_faction_bridge_mirror", lambda e, a: False)
    broken = _editor_write_system(store, focalizer="", chapter=1)
    assert "连核心层都不知道的真相" in broken, (
        "app 侧嵌套谓词必须是对 codex_secret_bridge.is_faction_bridge_mirror 的真委托——"
        "打断源函数后若 app 侧仍能独立过滤,说明两处判据各自实现,单一真相源不成立")


def test_bridge_mirror_predicate_consistent_across_call_sites():
    """一批既有真实字段名(部分 secret_capable、部分公开、部分 entity_id 前缀不匹配)
    交叉验证 is_faction_bridge_mirror 的判据边界,供 app.py/context_assembler.py 两处
    调用方共同信赖。"""
    cases = [
        (ENTITY_ID, "secret_agenda", True),
        (ENTITY_ID, "origin", True),
        (ENTITY_ID, "external_manipulation", True),
        (ENTITY_ID, "motto", False),             # 公开字段,不是桥镜像
        (ENTITY_ID, "ideology", False),           # 公开字段
        ("role:某人", "secret_agenda", False),     # 属性名撞了,但 entity_id 前缀不对
        ("faction:另一个势力", "artifact_operation", True),
        ("", "", False),
    ]
    for entity_id, attribute, expected in cases:
        assert is_faction_bridge_mirror(entity_id, attribute) is expected, (
            f"{entity_id!r}/{attribute!r} 判据应为 {expected}")
    assert is_faction_bridge_mirror(None, None) is False, "防御性:入参 None 不炸"
