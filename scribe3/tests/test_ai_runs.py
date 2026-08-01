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
import threading
import time
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

WORK = "book-a"


class _FakeRuntime:
    """桩掉 Hermes Runs 网关:create/approve/status/stop 都返回稳定结构,不发网络。"""

    def __init__(self):
        self._created = 0

    def create_run(self, input_text, **kwargs):
        self._created += 1
        return {"run_id": f"run_ctx_{self._created}", "status": "queued"}

    def approve_run(self, run_id, approval, **kwargs):
        return {"run_id": run_id, "status": "resumed"}

    def run_status(self, run_id, **kwargs):
        return {"run_id": run_id, "status": "waiting_for_approval"}

    def run_events(self, run_id, **kwargs):
        return iter(())

    def stop_run(self, run_id, **kwargs):
        return {"run_id": run_id, "status": "stopped"}


class _CompletedRunStopRuntime(_FakeRuntime):
    """模拟 Hermes 已清理完成 run 后，stop 返回 404 的真实网关语义。"""

    def stop_run(self, run_id, **kwargs):
        request = httpx.Request("POST", f"http://hermes.test/runs/{run_id}/stop")
        response = httpx.Response(404, request=request, text="run not found")
        raise httpx.HTTPStatusError("run not found", request=request, response=response)


class _CompletedRunStop400Runtime(_FakeRuntime):
    """真实 Hermes 对已回收 Run 可能以 400/run_not_found 回应，而非 404。"""

    def stop_run(self, run_id, **kwargs):
        request = httpx.Request("POST", f"http://hermes.test/runs/{run_id}/stop")
        response = httpx.Response(
            400, request=request,
            json={"error": {"code": "run_not_found", "message": f"Run not found: {run_id}"}},
        )
        raise httpx.HTTPStatusError("run not found", request=request, response=response)


class _EventsPrunedAfterRemoteCompletionRuntime(_FakeRuntime):
    """Hermes 已确认 Run 完成，但事件流在审计尾部被回收。"""

    def run_events(self, run_id, **kwargs):
        request = httpx.Request("GET", f"http://hermes.test/runs/{run_id}/events")
        response = httpx.Response(404, request=request, text="run events not found")
        raise httpx.HTTPStatusError("run events not found", request=request, response=response)

    def run_status(self, run_id, **kwargs):
        return {"run_id": run_id, "status": "completed", "last_event": "run.completed"}


class _RemoteCompletedWithoutEventsRuntime(_EventsPrunedAfterRemoteCompletionRuntime):
    """状态端点已 completed，但网关不再提供任何可审计事件。"""

    def run_events(self, run_id, **kwargs):
        return iter(())


class _PrunedRunStatusRuntime(_FakeRuntime):
    """Hermes 已回收完成 Run 后，状态查询也可能返回 404。"""

    def run_status(self, run_id, **kwargs):
        request = httpx.Request("GET", f"http://hermes.test/runs/{run_id}")
        response = httpx.Response(404, request=request, text="run not found")
        raise httpx.HTTPStatusError("run not found", request=request, response=response)


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
    runtime = _FakeRuntime()
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: runtime)
    client = TestClient(appmod.app)
    # 建会话并推进到 revision=8,焦点稳定在第 9 章(run 将绑定在 rev8 · 焦点 chapter:9)。
    session = store.create_context_session(WORK, "author", "dev")
    sid = session["session_id"]
    for rev in range(8):
        _navigate(store, sid, rev, chapter=9)
    return SimpleNamespace(client=client, store=store, session_id=sid, runtime=runtime)


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


def test_run_scope_isolates_stage_conversations(client, ctx_env):
    """不同章节阶段不得复用同一个 Hermes run 会话，避免工具游走和上下文无限累积。"""
    first = client.post(f"/ai/runs?work={WORK}", json={
        "input": "写演绎", "run_scope": "chapter:1:deduce",
    })
    second = client.post(f"/ai/runs?work={WORK}", json={
        "input": "写演绎", "run_scope": "chapter:2:deduce",
    })
    assert first.status_code == second.status_code == 200
    first_key = ctx_env.store.get_ai_run_trace(first.json()["run_id"])["session_key"]
    second_key = ctx_env.store.get_ai_run_trace(second.json()["run_id"])["session_key"]
    assert first_key != second_key


def test_deduce_run_selects_restricted_gateway_and_persists_stage_policy(client, ctx_env, monkeypatch):
    """章节演绎必须进入受限 profile，而不是只换 session key 后仍进完整写网关。"""
    import scribe3.app as appmod

    selected = []

    def runtime_for(policy=None):
        selected.append(policy)
        return ctx_env.runtime

    monkeypatch.setattr(appmod, "_hermes_runs_runtime", runtime_for)
    response = client.post(f"/ai/runs?work={WORK}", json={
        "input": "演绎第 1 章", "run_scope": "chapter:1:deduce",
    })

    assert response.status_code == 200
    assert selected and selected[0].profile == "scribe3_deduce"
    trace = ctx_env.store.get_ai_run_trace(response.json()["run_id"])
    assert trace["stage_policy"] == {
        "phase": "deduce",
        "profile": "scribe3_deduce",
        "allowed_tools": sorted(selected[0].allowed_tools),
        "max_tool_calls": 12,
        "required_tools": ["s3_patch_chapter_plan"],
    }

    preview = client.post(f"/ai/runs?work={WORK}", json={
        "input": "生成第 1 章演绎预览", "run_scope": "chapter:1:deduce_preview",
    })
    assert preview.status_code == 200
    preview_trace = ctx_env.store.get_ai_run_trace(preview.json()["run_id"])
    assert "mcp__scribe3_read__s3_get_chapter" in preview_trace["instructions"]
    assert "搜索或描述后不得结束 Run" in preview_trace["instructions"]


def test_unknown_chapter_run_phase_fails_closed_before_creating_run(client, ctx_env):
    response = client.post(f"/ai/runs?work={WORK}", json={
        "input": "随意做点事", "run_scope": "chapter:1:invent",
    })

    assert response.status_code == 422
    assert response.json()["detail"] == "unsupported chapter run phase"
    assert ctx_env.runtime._created == 0


def test_deduce_event_trace_fails_closed_on_out_of_policy_tool(client, ctx_env, monkeypatch):
    """即使网关配置漂移暴露了越权工具，服务端 trace 也必须将该 Run 判失败。"""
    import scribe3.app as appmod

    class DriftedRuntime:
        def __init__(self):
            self.event_session_key = None

        def create_run(self, _input, **_kwargs):
            return {"run_id": "run_deduce_drift", "status": "queued"}

        def run_events(self, _run_id, **kwargs):
            self.event_session_key = kwargs["session_key"]
            return iter([
                {"type": "tool.start", "name": "s3_add_character", "arguments": "{}", "call_id": "call_1"},
                {"type": "tool.complete", "call_id": "call_1", "output": '{"status":"written"}'},
                {"type": "run.completed", "run_id": "run_deduce_drift"},
            ])

    runtime = DriftedRuntime()
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: runtime)
    created = client.post(f"/ai/runs?work={WORK}", json={
        "input": "演绎第 1 章", "run_scope": "chapter:1:deduce",
    })
    assert created.status_code == 200

    events = client.get("/ai/runs/run_deduce_drift/events?work=book-a")
    assert events.status_code == 200
    trace = ctx_env.store.get_ai_run_trace("run_deduce_drift")
    assert runtime.event_session_key == "scribe3|work:book-a|chapter:1:deduce"
    assert trace["tool_calls"][0]["sequence"] == 1
    assert trace["status"] == "failed"
    assert {"code": "tool_not_allowed", "tool": "s3_add_character", "sequence": 1} in trace["policy_violations"]
    assert {"code": "required_tool_missing", "tool": "s3_patch_chapter_plan"} in trace["policy_violations"]


def test_explicit_book_write_tool_request_fails_when_run_only_claims_it_will_call(client, ctx_env, monkeypatch):
    """作品级写请求点名工具时，没有真实工具审计链绝不能终态假绿。

    本测试防住 TokenPlan/Hermes 的已复现行为：模型在普通文本里说“正在调用
    s3_add_chapter”，但 Hermes 没有产生任何 tool.started/tool.completed 事件。
    生产代码若移除书级工具合同，Run 会错误完成而本测试必须失败。
    """
    import scribe3.app as appmod

    class TextOnlyRuntime(_FakeRuntime):
        def create_run(self, _input, **_kwargs):
            return {"run_id": "run_book_claim_only", "status": "queued"}

        def run_events(self, run_id, **_kwargs):
            return iter([{
                "event": "run.completed", "run_id": run_id,
                "output": "我正在调用 s3_add_chapter，等待作者审批。",
            }])

    appmod.set_store(ctx_env.store, work=WORK)
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: TextOnlyRuntime())
    created = client.post(f"/ai/runs?work={WORK}", json={
        "input": "请调用 s3_add_chapter，新建第一章《潮声》并等待我审批。",
    })
    assert created.status_code == 200
    initial_trace = ctx_env.store.get_ai_run_trace("run_book_claim_only") or {}
    assert "mcp__scribe3_write__s3_add_chapter" in initial_trace["instructions"]
    assert "不得输出 <tool_call>" in initial_trace["instructions"]

    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        trace = ctx_env.store.get_ai_run_trace("run_book_claim_only") or {}
        if trace.get("status") == "failed":
            break
        time.sleep(0.01)

    trace = ctx_env.store.get_ai_run_trace("run_book_claim_only") or {}
    assert trace["status"] == "failed"
    assert {"code": "required_tool_missing", "tool": "s3_add_chapter"} in trace["policy_violations"]


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


def test_pending_deduce_approval_can_be_recovered_by_chapter_and_phase(client, ctx_env):
    """刷新恢复必须从持久 trace 找回当前章节的待审批，不依赖浏览器内存。"""
    ctx_env.store.upsert_ai_run_trace(
        "run_deduce_pending", status="waiting_for_approval",
        session_key="scribe3|work:book-a|chapter:3:deduce",
        approvals=[{
            "run_id": "run_deduce_pending", "approval_id": "approval_deduce_pending",
            "tool": "s3_patch_chapter_plan", "message": "允许写入第3章演绎？",
            "status": "requested",
        }],
    )
    ctx_env.store.update_ai_run_context("run_deduce_pending", stage_policy={
        "phase": "deduce", "profile": "scribe3_deduce",
        "allowed_tools": ["s3_get_chapter", "s3_patch_chapter_plan"],
        "max_tool_calls": 12, "required_tools": ["s3_patch_chapter_plan"],
    })
    # 同书但不同章、以及已决审批都不得在本章刷新时误恢复。
    ctx_env.store.upsert_ai_run_trace(
        "run_other_chapter", status="waiting_for_approval",
        session_key="scribe3|work:book-a|chapter:4:deduce",
        approvals=[{"approval_id": "approval_other", "status": "requested"}],
    )
    ctx_env.store.update_ai_run_context("run_other_chapter", stage_policy={"phase": "deduce"})
    ctx_env.store.upsert_ai_run_trace(
        "run_resolved", status="completed",
        session_key="scribe3|work:book-a|chapter:3:deduce",
        approvals=[{"approval_id": "approval_done", "decision": "approve", "status": "resolved"}],
    )
    ctx_env.store.update_ai_run_context("run_resolved", stage_policy={"phase": "deduce"})

    response = client.get("/ai/runs/pending-approvals?work=book-a&chapter=3&phase=deduce")

    assert response.status_code == 200
    assert response.json()["runs"] == [{
        "run_id": "run_deduce_pending",
        "approval_id": "approval_deduce_pending",
        "message": "允许写入第3章演绎？",
    }]


def test_pending_book_level_approval_can_be_recovered_without_chapter_scope(client, ctx_env):
    """作品级主编 Run 刷新后也必须重新露出审批卡，不能只支持章内阶段。"""
    ctx_env.store.upsert_ai_run_trace(
        "run_book_pending", status="waiting_for_approval",
        session_key="scribe3|work:book-a|runs",
        approvals=[{
            "run_id": "run_book_pending", "approval_id": "approval_book_pending",
            "tool": "s3_add_chapter", "message": "允许新建第1章？", "status": "requested",
        }],
    )
    ctx_env.store.upsert_ai_run_trace(
        "run_chapter_pending", status="waiting_for_approval",
        session_key="scribe3|work:book-a|chapter:1:draft",
        approvals=[{"approval_id": "approval_chapter_pending", "status": "requested"}],
    )

    response = client.get("/ai/runs/pending-approvals?work=book-a")

    assert response.status_code == 200
    assert response.json()["runs"] == [{
        "run_id": "run_book_pending",
        "approval_id": "approval_book_pending",
        "message": "允许新建第1章？",
    }]


def test_pending_approvals_exclude_run_with_terminal_approval_failure(client, ctx_env):
    """网关已拒绝/失效的审批不能在刷新后重新冒充可点击的待审批卡。"""
    ctx_env.store.upsert_ai_run_trace(
        "run_approval_failed", status="approval_failed",
        session_key="scribe3|work:book-a|runs",
        error='{"error":{"code":"approval_not_active"}}',
        approvals=[{
            "run_id": "run_approval_failed",
            "approval_id": "approval_expired",
            "message": "已失效的批准请求",
            "status": "requested",
        }],
    )

    response = client.get("/ai/runs/pending-approvals?work=book-a")

    assert response.status_code == 200
    assert response.json()["runs"] == []


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


def test_concurrent_approval_replay_is_idempotent_not_approval_failed(
    client, run, context_session, monkeypatch,
):
    """两个恢复中的浏览器同时批准同一张卡，第二次必须等首个决定落账后成功重放。"""
    import scribe3.app as appmod

    class ConcurrentRuntime(_FakeRuntime):
        def __init__(self):
            super().__init__()
            self.entered = threading.Event()
            self.release = threading.Event()
            self._lock = threading.Lock()
            self._consumed = False

        def approve_run(self, run_id, approval, **kwargs):
            with self._lock:
                if self._consumed:
                    request = httpx.Request("POST", f"http://hermes.test/runs/{run_id}/approval")
                    response = httpx.Response(400, request=request, text="approval_not_pending")
                    raise httpx.HTTPStatusError("approval_not_pending", request=request, response=response)
                self._consumed = True
                self.entered.set()
            assert self.release.wait(1), "测试未释放首个审批"
            return {"run_id": run_id, "status": "resumed"}

    runtime = ConcurrentRuntime()
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: runtime)
    body = {
        "approval_id": run.approval_id,
        "decision": "approve",
        "context_session_id": context_session.id,
        "context_revision": 8,
    }
    responses = []

    def submit():
        responses.append(client.post(f"/ai/runs/{run.id}/approval?work={WORK}", json=body))

    first = threading.Thread(target=submit)
    second = threading.Thread(target=submit)
    first.start()
    assert runtime.entered.wait(1), "首个审批没有到达 Hermes"
    second.start()
    # 给旧实现的第二个请求一次进入 Hermes 的机会；修复后它会被同 Run 锁阻塞。
    time.sleep(0.05)
    runtime.release.set()
    first.join(1)
    second.join(1)

    assert not first.is_alive() and not second.is_alive()
    assert sorted(response.status_code for response in responses) == [200, 200]
    trace = context_session.store.get_ai_run_trace(run.id)
    assert trace["status"] != "approval_failed"


def test_run_without_context_binding_keeps_legacy_approval(store, monkeypatch):
    """无 context 绑定的 run(存量/旧前端)审批不被重校验拦截——现有行为零回归。"""
    import scribe3.app as appmod

    appmod.set_store(store, work=WORK)
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: _FakeRuntime())
    client = TestClient(appmod.app)
    created = client.post(f"/ai/runs?work={WORK}", json={"input": "登记一条命题"})
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    approval = client.post(f"/ai/runs/{run_id}/approval?work={WORK}", json={
        "approval_id": "ap_legacy",
        "decision": "approve",
    })
    assert approval.status_code == 200


def test_approval_response_never_regresses_completed_trace(store, monkeypatch):
    """审批 HTTP 回写晚到时，不能把事件流已落下的终态改回 resumed。"""
    import scribe3.app as appmod

    appmod.set_store(store, work=WORK)
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: _FakeRuntime())
    client = TestClient(appmod.app)
    created = client.post(f"/ai/runs?work={WORK}", json={"input": "登记一条命题"})
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    # 真实 Run 中 SSE 的 run.completed 可以与审批 POST 并发抵达，并先写入 trace。
    store.upsert_ai_run_trace(run_id, status="completed")

    approval = client.post(f"/ai/runs/{run_id}/approval?work={WORK}", json={
        "approval_id": "ap_terminal", "decision": "approve",
    })

    assert approval.status_code == 200
    assert store.get_ai_run_trace(run_id)["status"] == "completed"


def test_stale_remote_status_never_regresses_completed_trace(client, run, context_session):
    """collector 已落终态后，晚到的远端 waiting 状态不得重新打开事件消费者。"""
    context_session.store.upsert_ai_run_trace(run.id, status="completed")

    response = client.get(f"/ai/runs/{run.id}?work={WORK}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert context_session.store.get_ai_run_trace(run.id)["status"] == "completed"


def test_stage_approval_persists_terminal_events_after_browser_stream_disconnects(store, monkeypatch):
    """刷新已断开浏览器 SSE 时，批准端点仍须收齐写工具完成和终态审计。"""
    import scribe3.app as appmod

    class TerminalAfterApprovalRuntime(_FakeRuntime):
        def run_events(self, run_id, **kwargs):
            return iter([
                {"event": "tool.started", "run_id": run_id,
                 "tool": "mcp_scribe3_deduce_write_s3_patch_chapter_plan"},
                {"event": "tool.completed", "run_id": run_id,
                 "tool": "mcp_scribe3_deduce_write_s3_patch_chapter_plan",
                 "result": {"status": "written"}},
                {"event": "run.completed", "run_id": run_id,
                 "usage": {"total_tokens": 23}},
            ])

    appmod.set_store(store, work=WORK)
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: TerminalAfterApprovalRuntime())
    client = TestClient(appmod.app)
    created = client.post(f"/ai/runs?work={WORK}", json={
        "input": "原样写入作者批准的场景真相",
        "run_scope": "chapter:1:deduce",
    })
    assert created.status_code == 200
    run_id = created.json()["run_id"]

    approval = client.post(f"/ai/runs/{run_id}/approval?work={WORK}", json={
        "approval_id": "ap_reloaded", "decision": "approve",
    })

    assert approval.status_code == 200
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if (store.get_ai_run_trace(run_id) or {}).get("status") == "completed":
            break
        time.sleep(0.01)
    trace = store.get_ai_run_trace(run_id)
    assert trace["status"] == "completed"
    assert any(
        row["tool"] == "s3_patch_chapter_plan"
        and row["output"] == {"status": "written"}
        for row in trace["tool_outputs"]
    )


def test_server_owned_event_collector_survives_author_approval_after_browser_disconnect(store, monkeypatch):
    """Run 事件由服务端持有，审批前浏览器离开也不能让 MCP 终态丢失。"""
    import scribe3.app as appmod

    class BlockingApprovalRuntime(_FakeRuntime):
        def __init__(self):
            super().__init__()
            self.approved = threading.Event()
            self.run_id = f"run_collector_{uuid4().hex}"
            self.approval_payloads = []

        def create_run(self, input_text, **kwargs):
            return {"run_id": self.run_id, "status": "queued"}

        def run_events(self, run_id, **kwargs):
            yield {"event": "tool.started", "run_id": run_id,
                   "tool": "mcp_scribe3_deduce_write_s3_patch_chapter_plan"}
            yield {"event": "approval.request", "run_id": run_id,
                   "approval_id": "ap_owned", "message": "允许写入章节演绎？"}
            assert self.approved.wait(1), "服务端事件收集器没有等到作者批准"
            yield {"event": "tool.completed", "run_id": run_id,
                   "tool": "mcp_scribe3_deduce_write_s3_patch_chapter_plan",
                   "result": {"status": "written"}}
            yield {"event": "run.completed", "run_id": run_id,
                   "output": "已完成章节计划核实。", "usage": {"total_tokens": 23}}

        def approve_run(self, run_id, approval, **kwargs):
            self.approval_payloads.append(dict(approval))
            self.approved.set()
            return {"run_id": run_id, "status": "resumed"}

    runtime = BlockingApprovalRuntime()
    appmod.set_store(store, work=WORK)
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: runtime)
    client = TestClient(appmod.app)
    created = client.post(f"/ai/runs?work={WORK}", json={
        "input": "写入作者批准的演绎",
        "run_scope": "chapter:1:deduce",
    })
    assert created.status_code == 200
    run_id = created.json()["run_id"]

    appmod._ensure_ai_run_event_collector(WORK, run_id)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if (store.get_ai_run_trace(run_id) or {}).get("approvals"):
            break
        time.sleep(0.01)
    assert (store.get_ai_run_trace(run_id) or {}).get("approvals"), "服务端未持久化待审批事件"

    # collector 可先于浏览器到达 approval.requested；订阅须重放审批卡，并在批准后
    # 保持连接以接收 resolved 与终态，不能让第一张卡截断多审批 Run。
    events_result = {}
    events_thread = threading.Thread(
        target=lambda: events_result.setdefault(
            "response", client.get(f"/ai/runs/{run_id}/events?work={WORK}")),
        daemon=True,
    )
    events_thread.start()
    time.sleep(0.03)

    approval = client.post(f"/ai/runs/{run_id}/approval?work={WORK}", json={
        "approval_id": "ap_owned", "decision": "approve",
    })
    assert approval.status_code == 200
    assert runtime.approval_payloads == [{"approval_id": "ap_owned", "choice": "once"}]
    events_thread.join(timeout=1)
    events = events_result.get("response")
    assert events is not None, "SSE 未在 Run 终态后收尾"
    assert events.status_code == 200
    assert '"approval"' in events.text
    assert '"done": true' in events.text
    while time.monotonic() < deadline:
        if (store.get_ai_run_trace(run_id) or {}).get("status") == "completed":
            break
        time.sleep(0.01)
    trace = store.get_ai_run_trace(run_id)
    assert trace["status"] == "completed"
    assert any(row["tool"] == "s3_patch_chapter_plan" for row in trace["tool_outputs"])


def test_traced_run_approval_rejects_wrong_work(store, monkeypatch):
    """后续审批必须先在请求 work 的 trace 中找到 run，禁止跨书 fallback。"""
    import scribe3.app as appmod

    work = "live_approval_contract"
    run_id = f"run_wrong_work_{uuid4().hex}"
    session_key = f"scribe3|work:{work}|runs"
    appmod.set_store(store, work=work)
    store.upsert_ai_run_trace(run_id, status="waiting_for_approval",
                              session_key=session_key)

    class Runtime:
        def approve_run(self, *_args, **_kwargs):
            raise AssertionError("错误 work 的审批不得到达 Hermes")

    class EmptyWorkStore:
        db_name = "other_live_approval_contract"

        def get_ai_run_trace(self, _run_id):
            return None

    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: Runtime())
    monkeypatch.setitem(appmod._stores, "other_live_approval_contract", EmptyWorkStore())
    client = TestClient(appmod.app)

    wrong_work = client.post(
        f"/ai/runs/{run_id}/approval?work=other_live_approval_contract",
        json={"decision": "approve"},
    )
    assert wrong_work.status_code == 404


def test_live_run_approval_without_approval_id_sends_choice_only(store, monkeypatch):
    """Hermes 0.18.2 的 live MCP 审批按 run_id + choice 解析，不要求 approval_id。"""
    import scribe3.app as appmod

    work = "live_approval_contract"
    run_id = f"run_live_approval_{uuid4().hex}"
    session_key = f"scribe3|work:{work}|runs"
    appmod.set_store(store, work=work)
    store.upsert_ai_run_trace(run_id, status="waiting_for_approval",
                              session_key=session_key)

    class Runtime:
        def __init__(self):
            self.approval_payloads = []

        def run_events(self, *_args, **_kwargs):
            return iter(())

        def approve_run(self, requested_run_id, approval, **kwargs):
            self.approval_payloads.append(
                (requested_run_id, dict(approval), kwargs.get("session_key"))
            )
            return {"run_id": requested_run_id, "status": "resumed"}

    runtime = Runtime()
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: runtime)
    client = TestClient(appmod.app)

    approved = client.post(
        f"/ai/runs/{run_id}/approval?work={work}",
        json={"decision": "approve"},
    )

    assert approved.status_code == 200
    assert runtime.approval_payloads == [
        (run_id, {"choice": "once"}, session_key),
    ]


def test_live_run_approval_rejects_invalid_choice_before_runtime_call(store, monkeypatch):
    """live 审批仍只接受 Hermes 的受控 choice 枚举，不能因省略 approval_id 放宽。"""
    import scribe3.app as appmod

    work = "live_approval_contract"
    run_id = f"run_invalid_choice_{uuid4().hex}"
    appmod.set_store(store, work=work)
    store.upsert_ai_run_trace(run_id, status="waiting_for_approval",
                              session_key=f"scribe3|work:{work}|runs")

    class Runtime:
        def approve_run(self, *_args, **_kwargs):
            raise AssertionError("非法 choice 不得到达 Hermes")

    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: Runtime())
    client = TestClient(appmod.app)

    invalid_choice = client.post(
        f"/ai/runs/{run_id}/approval?work={work}",
        json={"choice": "unbound-approval"},
    )
    assert invalid_choice.status_code == 400


def test_ai_run_creation_starts_server_collector_without_sse_subscription(store, monkeypatch):
    """创建 Run 后浏览器尚未订阅/已离开，服务端仍必须持久化终态。"""
    import scribe3.app as appmod

    class ImmediateRuntime(_FakeRuntime):
        def __init__(self):
            super().__init__()
            self.run_id = f"run_created_collector_{uuid4().hex}"

        def create_run(self, input_text, **kwargs):
            return {"run_id": self.run_id, "status": "queued"}

        def run_events(self, run_id, **kwargs):
            yield {"event": "tool.started", "run_id": run_id,
                   "tool": "mcp_scribe3_deduce_write_s3_patch_chapter_plan"}
            yield {"event": "tool.completed", "run_id": run_id,
                   "tool": "mcp_scribe3_deduce_write_s3_patch_chapter_plan",
                   "result": {"status": "written"}}
            yield {"event": "run.completed", "run_id": run_id,
                   "output": "已完成章节计划核实。", "usage": {"total_tokens": 23}}

    runtime = ImmediateRuntime()
    appmod.set_store(store, work=WORK)
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: runtime)
    client = TestClient(appmod.app)

    created = client.post(f"/ai/runs?work={WORK}", json={
        "input": "创建后立即离开的演绎",
        "run_scope": "chapter:1:deduce",
    })

    assert created.status_code == 200
    run_id = created.json()["run_id"]
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if (store.get_ai_run_trace(run_id) or {}).get("status") == "completed":
            break
        time.sleep(0.01)
    trace = store.get_ai_run_trace(run_id) or {}
    assert trace.get("status") == "completed"
    assert any(row["tool"] == "s3_patch_chapter_plan" for row in trace.get("tool_outputs", []))
    assert trace.get("response", {}).get("output") == "已完成章节计划核实。"


def test_stop_completed_run_is_idempotent_when_hermes_has_pruned_it(ctx_env, monkeypatch):
    """前端卸载晚于 run 完成时，stop 不能把 Hermes 404 误报成系统 500。"""
    import scribe3.app as appmod

    run_id = "run_completed_pruned"
    ctx_env.store.upsert_ai_run_trace(run_id, status="completed")
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda: _CompletedRunStopRuntime())

    response = ctx_env.client.post(f"/ai/runs/{run_id}/stop?work={WORK}")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": run_id,
        "status": "completed",
        "already_finished": True,
    }


def test_stop_completed_run_is_idempotent_when_hermes_returns_400_run_not_found(ctx_env, monkeypatch):
    """真实 TokenPlan/Hermes 清理完成 Run 的 400 不得覆写本地 completed 审计。"""
    import scribe3.app as appmod

    run_id = "run_completed_pruned_400"
    ctx_env.store.upsert_ai_run_trace(run_id, status="completed")
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda: _CompletedRunStop400Runtime())

    response = ctx_env.client.post(f"/ai/runs/{run_id}/stop?work={WORK}")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": run_id,
        "status": "completed",
        "already_finished": True,
    }
    assert ctx_env.store.get_ai_run_trace(run_id)["status"] == "completed"


def test_stop_remote_completed_pending_audit_is_idempotent_when_hermes_pruned_it(ctx_env, monkeypatch):
    """远端已完成、collector 尚在补审计时，作者点停止也不能得到 502。

    这个状态不能并入全局 terminal 集合（collector 仍须完成工具审计），但 Hermes 已无
    可停止的远端 run；对 stop 端点而言必须与已完成同样幂等。
    """
    import scribe3.app as appmod

    run_id = "run_remote_completed_pruned_400"
    ctx_env.store.upsert_ai_run_trace(run_id, status="remote_completed_pending_audit")
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda: _CompletedRunStop400Runtime())

    response = ctx_env.client.post(f"/ai/runs/{run_id}/stop?work={WORK}")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": run_id,
        "status": "remote_completed_pending_audit",
        "already_finished": True,
    }
    assert ctx_env.store.get_ai_run_trace(run_id)["status"] == "remote_completed_pending_audit"


def test_remote_completed_status_waits_for_event_audit_before_terminalizing(ctx_env, monkeypatch):
    """状态轮询不能在 tool/run 事件尚未落库时把 trace 假绿为 completed。"""
    import scribe3.app as appmod

    run_id = "run_remote_completed_without_events"
    ctx_env.store.upsert_ai_run_trace(run_id, status="started")
    monkeypatch.setattr(
        appmod,
        "_hermes_runs_runtime",
        lambda policy=None: _RemoteCompletedWithoutEventsRuntime(),
    )

    response = ctx_env.client.get(f"/ai/runs/{run_id}?work={WORK}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    trace = ctx_env.store.get_ai_run_trace(run_id)
    assert trace["status"] == "remote_completed_pending_audit"
    assert trace["response"]["status"] == "completed"


def test_completed_run_status_is_readable_after_hermes_prunes_remote_record(ctx_env, monkeypatch):
    """Hermes 回收远端记录后，前端状态轮询仍返回本地已完成审计而非 500。"""
    import scribe3.app as appmod

    run_id = "run_completed_status_pruned"
    ctx_env.store.upsert_ai_run_trace(run_id, status="completed")
    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda policy=None: _PrunedRunStatusRuntime())

    response = ctx_env.client.get(f"/ai/runs/{run_id}?work={WORK}")

    assert response.status_code == 200
    assert response.json()["run_id"] == run_id
    assert response.json()["status"] == "completed"
    assert ctx_env.store.get_ai_run_trace(run_id)["status"] == "completed"


def test_remote_completed_status_never_overwrites_local_required_tool_failure(ctx_env, monkeypatch):
    """远端 completed 不能掩盖 collector 已判定的工具合同失败。"""
    import scribe3.app as appmod

    run_id = "run_required_tool_missing"
    ctx_env.store.upsert_ai_run_trace(
        run_id,
        status="failed",
        error="stage tool policy violation",
    )
    ctx_env.store.update_ai_run_context(
        run_id,
        policy_violations=[{"code": "required_tool_missing", "tool": "s3_add_chapter"}],
    )
    monkeypatch.setattr(
        appmod,
        "_hermes_runs_runtime",
        lambda policy=None: _RemoteCompletedWithoutEventsRuntime(),
    )

    response = ctx_env.client.get(f"/ai/runs/{run_id}?work={WORK}")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    trace = ctx_env.store.get_ai_run_trace(run_id)
    assert trace["status"] == "failed"
    assert trace["policy_violations"] == [
        {"code": "required_tool_missing", "tool": "s3_add_chapter"},
    ]


def test_empty_events_after_remote_completion_need_audit_reconciliation(ctx_env, monkeypatch):
    """事件端点空结束同样不能把远端 completed 当成本地审计完成。"""
    import scribe3.app as appmod

    run_id = "run_remote_completed_empty_events"
    ctx_env.store.upsert_ai_run_trace(run_id, status="started")
    monkeypatch.setattr(
        appmod,
        "_hermes_runs_runtime",
        lambda policy=None: _RemoteCompletedWithoutEventsRuntime(),
    )

    appmod._ensure_ai_run_event_collector(WORK, run_id)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if (ctx_env.store.get_ai_run_trace(run_id) or {}).get("status") == "completed_unverified":
            break
        time.sleep(0.01)

    trace = ctx_env.store.get_ai_run_trace(run_id)
    assert trace["status"] == "completed_unverified"
    assert "events" in str(trace["error"])


def test_pruned_events_after_remote_completion_need_audit_reconciliation(ctx_env, monkeypatch):
    """远端已终态而 events=404 时，不能伪装为普通失败或完整成功。"""
    import scribe3.app as appmod

    run_id = "run_pruned_after_approval"
    ctx_env.store.upsert_ai_run_trace(
        run_id,
        status="waiting_for_approval",
        approvals=[{"approval_id": "ap_pruned", "status": "resolved"}],
    )
    ctx_env.store.update_ai_run_context(
        run_id,
        write_effects=[{"kind": "approval", "approval_id": "ap_pruned"}],
    )
    monkeypatch.setattr(
        appmod,
        "_hermes_runs_runtime",
        lambda policy=None: _EventsPrunedAfterRemoteCompletionRuntime(),
    )

    appmod._ensure_ai_run_event_collector(WORK, run_id)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if (ctx_env.store.get_ai_run_trace(run_id) or {}).get("status") == "completed_unverified":
            break
        time.sleep(0.01)

    trace = ctx_env.store.get_ai_run_trace(run_id)
    assert trace["status"] == "completed_unverified"
    assert "events" in str(trace["error"])
    assert trace["response"]["status"] == "completed"
