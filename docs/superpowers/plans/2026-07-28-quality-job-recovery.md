# 可恢复质量作业 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让一次章节质量评价以持久化、可恢复、真实 TokenPlan 可审计的作业执行，只有完整双轴证据落库后才向作者开放十维裁决。

**Architecture:** `quality_job` 保存不可变评价输入与可变执行状态；API 同步创建/幂等读取作业、后台执行评价，前端轮询状态而非占用浏览器请求。评价器保持现有冻结快照与 `ContextOutcome` 绑定，使用受限并发取得二十个独立判断，全部成功后原子写入 judgment 轴；失败保留安全错误摘要和可重试状态。

**Tech Stack:** FastAPI、SurrealDB、Python `ThreadPoolExecutor`、React、Vitest、pytest、Playwright、阿里云 TokenPlan/Qwen。

## Global Constraints

- 真实质量完成必须有 10 个 system + 10 个 reference judgment，并各自绑定真实 `provider_request_id` 与非零 usage。
- 参考原文、作者提示词和 Token 不进入作业状态、API、日志或测试报告。
- 世界状态写入仍只经 Hermes MCP 审批；本计划不新增 REST 正典写入口。
- 未完成、失败或只有部分结果的作业不得显示十维评分、决策指数或可提交作者裁决。
- 每个供应商调用保持硬截止；并发数固定为 4，任一调用失败时本轮不写半成品 judgment。

---

### Task 1: 持久化质量作业执行状态

**Files:**
- Create: `scribe3/migrations/105_quality_job_execution_state.surql`
- Modify: `scribe3/quality/store.py`
- Modify: `scribe3/quality/models.py`
- Test: `scribe3/tests/test_quality_store.py`

**Interfaces:**
- Produces `QualityJobExecutionStatus(status, attempts, error_code, error_message, started_at, finished_at)`。
- Produces `QualityStore.start_job(job_id)`, `finish_job(job_id)`, `fail_job(job_id, error_code, error_message)` 和 `get_job_status(job_id)`。

- [ ] **Step 1: 写失败测试**

```python
def test_quality_job_state_is_durable_and_never_overwrites_immutable_input(store):
    job = _seed_job(store)[0]
    quality = QualityStore(store)
    assert quality.start_job(job.job_id).status == "running"
    failed = quality.fail_job(job.job_id, "provider_timeout", "供应商调用超过截止")
    assert failed.status == "retryable_failed"
    assert failed.attempts == 1
    assert quality.get_job(job.job_id).contract_id == "contract:book-quality"
```

- [ ] **Step 2: 运行失败测试**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_store.py -k job_state -q`

- [ ] **Step 3: 实现最小状态模型和迁移**

```surql
DEFINE FIELD IF NOT EXISTS execution_status ON quality_job TYPE string ASSERT $value IN ['queued','running','completed','retryable_failed','failed'];
DEFINE FIELD IF NOT EXISTS execution_attempts ON quality_job TYPE int;
DEFINE FIELD IF NOT EXISTS execution_error_code ON quality_job TYPE option<string>;
DEFINE FIELD IF NOT EXISTS execution_error_message ON quality_job TYPE option<string>;
```

`start_job` 仅允许 `queued|retryable_failed -> running`；`finish_job` 只在完整 judgment 数量满足期望轴数后写 `completed`；错误文本限 300 字且不得包含请求体。

- [ ] **Step 4: 运行测试**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_store.py -k job_state -q`

### Task 2: 原子、受限并发的评价执行器

**Files:**
- Modify: `scribe3/quality/evaluator.py`
- Test: `scribe3/tests/test_quality_evaluator_pipeline.py`

**Interfaces:**
- Consumes `QualityJobRecord` 和 `QualityStore` 状态接口。
- Produces `QualityEvaluator.execute_job(job_id)`；返回完整 `QualityEvaluation` 或抛出分类供应商错误，绝不保存部分 judgment。

- [ ] **Step 1: 写失败测试**

```python
def test_execute_job_requires_all_twenty_bounds_before_persisting(store, approved_reference):
    evaluator = QualityEvaluator(store, OneSlowOrFailingClient())
    with pytest.raises(DeepSeekError):
        evaluator.execute_job(job_id)
    assert QualityStore(store).get_evaluation(job_id).system_reference_judgments == ()

def test_execute_job_limits_independent_dimensions_to_four_workers(store):
    evaluator = QualityEvaluator(store, CountingClient())
    evaluator.execute_job(job_id)
    assert CountingClient.max_inflight <= 4
    assert len(QualityStore(store).get_evaluation(job_id).system_reference_judgments) == 20
```

- [ ] **Step 2: 运行失败测试**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_evaluator_pipeline.py -k 'execute_job or four_workers' -q`

- [ ] **Step 3: 实现执行分离与原子落库**

从 `evaluate_chapter` 提取 `prepare_job` 与 `execute_job`；把 `(member, dimension, system|reference)` 任务提交到 `ThreadPoolExecutor(max_workers=4)`。工作线程只调用模型、构造 `BoundQualityJudgment`；主线程在所有 future 成功后按成员调用一次 `save_judgments`，再 `finish_job`。任一 future 异常：取消未开始任务，`fail_job`，不调用 `save_judgments`。

- [ ] **Step 4: 运行测试**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_evaluator_pipeline.py -q`

### Task 3: 后台 API 与浏览器恢复

**Files:**
- Modify: `scribe3/quality/api.py`
- Modify: `scribe3/web/src/api.js`
- Modify: `scribe3/web/src/quality/QualityReview.jsx`
- Test: `scribe3/tests/test_quality_api.py`
- Test: `scribe3/web/src/quality/QualityReview.test.jsx`

**Interfaces:**
- `POST /quality/snapshot` 返回 202 `{job_id,status:'queued'}`，同一输入重放返回同一 job。
- `GET /quality/evaluation` 返回 `queued|running|retryable_failed|failed|ready`，只有 `ready` 带 dimensions。
- `POST /quality/jobs/{job_id}/retry` 仅允许 `retryable_failed`，不改变快照、合同和指纹。

- [ ] **Step 1: 写失败测试**

```python
def test_snapshot_returns_accepted_job_and_get_hides_incomplete_axes(client, store, monkeypatch):
    monkeypatch.setattr("scribe3.quality.api._dispatch_quality_job", lambda *_: None)
    created = client.post("/quality/snapshot", json=_snapshot_body()).json()
    assert created["status"] == "queued"
    assert client.get("/quality/evaluation", params={"seq": 1}).json()["dimensions"] == []
```

```jsx
it('运行中持续轮询且不渲染作者裁决表单', async () => {
  apiMock.qualityEvaluation.mockResolvedValue({ chapter: 1, status: 'running', dimensions: [] })
  render(<QualityReview work="demo" seq={1} />)
  expect(await screen.findByText(/正在执行质量判断/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: '提交裁决' })).toBeNull()
})
```

- [ ] **Step 2: 运行失败测试**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_api.py -k accepted_job -q && cd scribe3/web && npx vitest run src/quality/QualityReview.test.jsx`

- [ ] **Step 3: 实现后台调度和轮询 UI**

后台线程使用独立 `SurrealStore(ns='scribe3', db=work)`，执行结束必定关闭连接。前端每 1 秒读取 evaluation；仅 `running|queued` 轮询，`retryable_failed` 显示“重试本次冻结评价”，`failed` 显示安全错误摘要，不自动重试。

- [ ] **Step 4: 运行测试**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_api.py -q && cd scribe3/web && npx vitest run src/quality/QualityReview.test.jsx`

### Task 4: 真实 TokenPlan 闭环回归

**Files:**
- Modify: `scribe3/web/e2e/quality_reference_author_journey.mjs`
- Modify: `scribe3/web/e2e/author_decisions.test.mjs`

**Interfaces:**
- 旅程接受 202 并等待 `ready`，严格回读 20 条 Qwen trace、参考消费账本、十维作者裁决和三轴权重。

- [ ] **Step 1: 写失败静态契约测试**

```javascript
it('质量旅程等待后台作业 ready 而非把 202 当作评价完成', () => {
  const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
  assert.match(journey, /qualityJobStatus/)
  assert.match(journey, /status === 'ready'/)
  assert.match(journey, /traces.length === 20/)
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && node --test e2e/author_decisions.test.mjs`

- [ ] **Step 3: 更新真实旅程**

记录 job id、状态转换和最终 trace 数量；超时/失败时输出脱敏的 job 状态与错误码，不能继续作者裁决。

- [ ] **Step 4: 验证**

Run: `cd scribe3/web && node --test e2e/author_decisions.test.mjs && E2E_BASE=http://127.0.0.1:3312 E2E_API=http://127.0.0.1:3321 E2E_BOOK_TITLE='质量闭环真人验收·TokenPlan·20260728124454' E2E_WORK=book_6998a492 node e2e/quality_reference_author_journey.mjs`

Expected: Gate A/B、正文、合同、指纹、20 条真实 Qwen trace、参考消费账本和十维作者裁决全部回读成功。

## Self-review

- 状态持久化、并发执行、API/UI 恢复、真人验收均有独立任务和失败测试。
- 所有状态名、接口和 job_id 在任务间一致；无未定义占位符。
- 不涉及正典 REST 写入口、参考原文回显或密钥处理。
