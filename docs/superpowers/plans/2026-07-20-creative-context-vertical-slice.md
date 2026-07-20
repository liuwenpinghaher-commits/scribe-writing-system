# Creative Context OS 首条真实纵向链实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让真实写作请求经过 `ContextRequest → ContextPolicy → CreativeContextEngine → ContextManifest → DeepSeek → ContextOutcomeTrace`，并让最终模型输入可重现、输出可追踪。

**Architecture:** 复用现有 `ContextSnapshot`/`ContextAssembler`/`ContextEnvelope`，不创建第二套召回或领域权威。新内核负责声明任务策略、为实际输入生成不可变 Manifest，并在生成结束后写 Outcome Trace；SurrealDB 继续是唯一持久化权威。

**Tech Stack:** Python 3.11+、Pydantic v2、FastAPI、SurrealDB、pytest、现有官方 DeepSeek 客户端。

## Global Constraints

- 全系统只有一个 `CreativeContextEngine`；现有 `ContextAssembler` 是其组装内核，不再平行拼接新提示链。
- SurrealDB 和现有领域模型是唯一业务权威；Manifest 只保存引用、版本、摘要和使用决策。
- 不接入、不依赖、不预留 Spectron 适配层。
- 模型实际输入字节使用 UTF-8 SHA-256 计算 `actual_input_hash`；不得用旧 `envelope_hash` 冒充。
- 秘密正文不得写入 Manifest、Outcome、日志或测试夹具；只保存摘要和屏蔽标记。
- 纯生成继续使用官方 DeepSeek；缺 key、不完整流和 provider 失败必须显式失败。
- 不启动 SurrealDB/Hermes 版本升级，不扩大 Hermes 证据缓存工作。
- 保留现有 `ContextEnvelope` 兼容性；新字段必须具有安全默认值。
- 生产写作路径的统一内核失败不得静默回退旧链。

---

### Task 1: 请求、策略与 Manifest 纯合同

**Files:**
- Create: `scribe3/context_policy.py`
- Create: `scribe3/context_manifest.py`
- Modify: `scribe3/context_models.py`
- Modify: `scribe3/context_assembler.py`
- Test: `scribe3/tests/test_creative_context_contracts.py`

**Interfaces:**
- Produces: `ContextRequest`、`ContextPolicy`、`ContextManifest`、`ContextManifestSource`、`build_context_manifest()`。
- Consumes: 现有 `ContextSnapshot`、`ContextEnvelope`、`ContextSource`。

- [ ] **Step 1: 先写失败测试**

  测试必须锁定：`draft/final` 映射到 `generation.v1`；未知任务拒绝；`ContextRequest` 不把导航快照当内容快照；每个选入来源具有 `content_digest`；最终输入任何一字节改变都改变 `actual_input_hash`；Manifest JSON 不包含来源正文。

- [ ] **Step 2: 运行 RED**

  Run: `pytest -q scribe3/tests/test_creative_context_contracts.py`
  Expected: FAIL，原因是新模块或新合同尚不存在。

- [ ] **Step 3: 实现最小合同**

  `ContextRequest` 至少包含 `request_id/task_kind/target_ref/navigation_snapshot_id/work/chapter/scene_key/phase/actor_role/pov_character/story_time_window/knowledge_cutoff/author_intent_ref/quality_contract_revision/required_slots/forbidden_source_kinds/budget_profile/freshness_requirement/policy_version`。`ContextPolicy` 使用代码内版本化注册表，首版提供 `generation.v1`，不允许 reference 原文冒充 canon。

  `ContextSource` 增加可选 `content_digest`；`_render_block()` 对每个真实选入 `_Item.text` 计算 SHA-256 并写回源对象。`build_context_manifest(request, policy, envelope, rendered_input)` 按有序来源摘要和真实 UTF-8 输入字节产生不可变 Manifest。

- [ ] **Step 4: 运行 GREEN 与旧合同回归**

  Run: `pytest -q scribe3/tests/test_creative_context_contracts.py scribe3/tests/test_context_models.py scribe3/tests/test_context_assembler.py`
  Expected: PASS。

- [ ] **Step 5: 提交**

  `git add scribe3/context_policy.py scribe3/context_manifest.py scribe3/context_models.py scribe3/context_assembler.py scribe3/tests/test_creative_context_contracts.py && git commit -m "feat: add creative context contracts"`

### Task 2: SurrealDB Manifest 与 Outcome 窄存储

**Files:**
- Create: `scribe3/migrations/091_creative_context_core.surql`
- Create: `scribe3/context_store.py`
- Create: `scribe3/context_outcome.py`
- Test: `scribe3/tests/test_creative_context_store.py`

**Interfaces:**
- Consumes: Task 1 `ContextManifest`。
- Produces: `ContextStore.save_manifest()`、`ContextStore.get_manifest()`、`ContextStore.save_outcome()`、`ContextStore.get_outcome()`、`ContextOutcomeTrace`。

- [ ] **Step 1: 先写真实 SurrealDB 失败测试**

  测试必须通过现有 `store` 夹具执行真实 migration，验证 Manifest 主记录与逐来源在一次事务中写入、重复 `manifest_id` 不产生第二份当前真相、Outcome 必须绑定 `request_id + manifest_id + actual_input_hash`、读回结构与 Pydantic 合同一致。

- [ ] **Step 2: 运行 RED**

  Run: `pytest -q scribe3/tests/test_creative_context_store.py`
  Expected: FAIL，原因是新迁移和窄存储尚不存在。

- [ ] **Step 3: 实现最小持久化**

  migration 定义 `context_policy_snapshot/context_manifest/context_manifest_source/context_outcome_trace`，至少对 `manifest_id`、`request_id`、`actual_input_hash`、`source_ref`、`created_at` 建立必要字段与索引。`ContextStore` 只包装已注入 `SurrealStore`，不修改 `store.py`；事务写入使用现有 `transaction()` 边界。

  `ContextOutcomeTrace` 首版保存 `outcome_id/request_id/manifest_id/actual_input_hash/status/provider/model/provider_request_id/usage/output_hash/error/created_at`，不保存正文。

- [ ] **Step 4: 运行 GREEN 与 migration 回归**

  Run: `pytest -q scribe3/tests/test_creative_context_store.py scribe3/tests/test_store.py::test_apply_schema_normal_migrations_unaffected`
  Expected: PASS。

- [ ] **Step 5: 提交**

  `git add scribe3/migrations/091_creative_context_core.surql scribe3/context_store.py scribe3/context_outcome.py scribe3/tests/test_creative_context_store.py && git commit -m "feat: persist context manifests and outcomes"`

### Task 3: 真实写作入口与 DeepSeek 结果链

**Files:**
- Create: `scribe3/context_engine.py`
- Modify: `scribe3/app.py`
- Modify: `scribe3/context_assembler.py`
- Test: `scribe3/tests/test_creative_context_engine.py`
- Test: `scribe3/tests/test_write_context_outcome.py`

**Interfaces:**
- Consumes: Task 1/2 全部合同与存储。
- Produces: `CreativeContextEngine.compile()`；`_assemble_write_instructions()` 的真实 Manifest 绑定；`/chat/write` 完成、失败、取消 Outcome Trace。

- [ ] **Step 1: 先写失败测试**

  引擎测试锁定：只调用现有 `ContextAssembler`；必需 slot 缺失显式失败；禁用来源不进模型输入；Manifest 与实际返回的完整 instructions 字节哈希相等。入口测试锁定：统一内核失败不走旧链；官方 DeepSeek `response.completed` 后写 succeeded Outcome；failed/incomplete/cancelled 也写真实终态；输出哈希来自供应商原始文本流，不是 UI 摘要。

- [ ] **Step 2: 运行 RED**

  Run: `pytest -q scribe3/tests/test_creative_context_engine.py scribe3/tests/test_write_context_outcome.py`
  Expected: FAIL，原因是引擎和真实接线尚不存在。

- [ ] **Step 3: 实现统一编译与绑定**

  `CreativeContextEngine.compile(request, snapshot, query, mode, render)` 调用旧 Assembler 获得 Envelope，应用 Policy 的必需/禁用检查，用 `render(envelope)` 生成完整实际模型输入，然后一次性建立并持久化 Manifest。返回值包含 `request/envelope/manifest/rendered_input`。

  `_assemble_write_instructions_v1` 使用引擎编译完整 instructions，并向已有 `envelope_trace` 回填 `request_id/manifest_id/policy_version/actual_input_hash`。生产不再依赖默认关闭的 `SCRIBE3_CONTEXT_ASSEMBLER_V1`；统一内核异常直接向上抛出，不执行旧散点链。

- [ ] **Step 4: 实现 Outcome 写入**

  `_stream_write` 单独累积供应商原始 delta 以计算 `output_hash`，不将原文放进 trace。`chat_write_post` 的完成回调从安全 context trace 取 Manifest 绑定，使用 provider/model/usage/response_id/status/error 写入 `ContextOutcomeTrace`。Outcome 写入失败必须记错，不得伪造 succeeded。

- [ ] **Step 5: 运行 GREEN 与写作回归**

  Run: `pytest -q scribe3/tests/test_creative_context_engine.py scribe3/tests/test_write_context_outcome.py scribe3/tests/test_context_assembler.py scribe3/tests/test_selection.py scribe3/tests/test_deepseek_client.py scribe3/tests/test_llm.py`
  Expected: PASS。

- [ ] **Step 6: 提交**

  `git add scribe3/context_engine.py scribe3/app.py scribe3/context_assembler.py scribe3/tests/test_creative_context_engine.py scribe3/tests/test_write_context_outcome.py && git commit -m "feat: route writing through creative context engine"`

## 本批退出门

- 至少一条真实 `/chat/write` 生产路径具备 Manifest 和 Outcome 完整链，不是只有类和空表。
- `actual_input_hash == sha256(官方 DeepSeek 实际收到的 system instructions UTF-8 字节)`。
- 失败、不完整、取消都有 Outcome，不冒充成功。
- 旧 ContextAssembler 行为回归通过，限知/秘密测试通过。
- 本批不宣称十维质量引擎、参考作品比较或五万字真人验收已完成。
