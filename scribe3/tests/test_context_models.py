"""Task 2 · 不可变 ContextSnapshot 与主编线程合同(纯类型层)。

这些 Pydantic 合同是统一上下文与记忆系统的地基:
Task 3(CAS 存储)/ Task 4(Context API)/ Task 7(assembler)都直接 import。
此处只验类型合同本身:完整性校验、稳定 hash、枚举拒绝、异常携带字段。
不碰 store/llm,不需要 SurrealDB。
"""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from scribe3.context_models import (
    ContextBlock,
    ContextEnvelope,
    ContextFocus,
    ContextSnapshot,
    ContextSource,
    NavigationIntent,
    StaleContextError,
)


def make_focus(focus_id: str = "role:a", type_: str = "character") -> ContextFocus:
    return ContextFocus(type=type_, id=focus_id, label="焦点")


def snapshot(*, focus_id: str = "role:a", work: str = "book-a", chapter: int | None = 3) -> ContextSnapshot:
    """构造一份完整快照并算好 hash——测试里所有比较都基于 with_hash 后的结果。"""
    snap = ContextSnapshot(
        session_id="ctx-1",
        work=work,
        revision=2,
        thread_id="thread-a",
        entry="codex",
        directory_path=["codex", "characters"],
        focus=make_focus(focus_id),
        detail_route=f"character:{focus_id}",
        chapter=chapter,
        phase="draft",
        focalizer=None,
        previous_revision=1,
        navigation_id="nav-1",
        captured_at=datetime.now(timezone.utc),
        context_hash="",
    )
    return snap.with_hash()


# ---------- 快照完整性 ----------

def test_snapshot_requires_one_complete_semantic_state():
    # focus 是快照语义状态的核心,缺失(None)必须拒绝——不允许"半份上下文"入库
    with pytest.raises(ValidationError):
        ContextSnapshot(
            session_id="ctx-1", work="book-a", revision=2,
            thread_id="thread-a", entry="codex", focus=None,
            detail_route="character:role:a", context_hash="",
        )


def test_snapshot_rejects_negative_revision():
    snap = snapshot()  # 辅助构造放在 raises 块外,避免它自身抛错造成假绿
    with pytest.raises(ValidationError):
        ContextSnapshot(**{**snap.canonical_payload(), "revision": -1,
                           "captured_at": snap.captured_at, "context_hash": ""})


# ---------- hash 语义:变则变、稳则稳、work 隔离 ----------

def test_snapshot_hash_changes_when_focus_changes():
    a = snapshot(focus_id="role:a")
    b = snapshot(focus_id="role:b")
    assert a.context_hash != b.context_hash


def test_snapshot_hash_changes_when_work_changes():
    # work 隔离:两个作品即便其余状态全同,hash 也必须不同
    a = snapshot(work="book-a")
    b = snapshot(work="book-b")
    assert a.context_hash != b.context_hash


def test_snapshot_hash_stable_for_same_payload():
    a = snapshot()
    assert a.with_hash().context_hash == a.context_hash


def test_snapshot_hash_ignores_captured_at():
    # captured_at 是墙钟噪声,不参与语义等价判断
    a = snapshot()
    later = a.model_copy(update={"captured_at": datetime(2030, 1, 1, tzinfo=timezone.utc)}).with_hash()
    assert later.context_hash == a.context_hash


def test_snapshot_hash_is_sha256_hex():
    h = snapshot().context_hash
    assert len(h) == 64 and int(h, 16) >= 0


def test_snapshot_golden_hash_regression():
    """黄金 hash 守卫:固定构造 → 硬编码期望值。
    Pydantic 升级改序列化、或 canonical_payload 加/删字段时这条第一时间报警——
    库里已存的 context_hash 一旦与新算法不一致,过期检测(409)会全面误判。"""
    snap = ContextSnapshot(
        session_id="ctx-golden", work="book-golden", revision=7,
        thread_id="thread-golden", entry="codex",
        directory_path=["codex", "characters"],
        focus=ContextFocus(type="character", id="role:golden", label="金标"),
        detail_route="character:role:golden", chapter=12, phase="draft",
        focalizer="role:golden", previous_revision=6, navigation_id="nav-golden",
        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc), context_hash="",
    ).with_hash()
    assert snap.context_hash == "390bb0215284b3e9f221619aa6d8e188db1a9408161e919a3bd5661c3c04ca53"


# ---------- 不可变性:hash 指纹不许被击穿 ----------

def test_snapshot_is_frozen():
    snap = snapshot()
    with pytest.raises(ValidationError):
        snap.work = "book-b"


def test_focus_is_frozen():
    focus = make_focus()
    with pytest.raises(ValidationError):
        focus.label = "改名"


def test_snapshot_rejects_invalid_phase():
    # 快照要持久化,phase 必须落在枚举内——垃圾 phase 不能入库
    snap = snapshot()
    with pytest.raises(ValidationError):
        ContextSnapshot(**{**snap.canonical_payload(), "phase": "revise",
                           "captured_at": snap.captured_at, "context_hash": ""})


# ---------- ContextFocus / NavigationIntent 枚举合同 ----------

def test_context_focus_rejects_invalid_type():
    with pytest.raises(ValidationError):
        ContextFocus(type="galaxy", id="x")


def test_context_focus_accepts_quality_review():
    focus = ContextFocus(type="quality_review", id="quality:3", label="质量审阅")
    assert focus.type == "quality_review"
    assert focus.id == "quality:3"


def make_intent(**overrides) -> NavigationIntent:
    payload = dict(
        navigation_id="nav-1",
        expected_revision=2,
        entry="codex",
        focus=make_focus(),
        detail_route="character:role:a",
        reason="item",
    )
    payload.update(overrides)
    return NavigationIntent(**payload)


def test_navigation_intent_accepts_minimal_payload():
    intent = make_intent()
    assert intent.directory_path == []
    assert intent.chapter is None and intent.phase is None


def test_navigation_intent_rejects_invalid_reason():
    with pytest.raises(ValidationError):
        make_intent(reason="teleport")


def test_navigation_intent_rejects_invalid_phase():
    with pytest.raises(ValidationError):
        make_intent(phase="revise")


def test_navigation_intent_directory_path_defaults_are_isolated():
    # Pydantic v2 对可变默认值做每实例深拷贝——守住这个前提
    a, b = make_intent(), make_intent()
    a.directory_path.append("codex")
    assert b.directory_path == []


# ---------- Envelope 块级溯源 ----------

def test_envelope_basic_construction():
    snap = snapshot()
    block = ContextBlock(
        name="canonical",
        text="甲在第3章已知乙的身世。",
        token_estimate=12,
        sources=[ContextSource(source_id="fact:1", source_kind="fact", work="book-a")],
    )
    env = ContextEnvelope(
        snapshot=snap,
        blocks=[block],
        total_token_estimate=12,
        omitted=[{"source_id": "fact:2", "reason": "limited_pov"}],
        assembled_at=datetime.now(timezone.utc),
        envelope_hash="",
    )
    assert env.blocks[0].sources[0].masked is False
    assert env.omitted[0]["reason"] == "limited_pov"


def test_context_block_rejects_invalid_name():
    with pytest.raises(ValidationError):
        ContextBlock(name="misc", text="x", token_estimate=1, sources=[])


def test_token_estimates_reject_negative():
    with pytest.raises(ValidationError):
        ContextBlock(name="focus", text="x", token_estimate=-1, sources=[])
    snap = snapshot()
    with pytest.raises(ValidationError):
        ContextEnvelope(
            snapshot=snap, blocks=[], total_token_estimate=-5,
            omitted=[], assembled_at=datetime.now(timezone.utc), envelope_hash="",
        )


# ---------- StaleContextError ----------

def test_stale_context_error_carries_revisions():
    err = StaleContextError(expected=3, actual=5, latest={"revision": 5, "navigation_id": "nav-9"})
    assert err.expected == 3
    assert err.actual == 5
    assert err.latest["navigation_id"] == "nav-9"
    assert isinstance(err, Exception)


def test_stale_context_error_latest_optional():
    err = StaleContextError(expected=1, actual=2)
    assert err.latest is None


def test_stale_context_error_has_stable_code():
    # Task 4 API 层映射 409 时直接透传的错误码,值一旦发布不许再改
    assert StaleContextError.code == "stale_context"
