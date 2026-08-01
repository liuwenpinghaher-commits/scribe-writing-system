# Gate B 阶段专用工具面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让章节“演绎” Run 只能访问完成演绎所需的最小 MCP 工具面，并把实际工具调用完整落入可审计 trace，避免会话隔离后仍发生跨阶段工具游走。

**Architecture:** Hermes Runs 不支持请求级工具裁剪，故按阶段选择独立、受版本控制的 Hermes gateway profile；profile 的 MCP server labels 以静态 `tools.include` 形成真实能力边界。后端只接受受控 `run_scope`，由单一运行路由表决定目标 profile/API 与阶段步骤上限；前端仅声明章节与阶段，不能指定 gateway。所有工具事件保留名称、参数、输出和调用序号，结束时由服务端基于阶段许可表判定 trace 是否合规。

**Tech Stack:** FastAPI/Pydantic、Hermes Agent profile + MCP allowlist、SurrealStore run trace、React/Vite、pytest、Vitest、真实浏览器 E2E。

## Global Constraints

- `docs/CURRENT_ARCHITECTURE.md` 与 `AGENTS.md` 是当前架构真源；SurrealDB 是唯一正典。
- 语义写入只能经 MCP + 人工审批；不以 REST 或 DB 灌库替代验收。
- 不把 secret 写进模板、测试、日志或提交。
- 演绎阶段的 allowlist 必须 fail-closed；未知 phase 不得悄悄回退到全写工具网关。
- 保留普通 Runs 与既有前端调用兼容；没有章节阶段的旧调用继续用 `scribe3_write`。
- 本次不 commit、不 push，除非用户另行明确授权。

---

### Task 1: 阶段运行路由与 Hermes profile 配置

**Files:**
- Create: `scribe3/run_stage_policy.py`
- Modify: `scribe3/llm.py`
- Modify: `scribe3/settings.py`
- Modify: `scribe3/scripts/provision_hermes.py`
- Create: `scribe3/deploy/hermes/overlay.scribe3_deduce.yaml`
- Modify: `scribe3/deploy/hermes/mcp_servers.yaml`
- Test: `scribe3/tests/test_run_stage_policy.py`
- Test: `scribe3/tests/test_provision_hermes.py`

**Interfaces:**
- Produces `resolve_run_stage_policy(run_scope: str | None) -> RunStagePolicy`.
- `RunStagePolicy` 包含 `profile`、`api_base_env`、`allowed_tools` 与 `max_tool_calls`。
- 演绎 profile 仅激活 `scribe3_deduce_read`、`scribe3_deduce_write`；write allowlist 仅有 `s3_patch_chapter_plan`。

- [ ] **Step 1: Write the failing policy and provisioning tests**

```python
def test_deduce_scope_uses_dedicated_profile_and_exact_allowlist():
    policy = resolve_run_stage_policy("chapter:1:deduce")
    assert policy.profile == "scribe3_deduce"
    assert policy.allowed_tools == frozenset({
        "s3_get_chapter", "s3_project_frame", "s3_character_state",
        "s3_list_entity_relations", "s3_list_world_rules", "s3_list_promises",
        "s3_patch_chapter_plan",
    })

def test_unknown_chapter_phase_is_rejected_fail_closed():
    with pytest.raises(ValueError, match="unsupported chapter run phase"):
        resolve_run_stage_policy("chapter:1:invent")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_run_stage_policy.py -q`

Expected: FAIL because `run_stage_policy` does not exist.

- [ ] **Step 3: Implement policy and declarative deduce profile**

```python
DEDUCE_ALLOWED_TOOLS = frozenset({...})
RUN_STAGE_POLICIES = {"deduce": RunStagePolicy(...)}

def resolve_run_stage_policy(run_scope):
    # chapter:<positive-int>:<registered-phase>; invalid/unknown phase raises ValueError
```

在 `mcp_servers.yaml` 新增只含上述工具的 `scribe3_deduce_read` 与 `scribe3_deduce_write`，新增 :8645 `scribe3_deduce` overlay，并让 provision 以深合并方式写入该 profile。绝不复制完整 write allowlist。

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_run_stage_policy.py scribe3/tests/test_provision_hermes.py -q`

Expected: PASS；演绎 profile 不包含任何角色/世界/正文/声线/弧光/伏笔等无关写工具。

### Task 2: 后端受控运行路由与工具 trace 完整性

**Files:**
- Modify: `scribe3/api/app_impl.py`
- Modify: `scribe3/hermes_runtime.py`
- Modify: `scribe3/store/` 中 ai-run trace 持久化实现（仅在现有 trace schema 无法存调用序号/参数/输出时）
- Test: `scribe3/tests/test_ai_runs.py`
- Test: `scribe3/tests/test_hermes_runtime.py`

**Interfaces:**
- `AIRunCreateReq.run_scope` 进入 `resolve_run_stage_policy`；无有效 policy 时返回 422，不创建 Run。
- `_hermes_runs_runtime(policy)` 选择 profile 和 API；前端不得传入 profile/API。
- trace 持久化 `tool_calls: [{sequence, name, arguments, output, call_id}]`。
- `validate_run_trace_policy(policy, tool_calls)` 返回违规工具与是否超过步骤上限。

- [ ] **Step 1: Write failing endpoint/trace tests**

```python
def test_deduce_run_uses_dedicated_runtime_and_records_policy(client, monkeypatch):
    response = client.post("/ai/runs?work=book-a", json={
        "input": "演绎第1章", "run_scope": "chapter:1:deduce",
    })
    assert response.status_code == 200
    assert created_runtime.profile == "scribe3_deduce"
    assert trace["stage_policy"]["phase"] == "deduce"

def test_deduce_trace_marks_out_of_policy_write_as_failed(client, fake_runtime):
    # 事件包含 s3_add_character 后，trace 必须带 policy violation，run 不能被标为成功
```

- [ ] **Step 2: Run test to verify it fails**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_ai_runs.py -q`

Expected: FAIL because runs currently always select `scribe3_write` and trace lacks policy result.

- [ ] **Step 3: Implement route selection and complete event persistence**

`HermesEventAdapter` 归一化 Hermes 的包裹工具名；事件流按 `session_key` 使用创建时 trace 的 session key，不得退回作品级 `runs` key。将 tool.started/tool.output 合并为同一 call_id 条目；输入事件参数、输出和序号均落 trace。Run completed 前执行 policy 校验；越权、超限或缺失必要 trace 记 `status=failed` 与结构化 `policy_violations`，并把失败事件推给前端。

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_ai_runs.py scribe3/tests/test_hermes_runtime.py -q`

Expected: PASS；普通 Runs 兼容，演绎 Runs 走 :8645/profile `scribe3_deduce`，且 trace 可证明每次工具调用。

### Task 3: 前端阶段声明、失败呈现与契约回归

**Files:**
- Modify: `scribe3/web/src/api.js`
- Modify: 章节演绎发起组件（按实际调用点定位）
- Modify: `scribe3/web/e2e/craft_first_journey.mjs`
- Test: `scribe3/web/src/__tests__/api-works.test.js`
- Test: `scribe3/web/src/e2e/chapterPlanState.test.js`

**Interfaces:**
- `runWrite` 仅从已选章节和受控 phase 产生 `run_scope`。
- API 422 或 trace policy violation 必须在主编界面显示可操作失败，不可显示“已完成”。
- E2E 在 Gate B 对 trace 断言：无不允许工具、存在 `s3_patch_chapter_plan` 的审批和写入、deductions 覆盖所有 involved characters。

- [ ] **Step 1: Write failing frontend/E2E contract tests**

```javascript
it('只为受支持的章节阶段发送 run_scope，未知阶段不创建 run', async () => {...})
it('Gate B 拒绝缺失 trace 或越权工具，即使章节字段看似完整', () => {...})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scribe3/web && npm test -- src/__tests__/api-works.test.js src/e2e/chapterPlanState.test.js`

Expected: FAIL because current API helper accepts arbitrary phase and E2E does not enforce policy trace.

- [ ] **Step 3: Implement minimal UI/contract behavior**

前端按后端阶段表允许的 phase 发送 scope；错误显示真实 `detail`/policy failure。E2E 不调用 API 写世界状态，不设置 `E2E_ALLOW_API_SEED`，并在首章 Gate B 前回读 trace 与 SurrealDB。

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `cd scribe3/web && npm test -- src/__tests__/api-works.test.js src/e2e/chapterPlanState.test.js src/e2e/workResolution.test.js`

Expected: PASS。

### Task 4: 真实网关与真实 UI Gate B 验收

**Files:**
- Modify: `docs/` 验收记录（仅记录真实证据）
- Runtime: `~/.hermes/profiles/scribe3_deduce/config.yaml`（只能由 provision `--commit` 生成，保留自动备份）

- [ ] **Step 1: Verify deployment diff before mutation**

Run: `scribe3/.venv/bin/python -m scribe3.scripts.provision_hermes --hermes-home ~/.hermes --repo "$PWD"`

Expected: dry-run 仅显示 scribe3_deduce profile 的 owned keys。

- [ ] **Step 2: Apply only the declarative profile overlay and restart supervised gateway**

Run: `scribe3/.venv/bin/python -m scribe3.scripts.provision_hermes --hermes-home ~/.hermes --repo "$PWD" --commit`

Then: restart only `scribe3_deduce` gateway using Hermes’ supervised profile command; probe its `/health/detailed` and `/v1/toolsets`.

- [ ] **Step 3: Run real browser first-chapter journey**

Run: `cd scribe3/web && E2E_BOOK_TITLE='真实验收·GateB·<timestamp>' E2E_API=http://127.0.0.1:3321 node e2e/craft_first_journey.mjs`

Expected: no API seed; Gate A and Gate B PASS; trace exposes only the exact deduce allowlist; SurrealDB readback shows semantically complete chapter plan and per-character deductions.

- [ ] **Step 4: Record evidence or stop honestly**

写入验收报告中的 work/run/chapter IDs、阶段配置摘要、工具 trace、审批结果、DB 回读和质量分析。若任何一项失败，回到对应任务以失败测试固定根因；不得进入 Gate C/D。
