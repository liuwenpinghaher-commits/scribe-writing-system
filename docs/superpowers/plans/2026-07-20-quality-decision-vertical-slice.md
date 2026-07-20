# 质量决策与参考作品首条真实纵向链 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让作者从真实章节正文创建不可变质量快照，获得固定十维系统判断、喜欢作品目标达成度和作者高权重裁决，并把证据、分歧、供应商身份与上下文 Manifest 持久化为可复验结果。

**Architecture:** 在 `scribe3/quality/` 建立独立而窄的质量领域包；正文、合同、参考作品、快照和判断仍以 SurrealDB 为唯一权威。所有 LLM 步骤通过 `CreativeContextEngine` 编译 `quality_chapter`、`reference_fingerprint`、`reference_compare` 上下文，再直连官方 DeepSeek；作者、系统和参考三轴分开保存，不生成小说总分。

**Tech Stack:** Python 3.11+、Pydantic v2、FastAPI、SurrealDB、官方 DeepSeek、React、Vitest、pytest。

## Global Constraints

- 固定十维为：连贯性与因果、人物真实性、场景必要性、结构与节奏、悬念与兑现、情绪效力、阅读体验、语言与声音、主题与潜台词、原创性。
- 作者、系统、参考三轴分别保存；默认 `wA=0.50`、`wS=0.30`、`wR=0.20`，并强制 `wA > wS` 且 `wA > wR`。
- 作者未评分时不计算决策指数；决策指数只用于同一维度内排序，禁止跨维度求和或生成小说总分。
- 系统必须先完成有原文证据的判断；LLM 自报置信度不进入最终置信度。
- 参考作品支持 `close / inspired / contrast / avoid`；参考原文不得进入生成任务，只能进入 `reference_fingerprint` 或隔离的 `reference_compare`。
- 每个 LLM 判断必须绑定 `request_id + manifest_id + actual_input_hash + provider_request_id/model/usage`；缺 key、空 JSON、证据锚点无效或上下文缺失必须显式失败。
- SurrealDB 和现有领域模型是唯一业务权威；不引入 SQLite、文件投影或第二套正文/Canon 权威。
- 不接入、不依赖、不预留 Spectron；不启动 SurrealDB/Hermes 升级；不扩大证据缓存。
- 不打印、持久化或提交任何真实 secret；测试使用占位值和注入 transport。
- 所有行为修改按 RED → GREEN；新代码不得继续堆入 `app.py` 或 `store.py`。

---

### Task 1: 冻结质量合同、十维量表与三轴数学合同

**Files:**
- Create: `scribe3/quality/__init__.py`
- Create: `scribe3/quality/models.py`
- Create: `scribe3/quality/rubrics.py`
- Test: `scribe3/tests/test_quality_contracts.py`

**Interfaces:**
- Produces: `CORE_DIMENSIONS`、`QualityContractRevision`、`ReferenceTarget`、`EvidenceAnchor`、`QualityJudgment`、`ThreeAxisDecision`、`decision_index()`。
- Consumes: 无生产存储；本任务只建立不可变纯合同。

- [x] **Step 1: 写失败合同测试**

测试逐项断言：十维键和顺序固定；五级锚点只允许1至5；`not_applicable/insufficient/degraded/conflicted` 不允许分数；`evaluable` 必须有分数、效果、机制和至少一个证据锚点；`ReferenceTarget.mode` 仅接受四种模式；默认权重精确为0.50/0.30/0.20；作者权重不高于任一机器轴时拒绝；作者缺席返回 `None`；不得出现 `total_score` 字段。

- [x] **Step 2: 运行 RED**

Run:

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_contracts.py -q
```

Expected: FAIL because `scribe3.quality` does not exist.

- [x] **Step 3: 实现最小纯合同**

`CORE_DIMENSIONS` 使用稳定英文键、中文标签、不可变观察项和恰好五级的不可变锚点；`QualityJudgment` 保存 `dimension/evaluator_kind/state/score/effect/mechanism/evidence/counter_evidence/confidence_components`。`ConfidenceComponents` 由服务端可观测信号构造并可持久化，`LLMJudgmentPayload` 不接受最终置信度字段。`decision_index(author, system, reference, weights)` 仅当三轴均存在且状态可评价时计算，返回0至5的小数，不写回模型或小说总分。

- [x] **Step 4: 运行 GREEN**

Run Step 2 同一命令。Expected: PASS。

- [x] **Step 5: Commit**

```bash
git add scribe3/quality/__init__.py scribe3/quality/models.py scribe3/quality/rubrics.py scribe3/tests/test_quality_contracts.py
git commit -m "feat: define quality decision contracts"
```

### Task 2: 建立质量合同、参考作品、快照与判断的 SurrealDB 权威

**Files:**
- Create: `scribe3/migrations/094_quality_decision_core.surql`
- Create: `scribe3/quality/store.py`
- Test: `scribe3/tests/test_quality_store.py`

**Interfaces:**
- Consumes: Task 1 Pydantic 合同与已注入 `SurrealStore`。
- Produces: `QualityStore.save_contract_revision()`、`approve_contract()`、`save_reference_work()`、`save_reference_fingerprint()`、`create_chapter_snapshot()`、`create_job()`、`save_judgments()`、`save_author_judgment()`、`get_evaluation()`。

- [ ] **Step 1: 写真实 SurrealDB RED 测试**

测试通过现有 `store` fixture 执行 migration，覆盖：合同修订只增不改且批准使用CAS；参考作品保存 `source_hash/import_revision/status`；章节快照引用不可变 `chapter_version` 并保存 `content_hash`；作业绑定合同、量表、参考指纹、模型配置和 `actual_input_hash`；系统判断与参考判断不可覆盖作者判断；相同幂等键并发创建只产生一个当前结果；读回正文与证据锚点一致。

- [ ] **Step 2: 运行 RED**

Run:

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_store.py -q
```

Expected: FAIL because migration and `QualityStore` are missing.

- [ ] **Step 3: 实现窄表与原子边界**

migration 定义 `quality_contract_revision/reference_work/reference_fingerprint/reference_target/quality_snapshot/quality_snapshot_member/quality_job/quality_judgment/quality_author_judgment`。正文只存在 `chapter_version.prose`；快照成员保存 record ref、`content_hash` 和有序成员序号。唯一键分别为合同revision、参考导入revision、快照hash、job幂等键和 `job_id + unit + dimension + evaluator_kind`。并发唯一冲突后读回并逐字段比较，不把冲突吞成成功。

- [ ] **Step 4: 运行 GREEN 与 migration 回归**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_quality_store.py \
  scribe3/tests/test_creative_context_store.py \
  scribe3/tests/test_store.py::test_apply_schema_normal_migrations_unaffected -q
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add scribe3/migrations/094_quality_decision_core.surql scribe3/quality/store.py scribe3/tests/test_quality_store.py
git commit -m "feat: persist quality decision truth"
```

### Task 3: 将三类质量任务接入唯一 CreativeContextEngine

**Files:**
- Modify: `scribe3/context_models.py`
- Modify: `scribe3/context_policy.py`
- Modify: `scribe3/context_assembler.py`
- Test: `scribe3/tests/test_quality_context.py`

**Interfaces:**
- Produces: `quality_chapter.v1`、`reference_fingerprint.v1`、`reference_compare.v1` 三个版本化 Policy。
- Consumes: Task 2 的合同、快照、参考指纹 record refs；现有 `CreativeContextEngine.compile()`。

- [ ] **Step 1: 写策略隔离 RED 测试**

测试锁定：`quality_chapter` 必须读冻结正文、批准合同和量表，不得读生成提示或生成推理；`reference_fingerprint` 只读单一参考作品分片，不读本书正文；`reference_compare` 读本书冻结证据与已批准参考指纹，不读参考原文；每个来源都有 revision/digest；缺必需slot时fail loud；Manifest持久化所有 included/omitted 决策。

- [ ] **Step 2: 运行 RED**

Run:

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_quality_context.py -q
```

Expected: FAIL because quality task kinds and policies are unknown.

- [ ] **Step 3: 实现三个声明式 Policy 与适配器**

扩展 `ContextRequest.task_kind` 受控枚举；Policy 明确 `required_slots/forbidden_source_kinds/budget_profile`。Assembler 只把领域对象映射为 `ContextSource`，不复制权威；参考原文物理禁止进入 `draft/final/quality_chapter/reference_compare`，只有抽象指纹可进入比较。

- [ ] **Step 4: 运行 GREEN 与生成链隔离回归**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_quality_context.py \
  scribe3/tests/test_creative_context_contracts.py \
  scribe3/tests/test_creative_context_engine.py \
  scribe3/tests/test_context_assembler.py -q
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add scribe3/context_models.py scribe3/context_policy.py scribe3/context_assembler.py scribe3/tests/test_quality_context.py
git commit -m "feat: compile isolated quality contexts"
```

### Task 4: 导入喜欢作品并生成可校正的分层指纹

**Files:**
- Create: `scribe3/quality/references.py`
- Create: `scribe3/quality/api.py`
- Modify: `scribe3/app.py`
- Test: `scribe3/tests/test_quality_references.py`
- Test: `scribe3/tests/test_quality_api.py`

**Interfaces:**
- Consumes: 现有 `material_import.parse_to_markdown()` 文件解析能力、Task 2 `QualityStore`、Task 3 `reference_fingerprint.v1`、官方 DeepSeek。
- Produces: `POST /references/import`、`POST /references/{id}/fingerprints`、`GET /references/{id}/fingerprints`、`PATCH /references/{id}`。

- [ ] **Step 1: 写 RED 测试**

覆盖 txt/md/pdf/docx 与粘贴文本；导入内容按稳定分片写入 reference 空间而非 material；source hash相同则幂等；DeepSeek JSON必须包含局部机制、跨章聚合、全书指纹、证据、反证、可迁移机制、不可复制要素和适用范围；作者可以校正并批准指纹新revision；任一JSON空响应、证据无法定位或Manifest缺失都使任务失败且不发布批准指纹。

- [ ] **Step 2: 运行 RED**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_quality_references.py scribe3/tests/test_quality_api.py -q
```

Expected: FAIL because reference service and router do not exist.

- [ ] **Step 3: 实现参考作品服务与 API**

复用文件解析，不复用 material 的业务表、召回空间或 kind。指纹服务逐分片调用官方 DeepSeek JSON，验证证据回指后聚合；每次调用写 Context Manifest/Outcome。`app.py` 只执行一次 `include_router(quality_router)`，不得增加质量业务函数。

- [ ] **Step 4: 运行 GREEN 与素材导入回归**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_quality_references.py scribe3/tests/test_quality_api.py \
  scribe3/tests/test_material_import.py -q
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add scribe3/quality/references.py scribe3/quality/api.py scribe3/app.py \
  scribe3/tests/test_quality_references.py scribe3/tests/test_quality_api.py
git commit -m "feat: fingerprint favorite reference works"
```

### Task 5: 实现固定十维系统评价、参考对比与分歧判定

**Files:**
- Create: `scribe3/quality/evaluator.py`
- Create: `scribe3/quality/confidence.py`
- Modify: `scribe3/deepseek_client.py`
- Modify: `scribe3/quality/api.py`
- Test: `scribe3/tests/test_quality_evaluator.py`
- Test: `scribe3/tests/test_deepseek_json.py`

**Interfaces:**
- Produces: `DeepSeekClient.complete_json()`、`QualityEvaluator.evaluate_chapter()`、`compare_references()`、`merge_three_axes()`。
- Consumes: Task 1量表、Task 2快照/存储、Task 3 Policy、Task 4批准指纹。

- [ ] **Step 1: 写六段评价流水线 RED 测试**

测试要求：确定性硬风险先运行；证据提取和评分使用不同请求；评分请求看不到作者分数、生成提示或“AI文本”标记；十维每维都有合法状态；`evaluable` 证据必须能在冻结正文按UTF-16锚点定位；独立反证请求保存反证；高影响判断执行第二次独立上下文评价；参考比较交换顺序；置信度只由覆盖、证据有效率、校准可靠度、独立性和稳定性保守组合；作者与系统相差两档、参考目标冲突或两次高影响判断相反时标记 `conflicted`。

- [ ] **Step 2: 运行 RED**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_deepseek_json.py scribe3/tests/test_quality_evaluator.py -q
```

Expected: FAIL because JSON completion and evaluator are missing.

- [ ] **Step 3: 实现官方 JSON 与评价器**

`complete_json()` 固定 `response_format={"type":"json_object"}`，空内容失败，最多两次有记录的格式修复，最终必须通过Pydantic Schema。Evaluator按“硬风险→证据→评分→反证→重复评价→合并”执行，每次调用独立Manifest/Outcome；系统结果和参考结果分别写 `evaluator_kind=system/reference`，不得在提示或存储中预先混合作者判断。

- [ ] **Step 4: 运行 GREEN 与供应商回归**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_deepseek_json.py scribe3/tests/test_quality_evaluator.py \
  scribe3/tests/test_deepseek_client.py scribe3/tests/test_llm_stream.py -q
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add scribe3/quality/evaluator.py scribe3/quality/confidence.py \
  scribe3/deepseek_client.py scribe3/quality/api.py \
  scribe3/tests/test_quality_evaluator.py scribe3/tests/test_deepseek_json.py
git commit -m "feat: evaluate chapters across ten quality dimensions"
```

### Task 6: 交付真实四栏质量审阅与参考作品入口

**Files:**
- Create: `scribe3/web/src/quality/QualityReview.jsx`
- Create: `scribe3/web/src/quality/ReferenceWorks.jsx`
- Modify: `scribe3/web/src/api.js`
- Modify: `scribe3/web/src/DetailPane.jsx`
- Modify: `scribe3/web/src/layout/EntryRail.jsx`
- Test: `scribe3/web/src/quality/QualityReview.test.jsx`
- Test: `scribe3/web/src/quality/ReferenceWorks.test.jsx`
- Test: `scribe3/web/src/__tests__/detailPane-capabilities.test.jsx`

**Interfaces:**
- Consumes: Tasks 4/5 API。
- Produces: `references` 左轨入口；现有 `review` 详情中的十维三轴判断、证据定位、分歧、降级和作者评分。

- [ ] **Step 1: 写前端 RED 测试**

测试真实交互：导入喜欢作品→查看/校正/批准指纹→为某章创建快照→启动评价→查看十维系统判断和参考目标→填写作者评分→只在三轴齐全时显示同维度决策指数；界面不显示小说总分；证据点击返回章和UTF-16范围；失败、partial、degraded和conflicted各有明确状态；所有用户字段带稳定 `data-field-path`。

- [ ] **Step 2: 运行 RED**

Run:

```bash
cd scribe3/web && npm test -- --run \
  src/quality/QualityReview.test.jsx \
  src/quality/ReferenceWorks.test.jsx \
  src/__tests__/detailPane-capabilities.test.jsx
```

Expected: FAIL because quality UI does not exist.

- [ ] **Step 3: 实现四栏内真实入口**

只在现有 `EntryRail → DetailPane` 路径加入 `references`，并升级既有 `review`；不创建新应用壳、新聊天系统或可视化伴侣。作者评分保存后重新读取服务器三轴结果，不能只改前端本地状态。

- [ ] **Step 4: 运行 GREEN、全前端与 build**

Run:

```bash
cd scribe3/web && npm test -- --run
cd scribe3/web && npm run build
```

Expected: 全部测试PASS，Vite build退出0。

- [ ] **Step 5: Commit**

```bash
git add scribe3/web/src/quality scribe3/web/src/api.js scribe3/web/src/DetailPane.jsx \
  scribe3/web/src/layout/EntryRail.jsx scribe3/web/src/__tests__/detailPane-capabilities.test.jsx
git commit -m "feat: add quality review and reference workspaces"
```

## 本批退出门

- 一条真实章节路径能从当前正文创建不可变快照，经官方DeepSeek获得固定十维系统判断和喜欢作品目标判断，再保存作者评分与分歧。
- 每个LLM结果都有可读回的Manifest、Outcome、供应商身份、usage、有效原文证据和冻结正文hash。
- 作者、系统、参考三轴独立；作者权重默认最高；无小说总分；硬风险不能被加权抵消。
- 参考原文不进入生成上下文，`close/inspired/contrast/avoid` 都有合同测试。
- 本批通过自动化与真实SurrealDB集成后，只能声明“质量决策首条纵向链完成”；校准集、五万字真实UI和真人盲评仍需后续验收。
