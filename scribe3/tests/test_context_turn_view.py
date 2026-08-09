"""B∪C ContextTurnView 合同：纯逻辑 + 写/讨论编译 roundtrip（不依赖本机 Surreal 全量 schema）。

本机 Grok 跑 Surreal 2.3.7 时 type::record 参数序与 demo 3.x 相反，conftest 全量
apply_schema 不可靠；本文件用 MiniStore 驱动**已交付**的 assemble / bind / view 函数。
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from scribe3.context_turn_view import (
    BLOCK_ORDER,
    build_turn_view,
    not_compiled_view,
    view_from_bind_row,
    merge_memory_trace_into_view,
)


def test_not_compiled_has_no_fake_zero_blocks():
    v = not_compiled_view(session_id="s1", revision=3)
    assert v["available"] is False
    assert v["availability"] == "not_compiled_yet"
    assert "block_tokens" not in v
    assert "blocks" not in v


def test_build_turn_view_eight_blocks_from_envelope():
    class _Src:
        def __init__(self, sid):
            self.source_id = sid
            self.masked = False

    class _Block:
        def __init__(self, name, tok, sids):
            self.name = name
            self.token_estimate = tok
            self.sources = [_Src(s) for s in sids]
            self.text = "x" * tok

    class _Env:
        blocks = [
            _Block("focus", 10, ["f1"]),
            _Block("global", 50, ["g1", "g2"]),
            _Block("canonical", 100, ["c1"]),
            _Block("recent", 0, []),
            _Block("procedural", 0, []),
            _Block("reference", 0, []),
            _Block("uncertainty", 0, []),
            _Block("provenance", 30, ["p1"]),
        ]
        envelope_hash = "eh"

    v = build_turn_view(
        session_id="sess-a", revision=2, work="w1",
        task_kind="draft", path="write", envelope=_Env(),
        manifest_id="m1", actual_input_hash="aih",
    )
    assert v["available"] is True
    assert v["availability"] == "ready"
    assert set(v["block_tokens"]) >= set(BLOCK_ORDER)
    assert v["block_tokens"]["global"] == 50
    assert v["block_tokens"]["canonical"] == 100
    g = next(b for b in v["blocks"] if b["name"] == "global")
    assert g["source_count"] == 2
    assert g["source_ids"] == ["g1", "g2"]
    assert v["manifest_id"] == "m1"


def test_view_from_bind_row_ready():
    row = {
        "work": "w",
        "context_session_id": "s",
        "snapshot_revision": 9,
        "task_kind": "discussion",
        "path": "discuss",
        "availability": "ready",
        "block_tokens": {"global": 12, "canonical": 0},
        "blocks": [
            {"name": "global", "token_estimate": 12, "source_ids": ["a"], "source_count": 1},
        ],
        "selected": [],
        "rejected": [],
        "manifest_id": "mm",
        "actual_input_hash": "hh",
    }
    v = view_from_bind_row(row, session_id="s", revision=9)
    assert v["available"] is True
    assert v["task_kind"] == "discussion"
    assert v["block_tokens"]["global"] == 12


def test_merge_memory_trace_prefers_selected_detail():
    view = build_turn_view(
        session_id="s", revision=1, work="w",
        envelope=SimpleNamespace(blocks=[], envelope_hash="e"),
        selected=[],
    )
    # force ready with empty blocks still available
    view["available"] = True
    view["block_tokens"] = {"global": 5}
    view["blocks"] = [{"name": "global", "token_estimate": 5, "source_ids": [], "source_count": 0}]
    merged = merge_memory_trace_into_view(view, {
        "selected": [{"source_id": "mem:1", "text": "hit"}],
        "rejected": [{"source_id": "mem:2", "reason": "token_budget"}],
        "channels": {"bm25": 1},
        "query": "q",
    })
    assert merged["selected"][0]["source_id"] == "mem:1"
    assert merged["rejected"][0]["reason"] == "token_budget"
    assert merged["channels"]["bm25"] == 1


# ---------- MiniStore：驱动真实 assemble / bind，不启全量 Surreal schema ----------

class _MiniStore:
    """足够通过 CreativeContextEngine + assembler 的最小 store 鸭子类型。"""

    def __init__(self):
        self.db_name = "test"
        self._binds: dict[tuple[str, int], dict] = {}
        self._traces: dict[tuple[str, int], dict] = {}
        self._intents = {
            "reader_feeling": "冷", "emotional_arc": "沉", "red_lines": "禁AI腔",
        }

    def __getattr__(self, name):
        # 写路径大量可选 list_* / recall_*：缺方法时 fail-soft 空结果
        if name.startswith(("list_", "recall_", "get_", "open_", "promises")):
            return lambda *a, **k: [] if not name.startswith("get_") else {}
        raise AttributeError(name)

    def get_intent(self):
        return dict(self._intents)

    def characters(self):
        return [SimpleNamespace(name="甲", id="role:jia")]

    def facts_at(self, chapter=None, **kw):
        return []

    def open_promises(self):
        return []

    def list_materials(self):
        return []

    def list_craft_rules(self):
        return []

    def list_voice_profiles(self):
        return []

    def get_chapter(self, seq):
        return {"synopsis": "城东开场", "title": "一", "scene_truth": "", "draft": ""}

    def recent_proses(self, chapter, k=3):
        return []

    def promises_with_lifecycle(self, *a, **k):
        return []

    def list_motifs(self, **kw):
        return []

    def list_events(self, **kw):
        return []

    def promises(self, **kw):
        return []

    def list_knowledge_edges(self, **kw):
        return []

    def project_frame(self, *a, **k):
        return SimpleNamespace(facts=[])

    def _query(self, *a, **k):
        return []

    def _execute_write(self, *a, **k):
        return None

    def transaction(self):
        from contextlib import nullcontext
        return nullcontext()

    def save_context_turn_bind(self, view: dict) -> str:
        from scribe3.store import mask_memory_trace
        sid = str(view.get("context_session_id") or view.get("session_id"))
        rev = int(view.get("snapshot_revision"))
        masked = mask_memory_trace({
            "selected": view.get("selected") or [],
            "rejected": view.get("rejected") or [],
        })
        row = dict(view)
        row["selected"] = masked.get("selected") or []
        row["rejected"] = masked.get("rejected") or []
        self._binds[(sid, rev)] = row
        return f"ctb:{sid}:{rev}"

    def get_context_turn_bind(self, session_id: str, revision: int):
        return self._binds.get((session_id, int(revision)))

    def save_memory_trace(self, trace: dict) -> str:
        from scribe3.store import mask_memory_trace
        t = mask_memory_trace(trace)
        key = (str(t.get("context_session_id")), int(t.get("snapshot_revision") or 0))
        self._traces[key] = t
        return str(t.get("trace_id") or "mt")

    def get_memory_trace_for_snapshot(self, session_id: str, revision: int):
        return self._traces.get((session_id, int(revision)))

    def _secret_proposition_values(self):
        return set()


@pytest.fixture()
def mini_store(monkeypatch):
    st = _MiniStore()
    # fabric 开：retriever 可无候选，仍应落 TurnBind
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "0")
    try:
        from scribe3 import settings as S
        S.invalidate_cache()
    except Exception:
        pass
    # ContextStore.save_manifest 需要真实 Surreal 时 fail soft 不在 compile 路径硬依赖
    # 我们让 ContextStore.save_manifest 成为 no-op 成功
    from scribe3.context_store import ContextStore

    def _save(self, manifest):
        return manifest

    monkeypatch.setattr(ContextStore, "save_manifest", _save)
    # MemoryRetriever：返回空 RetrievalResult
    from scribe3.memory_models import RetrievalResult

    class _R:
        def retrieve(self, *a, **k):
            return []

        def retrieve_full_cached(self, q):
            return RetrievalResult(selected=[])

    monkeypatch.setattr(
        "scribe3.api.services.write_stream._get_write_retriever",
        lambda st: _R(),
    )
    return st


def test_write_bind_roundtrip_real_assemble(mini_store):
    """带 session+revision 的真实写作组装 → TurnBind 就绪且至少一块 token>0。"""
    import scribe3.app as A
    A.set_store(mini_store, work="test")

    ctx = {
        "context_session_id": "sess-round",
        "context_revision": 5,
        "context_hash": "a" * 64,
        "thread_id": "th-1",
    }
    instr = A._assemble_write_instructions(
        mini_store, chapter=1, focalizer="", phase="draft",
        seed_words=["城东"], short_mode=False, work="test",
        memory_trace_ctx=ctx, request_text="写甲在城东的一幕",
    )
    assert isinstance(instr, str) and len(instr) > 20
    assert "⟦PROPOSAL" in instr or "作者视角" in instr or "主编" in instr

    bind = mini_store.get_context_turn_bind("sess-round", 5)
    assert bind is not None, "写作编译后必须落 TurnBind"
    assert bind.get("block_tokens"), "必须有块 token"
    assert any(int(v or 0) > 0 for v in (bind.get("block_tokens") or {}).values())
    assert bind.get("manifest_id") or bind.get("actual_input_hash")
    assert bind.get("task_kind") in ("draft", "final")

    view = view_from_bind_row(bind, session_id="sess-round", revision=5)
    assert view["available"] is True
    assert view["availability"] == "ready"
    assert any(int(v or 0) > 0 for v in view["block_tokens"].values())


def test_discussion_compile_no_proposal_and_bind(mini_store):
    """讨论单编译：无写作围栏；TurnBind task_kind=discussion。"""
    from scribe3.api.services.write_assemble import assemble_discussion_system

    ctx = {
        "context_session_id": "sess-d",
        "context_revision": 1,
        "context_hash": "b" * 64,
        "thread_id": "th-d",
    }
    text = assemble_discussion_system(
        mini_store, work="test", chapter=1, user_msg="乙的性格怎么写更冷？",
        memory_trace_ctx=ctx,
        pulse_text="【脉搏】无超期",
        directive_text="【讨论指令】只讨论不写稿",
    )
    # 讨论 banner 会提到「不得输出 ⟦PROPOSAL⟧」作禁令；不得出现写作围栏协议正文
    assert "⟦PROPOSAL scope=" not in text
    assert "绝对禁止输出 ⟦PROPOSAL⟧" not in text
    assert "讨论" in text or "主编" in text

    bind = mini_store.get_context_turn_bind("sess-d", 1)
    assert bind is not None
    assert bind.get("task_kind") == "discussion"
    assert bind.get("path") == "discuss"
    assert any(int(v or 0) > 0 for v in (bind.get("block_tokens") or {}).values())


def test_secret_masked_in_turn_bind_selected(mini_store):
    """secret 条目写入 bind 前经 mask，明文不出现。"""
    from scribe3.api.services.write_stream import _save_context_turn_bind
    from scribe3.context_turn_view import build_turn_view

    secret_val = "SECRET_TRUE_NAME_XYZ"
    env = SimpleNamespace(
        blocks=[],
        envelope_hash="e",
    )
    # 手工构造带 secret 的 view 走 save
    view = build_turn_view(
        session_id="sess-sec", revision=2, work="test",
        envelope=env,
        selected=[{
            "source_id": "fact:sec", "source_kind": "canonical",
            "secret": True, "text": secret_val, "reason": "canonical",
        }],
    )
    mini_store.save_context_turn_bind(view)
    row = mini_store.get_context_turn_bind("sess-sec", 2)
    blob = str(row.get("selected") or [])
    assert secret_val not in blob


def test_api_context_trace_get_uses_turn_bind(mini_store, monkeypatch):
    """GET trace 聚合：有 TurnBind → available ready；无 → not_compiled 诚实。"""
    import scribe3.app as A
    from fastapi.testclient import TestClient
    from scribe3.context_service import ContextService, ContextServiceError

    A.set_store(mini_store, work="test")
    # 注入 bind
    mini_store.save_context_turn_bind(build_turn_view(
        session_id="sess-api", revision=3, work="test",
        envelope=SimpleNamespace(
            blocks=[SimpleNamespace(
                name="global", token_estimate=42, sources=[], text="g" * 42,
            )],
            envelope_hash="h",
        ),
        task_kind="draft",
        manifest_id="mid",
        actual_input_hash="aih",
    ))

    # 绕过 ContextService 对不存在 session 的校验：有 bind 时 API 不强制 session 表
    c = TestClient(A.app)
    r = c.get("/context/sessions/sess-api/trace/3?work=test")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("available") is True
    assert body.get("availability") == "ready"
    assert body.get("block_tokens", {}).get("global") == 42

    # 无 bind：需要 ContextService 确认 session；mock get 成功 → not_compiled
    def _fake_get(self, session_id, work, revision=None):
        return {"session_id": session_id, "revision": revision or 0, "work": work}

    monkeypatch.setattr(ContextService, "get", _fake_get)
    r2 = c.get("/context/sessions/empty/trace/0?work=test")
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2.get("available") is False
    assert b2.get("availability") == "not_compiled_yet"
    assert "block_tokens" not in b2
