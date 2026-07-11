"""统一上下文与记忆系统 · Task 13:Runs/审批链回作品级主编线程 + 审批前重校验发起时快照。

现有 ai-runs 端点行为测试在 test_hermes_runtime.py;本文件专测【context 绑定 + 审批重校验】:
- 发起 run 时记 parent_thread_id + 发起时上下文快照(session/revision/hash/focus);
- 审批前对比 run 的 origin_context_revision 与【当前】session revision:
    · 未变 → 按原审批执行,记 completion_context_revision + write_effects;
    · 已变且影响当前章/条目 → 409 run_context_changed(原审批作废);
    · 已变但写目标与当前焦点无关 → 需 approve_stale=true 二次确认才执行;
- 刷新恢复只依 run_id + parent_thread_id(GET /ai/runs/{id}/trace),不依赖任何进程内 state。

限知红线:审批重校验是【新增前置】,校验通过后原 approve 流程一字不改;Runs 隔离
(_run_session_key)与 approval 三态不变。测试用真内存 SurrealDB(store 夹具)+ FakeRuntime
桩掉真实 Hermes 网关(绝不烧真 LLM)。
"""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

WORK = "book-a"


class _FakeRuntime:
    """桩掉 Hermes Runs 网关:create/approve/status/stop 都返回稳定结构,不发网络。"""

    def create_run(self, input_text, **kwargs):
        return {"run_id": "run_ctx_1", "status": "queued"}

    def approve_run(self, run_id, approval, **kwargs):
        return {"run_id": run_id, "status": "resumed"}

    def run_status(self, run_id, **kwargs):
        return {"run_id": run_id, "status": "waiting_for_approval"}

    def stop_run(self, run_id, **kwargs):
        return {"run_id": run_id, "status": "stopped"}


def _navigate(store, session_id, expected_rev, *, chapter, focus_id=None):
    """把上下文会话推进一版(CAS);focus 落在指定章。返回新快照 dict。"""
    intent = {
        "navigation_id": uuid4().hex,
        "expected_revision": expected_rev,
        "entry": "chapter",
        "directory_path": [],
        "focus": {
            "type": "chapter",
            "id": focus_id or f"chapter:{chapter}",
            "label": f"第 {chapter} 章",
        },
        "detail_route": f"chapter:{chapter}",
        "chapter": chapter,
        "phase": None,
        "focalizer": None,
        "reason": "item",
    }
    return store.advance_context(session_id, intent)


def advance_context(context_session, *, chapter=9, focus=None):
    """测试语义助手:把会话焦点推进到某章(默认第 9 章,焦点保持同章、revision 前进)。"""
    store = context_session.store
    snap = store.get_context_snapshot(context_session.id)
    return _navigate(store, context_session.id, snap["revision"], chapter=chapter, focus_id=focus)


@pytest.fixture
def ctx_env(store, monkeypatch):
    import scribe3.app as appmod

    appmod.set_store(store, work=WORK)
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda: _FakeRuntime())
    client = TestClient(appmod.app)
    # 建会话并推进到 revision=8,焦点稳定在第 9 章(run 将绑定在 rev8 · 焦点 chapter:9)。
    session = store.create_context_session(WORK, "author", "dev")
    sid = session["session_id"]
    for rev in range(8):
        _navigate(store, sid, rev, chapter=9)
    return SimpleNamespace(client=client, store=store, session_id=sid)


@pytest.fixture
def client(ctx_env):
    return ctx_env.client


@pytest.fixture
def context_session(ctx_env):
    return SimpleNamespace(id=ctx_env.session_id, store=ctx_env.store)


@pytest.fixture
def run(ctx_env):
    """在 revision=8 · 焦点第 9 章 处发起 run;approval_id 由事件流给,测试里用固定桩值。"""
    resp = ctx_env.client.post(f"/ai/runs?work={WORK}", json={
        "input": "整理第 9 章的设定",
        "instructions": "先核实再写入",
        "context_session_id": ctx_env.session_id,
        "context_revision": 8,
    })
    assert resp.status_code == 200
    return SimpleNamespace(id=resp.json()["run_id"], approval_id="ap_ctx_1")


# ---------------------------------------------------------------------------
# Step 1(计划原文):旧 run 不得写新焦点——审批前重校验发起时上下文
# ---------------------------------------------------------------------------

def test_run_approval_rechecks_origin_context_before_write(client, run, context_session):
    advance_context(context_session, chapter=9, focus="chapter:9")   # 焦点前进(同章、revision 变)
    response = client.post(f"/ai/runs/{run.id}/approval?work={WORK}", json={
        "approval_id": run.approval_id,
        "decision": "approve",
        "context_session_id": context_session.id,
        "context_revision": 9,
    })
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "run_context_changed"


def test_run_approval_unchanged_executes_and_records_write_effects(client, run, context_session):
    """快照未变(origin revision == 当前 session revision):按原审批执行,记 write_effects。"""
    response = client.post(f"/ai/runs/{run.id}/approval?work={WORK}", json={
        "approval_id": run.approval_id,
        "decision": "approve",
        "context_session_id": context_session.id,
        "context_revision": 8,
    })
    assert response.status_code == 200
    trace = context_session.store.get_ai_run_trace(run.id)
    assert trace["completion_context_revision"] == 8
    assert trace["write_effects"], "未变执行必须留下 write_effects 台账"


def test_run_approval_unrelated_focus_needs_approve_stale(client, run, context_session):
    """快照已变但写目标(第 9 章)与当前焦点(第 3 章)无关:需 approve_stale=true 二次确认。"""
    advance_context(context_session, chapter=3, focus="chapter:3")   # 换到不相干的第 3 章
    first = client.post(f"/ai/runs/{run.id}/approval?work={WORK}", json={
        "approval_id": run.approval_id,
        "decision": "approve",
        "context_session_id": context_session.id,
        "context_revision": 9,
    })
    assert first.status_code == 409
    assert first.json()["detail"]["code"] == "run_context_stale"

    second = client.post(f"/ai/runs/{run.id}/approval?work={WORK}", json={
        "approval_id": run.approval_id,
        "decision": "approve",
        "approve_stale": True,
        "context_session_id": context_session.id,
        "context_revision": 9,
    })
    assert second.status_code == 200


def test_run_deny_never_blocked_by_stale_context(client, run, context_session):
    """拒绝旧 run 永远安全(不写入):即使焦点已变也不触发 409。"""
    advance_context(context_session, chapter=9, focus="chapter:9")
    response = client.post(f"/ai/runs/{run.id}/approval?work={WORK}", json={
        "approval_id": run.approval_id,
        "decision": "deny",
        "context_session_id": context_session.id,
        "context_revision": 9,
    })
    assert response.status_code == 200


def test_run_trace_carries_parent_thread_and_origin_for_recovery(client, run, context_session):
    """刷新恢复只依 run_id + parent_thread_id:发起时快照必须完整落在 trace 上供 GET 重建。"""
    trace_resp = client.get(f"/ai/runs/{run.id}/trace?work={WORK}")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    assert trace["parent_thread_id"], "run 必须链回作品级主编线程"
    assert trace["context_session_id"] == context_session.id
    assert trace["origin_context_revision"] == 8
    assert trace["origin_context_hash"], "发起时 context_hash 必须留痕"
    assert (trace.get("focus") or {}).get("id") == "chapter:9"


def test_run_approval_fail_closed_when_origin_unverifiable(client):
    """I-3 fail-closed:origin 只绑 revision 没绑 session(核实不了当前快照)→ 审批保守作废,
    绝不回退信任审批自报的 revision 放行。"""
    created = client.post(f"/ai/runs?work={WORK}", json={
        "input": "登记一条命题",
        "context_revision": 8,   # 只报 revision,不报 session_id → 后端无法核实
    })
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    approval = client.post(f"/ai/runs/{run_id}/approval?work={WORK}", json={
        "approval_id": "ap_x",
        "decision": "approve",
        "context_revision": 8,   # 审批自报同 revision:fail-closed 下也不放行
    })
    assert approval.status_code == 409
    assert approval.json()["detail"]["code"] == "run_context_changed"


def test_run_approval_write_effects_idempotent_on_replay(client, run, context_session):
    """Minor:同一审批重放不叠重复 write_effects 台账(按 approval_id/revision/kind 去重)。"""
    body = {"approval_id": run.approval_id, "decision": "approve",
            "context_session_id": context_session.id, "context_revision": 8}
    assert client.post(f"/ai/runs/{run.id}/approval?work={WORK}", json=body).status_code == 200
    assert client.post(f"/ai/runs/{run.id}/approval?work={WORK}", json=body).status_code == 200
    trace = context_session.store.get_ai_run_trace(run.id)
    approval_effects = [e for e in (trace.get("write_effects") or []) if e.get("kind") == "approval"]
    assert len(approval_effects) == 1


def test_run_without_context_binding_keeps_legacy_approval(store, monkeypatch):
    """无 context 绑定的 run(存量/旧前端)审批不被重校验拦截——现有行为零回归。"""
    import scribe3.app as appmod

    appmod.set_store(store, work=WORK)
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda: _FakeRuntime())
    client = TestClient(appmod.app)
    created = client.post(f"/ai/runs?work={WORK}", json={"input": "登记一条命题"})
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    approval = client.post(f"/ai/runs/{run_id}/approval?work={WORK}", json={
        "approval_id": "ap_legacy",
        "decision": "approve",
    })
    assert approval.status_code == 200
