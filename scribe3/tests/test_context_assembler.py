"""Task 7 · ContextAssembler(可预算、可追溯的上下文组装)测试。

覆盖四条硬合同:
1. 固定八块顺序 + 总预算不超标(计划 Step 1 RED);
2. 正典优先——canonical 与冲突 episodic 撞车时,canonical 入块、
   episodic 进 omitted 且 reason=superseded_by_canonical;
3. 限知秘密屏蔽(宪法级)——focalizer 非空时 canonical 块物理屏蔽
   secret value,被屏蔽源留痕 masked=True;
4. envelope_hash / trace manifest 不含正文秘密,只记配方身份与来源 id。

不真调 LLM/retriever:retriever 用 FakeRetriever;store 用 conftest 临时 SurrealDB。
"""
from datetime import datetime, timezone

import json

import pytest

from scribe3.context_assembler import (
    BLOCK_BUDGETS,
    ContextAssembler,
    envelope_trace_manifest,
    estimate_tokens,
)
from scribe3.context_models import ContextFocus, ContextSnapshot
from scribe3.ontology import Entity, Fact, KnowledgeEdge


# ---------- 测试替身 ----------

class FakeCandidate:
    """MemoryRetriever(Task 8)候选的鸭子类型:assembler 只读这些属性。"""

    def __init__(self, source_kind, source_id, text, *, work="book-a",
                 provenance=None, **kw):
        self.source_kind = source_kind
        self.source_id = source_id
        self.text = text
        self.work = work
        self.provenance = provenance or []
        for k, v in kw.items():
            setattr(self, k, v)


class FakeRetriever:
    """协议 retrieve(work, snapshot_dict, query, k) -> list[候选]。"""

    def __init__(self, candidates):
        self._candidates = candidates
        self.calls = []

    def retrieve(self, work, snapshot_dict, query, k):
        self.calls.append((work, query, k))
        return list(self._candidates)

    @classmethod
    def with_conflicting_episode_and_fact(cls):
        """构造一枚"权威事实 vs 旧推测"冲突(同 entity+attribute)+ 若干块料。"""
        canonical = FakeCandidate(
            "canonical", "fact:jia-loc",
            "甲现在在城里(权威事实)",
            provenance=[{"entity": "role:jia", "attribute": "location",
                         "tense": "valid"}],
            revision="3")
        episodic = FakeCandidate(
            "episodic", "ep:jia-loc-old",
            "甲大概还在村里(旧推测)",
            provenance=[{"entity": "role:jia", "attribute": "location",
                         "tense": "belief"}],
            confidence=0.4)
        working = FakeCandidate(
            "working", "sum:1", "近三章工作摘要:甲进城寻兄。")
        procedural = FakeCandidate(
            "procedural", "lesson:1", "教训:限知章配角勿批发真相。")
        reference = FakeCandidate(
            "reference", "mat:1", "参考素材:某地城门夜市风物。")
        uncertainty = FakeCandidate(
            "uncertainty", "unc:1", "待确认:甲兄是否已死。", confidence=0.3)
        return cls([canonical, episodic, working, procedural, reference,
                    uncertainty])


# ---------- 夹具 ----------

def _snapshot(*, focus_id="role:jia", focus_type="character", focus_label="甲",
              work="book-a", chapter=3, focalizer=None):
    snap = ContextSnapshot(
        session_id="ctx-1", work=work, revision=2, thread_id="thread-a",
        entry="codex", directory_path=["codex", "characters"],
        focus=ContextFocus(type=focus_type, id=focus_id, label=focus_label),
        detail_route=f"character:{focus_id}", chapter=chapter, phase="draft",
        focalizer=focalizer, previous_revision=1, navigation_id="nav-1",
        captured_at=datetime.now(timezone.utc), context_hash="")
    return snap.with_hash()


def test_focalized_project_frame_failure_is_fail_loud(store, monkeypatch):
    import scribe3.knowledge as knowledge

    monkeypatch.setattr(
        knowledge, "project_frame",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("project-frame-query-failed")
        ),
    )

    with pytest.raises(RuntimeError, match="project-frame-query-failed"):
        ContextAssembler(store).assemble(
            _snapshot(work=store.db_name, focalizer="role:jia"),
            "本章事实", "write",
        )


@pytest.fixture()
def snapshot():
    return _snapshot()


def block(envelope, name):
    for b in envelope.blocks:
        if b.name == name:
            return b
    raise AssertionError(f"envelope 缺 block {name!r}")


# ---------- 计划 Step 1:预算 + 正典优先(RED) ----------

def test_assembler_is_budgeted_and_canonical_wins(store, snapshot):
    retriever = FakeRetriever.with_conflicting_episode_and_fact()
    envelope = ContextAssembler(store, retriever, token_budget=10_000).assemble(
        snapshot, "甲现在在哪?", "discussion")
    assert [b.name for b in envelope.blocks] == [
        "focus", "global", "canonical", "recent",
        "procedural", "reference", "uncertainty", "provenance",
    ]
    assert envelope.total_token_estimate <= 10_000
    assert "权威事实" in block(envelope, "canonical").text
    assert "旧推测" not in block(envelope, "canonical").text
    assert any(item["reason"] == "superseded_by_canonical"
               for item in envelope.omitted)


# ---------- 预算裁剪:每块不超上限,总额守住 ----------

def test_per_block_budget_and_total_respected(store, snapshot):
    # 塞一枚超长 canonical 候选,断言被裁到 canonical 预算内,溢出料进 omitted
    huge = FakeCandidate("canonical", "fact:huge", "甲" * 5000,
                         provenance=[{"entity": "role:x", "attribute": "a"}])
    normal = FakeCandidate("canonical", "fact:small", "乙在祠堂(权威)。",
                           provenance=[{"entity": "role:y", "attribute": "b"}])
    env = ContextAssembler(store, FakeRetriever([huge, normal]),
                           token_budget=10_000).assemble(snapshot, "x", "write")
    canon = block(env, "canonical")
    assert canon.token_estimate <= BLOCK_BUDGETS["canonical"]
    assert env.total_token_estimate <= 10_000
    # 溢出的巨块被 token_budget 裁掉并留痕
    assert any(o["reason"] == "token_budget" and o["source_id"] == "fact:huge"
               for o in env.omitted)


def test_estimate_tokens_is_conservative_char_count():
    assert estimate_tokens("甲乙丙") == 3
    assert estimate_tokens("") == 0


# ---------- 无 retriever 降级:canonical 仍有真数据,不崩 ----------

def test_degrades_to_store_when_retriever_none(store, snapshot):
    store.add_entity(Entity("role:jia", "character", "甲"))
    store.add_fact(Fact("fact:pub", "role:jia", "位置", "村口", valid_from=1))
    env = ContextAssembler(store, None, token_budget=10_000).assemble(
        snapshot, "甲在哪", "write")
    # 八块齐全,不因无 retriever 崩
    assert [b.name for b in env.blocks][:3] == ["focus", "global", "canonical"]
    assert "村口" in block(env, "canonical").text


def test_chapter_focus_includes_synopsis_and_beats(store):
    """章焦点必须把大纲和节拍一起纳入有预算、有溯源的 focus 块。"""
    store.save_chapter(3, "", title="第三章")
    store.update_chapter_meta(3, {
        "synopsis": "柳怀玉赴义庄验尸",
        "beats": [{"text": "抵达义庄"}, {"text": "发现异样"}],
    })
    snap = _snapshot(
        focus_id="3", focus_type="chapter", focus_label="第三章", chapter=3,
    )

    env = ContextAssembler(store, None).assemble(snap, "写本章", "write")

    focus = block(env, "focus")
    assert "柳怀玉赴义庄验尸" in focus.text
    assert "抵达义庄" in focus.text and "发现异样" in focus.text
    assert any(source.source_id == "chapter:3:outline" for source in focus.sources)


def test_recent_prioritizes_current_chapter_tail_with_memory_candidates(store):
    """开启经验检索后也不能让 memory candidate 挤掉当前章续写锚点。"""
    store.save_chapter(
        3,
        "这一段开头不应保留。" * 80 + "当前章结尾：老道把灯芯挑亮。",
        title="第三章",
    )
    snap = _snapshot(
        focus_id="3", focus_type="chapter", focus_label="第三章", chapter=3,
    )
    retriever = FakeRetriever([
        FakeCandidate("working", "sum:recent", "经验摘要：此处应放慢节奏。"),
    ])

    env = ContextAssembler(store, retriever).assemble(snap, "续写", "write")

    recent = block(env, "recent")
    assert "当前章结尾：老道把灯芯挑亮" in recent.text
    assert "经验摘要：此处应放慢节奏" in recent.text
    assert any(source.source_id == "chapter:3:tail" for source in recent.sources)


# ---------- 宪法级:限知章 secret value 物理屏蔽 + 留痕 ----------

def test_canonical_masks_secret_under_focalizer(store):
    store.add_entity(Entity("role:jia", "character", "甲"))
    # 公开事实(应可见)
    store.add_fact(Fact("fact:pub", "role:jia", "位置", "村口", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:jia", "fact:pub", since_chapter=1))
    # 私密事实(焦点者虽知,渲染层仍屏蔽 value,防 leak marker 穿帮)
    store.add_fact(Fact("fact:sec", "role:jia", "真身", "甲其实是狐妖",
                        valid_from=1, secret=True))
    store.add_knowledge(KnowledgeEdge("role:jia", "fact:sec", since_chapter=1))
    snap = _snapshot(focalizer="role:jia", chapter=2)
    env = ContextAssembler(store, None, token_budget=10_000).assemble(
        snap, "甲是谁", "write")
    canon = block(env, "canonical")
    assert "村口" in canon.text                     # 公开可见
    assert "甲其实是狐妖" not in canon.text          # 秘密物理屏蔽
    assert any(s.masked for s in canon.sources)     # 被屏蔽源留痕


# ---------- C1(宪法级):store 权威 secret 集夺回裁决权,retriever 漏标也屏蔽 ----------

def test_candidate_masked_from_store_secret_even_if_unflagged(store):
    """retriever 返回某 secret fact 的【真值文本】但 provenance 漏标 secret →
    ①全知章 ②限知章帧内,canonical text 都不得含真值且被屏蔽源 masked=True。
    此前候选路径只信 provenance.secret + 帧判据,这两种情形都会漏(严格弱于 store 路径)。"""
    store.add_entity(Entity("role:x", "character", "X"))
    store.add_fact(Fact("fact:sec", "role:x", "真身", "X是狐妖",
                        valid_from=1, secret=True))
    # 候选带 secret 真值文本,但未标 provenance.secret(模拟 retriever 漏标)
    cand = FakeCandidate("canonical", "fact:sec", "X的真身其实是狐妖(权威事实)",
                         provenance=[{"entity": "role:x", "attribute": "真身"}])

    # ① 全知章(focalizer=None):帧判据完全失效,只能靠 store 权威 secret 集救
    env_omni = ContextAssembler(store, FakeRetriever([cand])).assemble(
        _snapshot(focalizer=None), "X是谁", "write")
    c1 = block(env_omni, "canonical")
    assert "狐妖" not in c1.text
    assert any(s.masked and s.source_id == "fact:sec" for s in c1.sources)

    # ② 限知章且秘密在焦点者帧【内】(焦点者知这条 secret):帧判据放行,仍须屏蔽
    store.add_knowledge(KnowledgeEdge("role:x", "fact:sec", since_chapter=1))
    env_lim = ContextAssembler(store, FakeRetriever([cand])).assemble(
        _snapshot(focus_id="role:x", focalizer="role:x", chapter=2), "X是谁", "write")
    c2 = block(env_lim, "canonical")
    assert "狐妖" not in c2.text
    assert any(s.masked and s.source_id == "fact:sec" for s in c2.sources)


# ---------- I1(ON 路径,B-3 同型):envelope 独占事实注入,不与身份块重复 ----------

def test_unified_context_canonical_fact_appears_once(store):
    """统一内核用纯身份块 + envelope，某条 fact 的真值
    只应出现 1 次(此前 _editor_write_system 的设定块 + envelope canonical → 2 次)。"""
    import scribe3.app as appmod
    store.add_entity(Entity("role:jia", "character", "甲"))
    # 用一个绝不会撞车的独特串,避免和身份块/纪律块里的固定措辞混淆
    store.add_fact(Fact("fact:pub", "role:jia", "位置", "青骡巷尽头的窨井",
                        valid_from=1))
    out = appmod._assemble_write_instructions(
        store, chapter=1, focalizer="", phase="draft", seed_words=[],
        short_mode=False, with_tools=False, work="main")
    assert out.count("青骡巷尽头的窨井") == 1


def test_unified_context_calls_avoid_directive(store, monkeypatch):
    """S-007 回归钉:统一组装链必须调用 _avoid_directive(跨章避免复读禁令)。它是【确定性禁令】、
    非上下文信息——envelope 只聚合"前文写了什么",给不出"禁止逐字复用"的禁令;此前随
    "envelope 替代旧 avoid/voice/arc 散点"一起漏掉,曾导致跨章复读防线失效
    (实证某章 cross_repetition=25)。"""
    import scribe3.app as appmod
    called = {}
    orig = appmod._avoid_directive

    def _spy(st, ch, *a, **k):
        called["yes"] = True
        return orig(st, ch, *a, **k)

    monkeypatch.setattr(appmod, "_avoid_directive", _spy)
    appmod._assemble_write_instructions(
        store, chapter=2, focalizer="", phase="final", seed_words=[],
        short_mode=False, with_tools=False, work="main")
    assert called.get("yes"), "v1 链必须调用 _avoid_directive(S-007 防回归)"


# ---------- Creative Context Engine 失败必须 fail-loud，不回退旧链 ----------

def test_unified_context_failure_propagates_without_legacy_fallback(store, monkeypatch):
    import scribe3.app as appmod

    def _boom(*a, **k):
        raise RuntimeError("boom")

    before = appmod._context_assembler_fallbacks
    monkeypatch.setattr(appmod, "_assemble_write_instructions_v1", _boom)
    with pytest.raises(RuntimeError, match="boom"):
        appmod._assemble_write_instructions(
            store, chapter=1, focalizer="", phase="draft", seed_words=[],
            short_mode=False, with_tools=False, work="main")
    assert appmod._context_assembler_fallbacks == before


# ---------- envelope_hash / trace manifest:不含正文秘密 ----------

def test_envelope_hash_is_recipe_identity_not_text(store, snapshot):
    r = FakeRetriever.with_conflicting_episode_and_fact()
    a = ContextAssembler(store, r, token_budget=10_000)
    e1 = a.assemble(snapshot, "q", "discussion")
    e2 = a.assemble(snapshot, "q", "discussion")
    assert e1.envelope_hash == e2.envelope_hash          # 同配方 → 同 hash
    assert len(e1.envelope_hash) == 64                   # sha256 hex


def test_trace_manifest_excludes_secret_values(store):
    store.add_entity(Entity("role:jia", "character", "甲"))
    store.add_fact(Fact("fact:sec", "role:jia", "真身", "甲其实是狐妖",
                        valid_from=1, secret=True))
    store.add_knowledge(KnowledgeEdge("role:jia", "fact:sec", since_chapter=1))
    snap = _snapshot(focalizer="role:jia", chapter=2)
    env = ContextAssembler(store, None, token_budget=10_000).assemble(
        snap, "甲是谁", "write")
    manifest = envelope_trace_manifest(env)
    blob = json.dumps(manifest, ensure_ascii=False)
    assert "甲其实是狐妖" not in blob                  # secret value 绝不进 trace
    assert manifest["envelope_hash"] == env.envelope_hash
    assert manifest["snapshot_hash"] == snap.context_hash
    assert manifest["snapshot_revision"] == snap.revision
    # 每块只记 token + source id,不记正文
    assert all("text" not in b for b in manifest["blocks"])
