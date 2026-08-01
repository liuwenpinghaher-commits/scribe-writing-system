# 质量决策闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让作者能以已批准的参考技法、固定十维和高于机器的作者裁决，完成可追溯且可复验的章节质量改进闭环。

**Architecture:** 质量合同、指纹、快照、判断和裁决均保存到现有 SurrealDB 质量领域表；生成与正典写入边界不变。评价器只从已批准指纹提取安全技法摘要，所有机器判断必须锚定冻结正文和真实 Provider outcome；前端只调用质量 API，不直接写世界正典。

**Tech Stack:** FastAPI、SurrealDB、Pydantic、React/Vitest、Playwright、阿里云 TokenPlan/Qwen、Hermes。

## Global Constraints

- 真实模型基线为 `qwen3.8-max-preview`（TokenPlan），不得以 DeepSeek 作为验收依据。
- 参考原文仅供指纹生成；生成与评价比较只能读取已批准的安全技法摘要，不能复刻原句、人物或情节。
- 作者权重必须严格高于 system/reference，且裁决理由、反证与采纳状态必须可回读。
- 正典语义写入继续走 MCP 审批；本计划不新增 REST 世界写旁路。
- 通过单测不等于验收完成；每项需补 UI + Provider + SurrealDB 证据。

---

### Task 1: 参考技法轴与安全边界

**Files:**
- Modify: `scribe3/quality/evaluator.py`
- Test: `scribe3/tests/test_quality_evaluator_pipeline.py`

**Interfaces:**
- Consumes: `ReferenceFingerprintRecord(status="approved")` 的 `transferable_mechanisms`、`non_copyable_elements`、`applicable_scope`。
- Produces: 每个冻结章节版本十条 `evaluator_kind="reference"` 的 `BoundQualityJudgment`，并绑定 `reference_compare.v1` outcome。

- [x] 写失败测试：批准指纹参加评价后产生十条带正文锚点的 reference 判断。
- [x] 确认旧实现失败：reference 轴为空。
- [x] 只用安全摘要调用比较器，拒绝未批准指纹，生成独立 outcome ID，保存 reference 轴。
- [x] 跑 `scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_evaluator_pipeline.py scribe3/tests/test_quality_evaluator.py scribe3/tests/test_quality_context.py -q`。

### Task 2: 真实模型调用留痕

**Files:**
- Modify: `scribe3/deepseek_client.py`
- Modify: `scribe3/quality/evaluator.py`
- Test: `scribe3/tests/test_quality_evaluator_pipeline.py`

**Interfaces:**
- Consumes: `CompletionResult(response_id, model, usage, identity)`。
- Produces: `ContextOutcomeTrace` 与 `QualityJobRecord` 中的真实请求 ID、实际模型和 usage；fake client 仍可按旧 `complete_json` 兼容。

- [ ] 写失败测试：评价 outcome 的 request ID/usage 不得由派生常量或零值伪造。
- [ ] 给 `DeepSeekClient` 增加保留最后一次 JSON 完成 metadata 的显式返回接口，不改变既有 `complete_json` 返回 schema 实例的调用方。
- [ ] 评价器优先写真实 metadata；不支持 metadata 的 fake client 标为 `unavailable` 而非伪造成功数据。
- [ ] 跑质量流水线、客户端单测和一次隔离书 TokenPlan 评价，核验 provider/model/usage。

### Task 3: 合同与作者裁决领域完整性

**Files:**
- Modify: `scribe3/quality/models.py`
- Modify: `scribe3/quality/store.py`
- Create: `scribe3/migrations/101_quality_author_verdict.surql`
- Modify: `scribe3/quality/api.py`
- Test: `scribe3/tests/test_quality_contracts.py`, `scribe3/tests/test_quality_store.py`, `scribe3/tests/test_quality_api.py`

**Interfaces:**
- Consumes: 完整 `QualityContractRevision`、十维 `DecisionWeights`、作者评分/理由/反证/裁决。
- Produces: append-only 合同修订、作者判断的独立正文证据、`accept|revise|reject` 决策，评价响应按合同权重计算 index。

- [ ] 写失败测试：API 使用合同 weights 而非 `(0.5, 0.3, 0.2)` 常量；作者理由与反证能回读；作者不存在时不产生 index。
- [ ] 为作者裁决增加不可变 payload 与 migration，保持旧 author judgment 向后可读。
- [ ] 新增合同草案/读取/批准 API；世界级叙事字段通过主编审批入口创建，质量配置字段走专用 append-only API。
- [ ] 跑模型、存储、API 三组测试。

### Task 4: 作者可达 UI

**Files:**
- Modify: `scribe3/web/src/api.js`
- Modify: `scribe3/web/src/quality/QualityReview.jsx`
- Modify: `scribe3/web/src/quality/ReferenceWorks.jsx`
- Create: `scribe3/web/src/quality/QualityContractEditor.jsx`
- Test: 对应 `*.test.jsx`

**Interfaces:**
- Consumes: `/quality/contracts`、`/quality/snapshot`、`/quality/author-judgment`、references API。
- Produces: 合同全字段可填、指纹可校订批准、章节评价可发起、作者可提交理由/反证/裁决并看到三轴差异。

- [ ] 为每个交互写失败组件测试，特别覆盖有效 `seq` 绑定和没有章节时的禁用态。
- [ ] 实现表单分区、错误回显和可定位原文证据；不直接写正典。
- [ ] 补 API facade 与组件回归测试。

### Task 5: 真实验收编排

**Files:**
- Create: `scribe3/web/e2e/quality_reference_author_journey.mjs`
- Modify: `Makefile`
- Test: `scribe3/web/e2e/author_decisions.test.mjs`

**Interfaces:**
- Consumes: 运行中的 `:3311/:3321`、TokenPlan/Qwen、Hermes、隔离 work。
- Produces: 参考导入→指纹→作者校订批准→合同填满→章节生成→十维三轴→作者裁决→Surreal 回读的结构化证据。

- [ ] 先写脚本断言：每次模型调用均断言 `provider=qwen`、规范 Qwen model、非伪造 request/usage；reference 轴和作者理由均可回读。
- [ ] 脚本只用浏览器输入与点击完成作者动作；只读 API 用于验证，不用 REST 灌入正典或正文。
- [ ] 接入 `make e2e-quality-real`，明确标注其是本机真调门禁而不是 CI mock。
- [ ] 保存隔离验收报告，审阅文本是否泄露参考原文/作者内部说明，并记录作者可编辑、可拒绝、可修订证据。

## Self-review

- 覆盖了参考对比、真实模型留痕、合同权重/作者裁决、UI 和真人 E2E 五个审计 P0 缺口。
- 没有以字数、mock 或单一 API 成功替代质量验收。
- 未把参考原文加入生成或比较输入；技术边界与现有 Surreal 质量领域保持一致。
