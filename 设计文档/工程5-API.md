# 工程5 · API 接口设计(协作回路 REST 全集)

> **上游根**：[00-总纲与数据模型](00-总纲与数据模型.md) · [内核1-作者协作回路](内核1-作者协作回路.md)
> **本文职责**：定义 Scribe 前端与后端编排层之间的唯一 HTTP 契约——资源 CRUD、内核协作回路端点、异步生成任务、服务型端点、统一分页/幂等/错误码约定。
> **本文取代旧版 15-API接口设计.md**。资源命名严格对齐 00 §4 实体，内核实体（Imagination / AuthorIntent / OptionSet / FeedbackNote / TasteModel / PreferenceSignal）作为一等公民完整覆盖。
> 设计基线 2026 年 6 月。

---

## 目录

1. [在回路中的位置与职责](#1-在回路中的位置与职责)
2. [设计目标与百万字挑战](#2-设计目标与百万字挑战)
3. [详细设计](#3-详细设计)
   - 3.1 [统一约定](#31-统一约定)
   - 3.2 [鉴权占位](#32-鉴权占位)
   - 3.3 [错误响应结构与状态码规范](#33-错误响应结构与状态码规范)
   - 3.4 [内核端点：imaginations](#34-内核端点imaginations)
   - 3.5 [内核端点：author-intent](#35-内核端点author-intent)
   - 3.6 [内核端点：optionsets](#36-内核端点optionsets)
   - 3.7 [内核端点：feedback-notes](#37-内核端点feedback-notes)
   - 3.8 [内核端点：taste-model](#38-内核端点taste-model)
   - 3.9 [内核端点：preference-signals](#39-内核端点preference-signals)
   - 3.10 [资源端点：works](#310-资源端点works)
   - 3.11 [资源端点：volumes](#311-资源端点volumes)
   - 3.12 [资源端点：chapters](#312-资源端点chapters)
   - 3.13 [资源端点：segments](#313-资源端点segments)
   - 3.14 [资源端点：characters](#314-资源端点characters)
   - 3.15 [资源端点：setting-items](#315-资源端点setting-items)
   - 3.16 [资源端点：entity-relations](#316-资源端点entity-relations)
   - 3.17 [资源端点：timeline-events](#317-资源端点timeline-events)
   - 3.18 [资源端点：foreshadows](#318-资源端点foreshadows)
   - 3.19 [资源端点：consistency-flags](#319-资源端点consistency-flags)
   - 3.20 [资源端点：memory](#320-资源端点memory)
   - 3.21 [资源端点：snapshots](#321-资源端点snapshots)
   - 3.22 [资源端点：materials](#322-资源端点materials)
   - 3.23 [异步生成：任务提交与进度轮询](#323-异步生成任务提交与进度轮询)
   - 3.24 [SSE 进度订阅](#324-sse-进度订阅)
   - 3.25 [服务型端点：上下文拼装与语义检索](#325-服务型端点上下文拼装与语义检索)
   - 3.26 [服务型端点：一致性校验与伏笔扫描](#326-服务型端点一致性校验与伏笔扫描)
   - 3.27 [服务型端点：质量评估](#327-服务型端点质量评估)
   - 3.28 [修订回流端点](#328-修订回流端点)
   - 3.29 [批量操作端点](#329-批量操作端点)
4. [数据契约](#4-数据契约)
5. [对外接口：端点全索引](#5-对外接口端点全索引)
6. [失败模式与缓解](#6-失败模式与缓解)
7. [MVP vs 完整版](#7-mvp-vs-完整版)
8. [证据与引用](#8-证据与引用)
9. [开放问题](#9-开放问题)

---

## 1. 在回路中的位置与职责

### 1.1 一句话定位

工程5 是 Scribe **协作回路对外暴露的唯一 HTTP 界面**。它既是前端与后端的契约层，也是内核机制（想象捕获 / 北极星 / 多方案 / 意见反馈）对外的 REST 入口。旧版 15 仅覆盖门槛层实体（chapters / segments / characters…），完全缺失内核实体的端点——本文是对这一空缺的系统性补全，同时保留旧版对门槛层的完整覆盖。

### 1.2 职责边界

**本文负责**：

| 类别 | 具体范围 |
|---|---|
| 内核端点（新增） | imaginations、author-intent、optionsets（含 choose）、feedback-notes（含 confirm/rewrite）、taste-model、preference-signals |
| 正文资源 | works、volumes、chapters、segments |
| 设定·连贯 | characters、setting-items、entity-relations、timeline-events、foreshadows、consistency-flags |
| 记忆·版本·素材 | memory、snapshots、materials |
| 异步任务 | 触发规划/写章/OptionSet生成/FeedbackNote重做；task_id → 轮询/SSE |
| 服务型端点 | assembleContext(只读)、语义检索、一致性校验、伏笔扫描、质量评估 |
| 修订回流 | revisions、impact-analysis |
| 批量操作 | batch-generate、batch-adjudicate |
| 统一约定 | 游标分页、过滤、部分响应、幂等、错误码体系 |

**本文不负责**：

| 排除项 | 由谁负责 |
|---|---|
| LLM 调用内部实现 | 工程3-LLM接入与成本 |
| Agent 编排状态机 | 实现3-编排引擎 |
| 记忆摘要算法 | 实现4-记忆与检索 |
| 品味模型学习算法 | 内核2-品味与偏好模型 |
| 版本快照分支算法 | 工程4-版本与回流 |
| 鉴权加密与会话细节 | 工程7-工程化与路线图 |
| WebSocket 实时协同编辑 | 工程2-交互与编辑器（本文只定义 SSE） |

### 1.3 回路中的位置图

```
        ┌──────────────── 人(作者) ──────────────────┐
        │  想象 / 北极星 / 选方案 / 提意见              │
        └──────────────┬─────────────▲───────────────┘
                       │ HTTP 请求    │ HTTP 响应
                       ▼             │
        ┌──────── 工程5 API 层(本文) ──────────────────┐
        │  内核端点  imaginations / author-intent /    │
        │           optionsets / feedback-notes /      │
        │           taste-model / preference-signals   │
        │  资源端点  works / chapters / segments / ... │
        │  任务端点  POST task → GET poll / SSE stream  │
        │  服务端点  context / check / evaluate / ...  │
        └──────────────┬─────────────▲───────────────┘
                       │ 内部调用     │ 内部响应
                       ▼             │
        ┌──────── 后端编排层 (实现1/2/3/4) ────────────┐
        │  OutlineAgent / WritingAgent /               │
        │  FeedbackRewriteAgent / OptionSetAgent       │
        └──────────────────────────────────────────────┘
```

---

## 2. 设计目标与百万字挑战

### 2.1 设计目标

| 编号 | 目标 | 可度量指标 |
|---|---|---|
| G-1 | 资源命名严格对齐 00 §4 实体，无自造命名 | 端点路径与实体名 100% 对应，CR 前检查 |
| G-2 | 内核实体一等公民——imaginations / author-intent / optionsets / feedback-notes / taste-model 均有完整 CRUD + 动作端点 | 覆盖率 100%；无内核实体仅靠 jsonb 嵌套在 works 里返回 |
| G-3 | 异步生成全程非阻塞——所有 LLM 调用走 POST task → GET poll / SSE | 章生成 P95 ≤ 120s；前端无同步等待 |
| G-4 | 幂等键必填——断点续跑不重复触发 | 所有写任务端点携带 idempotency_key；重复提交返回 409 含已有 task_id |
| G-5 | 游标分页全覆盖——百万字下 300–500 章不全量返回 | 所有列表端点强制分页；禁止无参数全量拉取大集合 |
| G-6 | 错误码可机读——前端可显示定向提示 | 所有 4xx/5xx 响应含 error_code 枚举 |
| G-7 | 意见→重做端到端 ≤ 90s——FeedbackNote 提交到新 Snapshot 出现 | SSE 推送 rewrite_complete 事件；前端可 diff 预览 |

### 2.2 百万字挑战在 API 层的具体表现

**挑战1：大集合分页**

一部百万字小说含 300–500 章、数千段落、数百设定项、数百条 Imagination。`GET /works/{id}/chapters` 若全量返回，响应体可达数 MB。
→ 应对：强制游标分页（cursor + limit），禁止无参数全量拉取（返回 400）；提供 `fields` 参数裁剪大文本字段（text / content / embedding 等）。

**挑战2：异步生成时延**

WritingAgent 生成一章含检索 + LLM 调用 + ReviewAgent 审校，P95 时延约 60–120 秒。FeedbackNote 重做 P95 ≤ 90 秒。前端不能同步等待。
→ 应对：全部走 task 异步模式；提供 SSE endpoint 供前端实时订阅进度，细粒度到每个 Agent 阶段完成事件及关键回路事件（imagination.used / deviation_detected / rewrite_complete）。

**挑战3：幂等与断点续跑**

网络抖动下前端可能重复提交生成任务。宕机后编排引擎需从上次检查点恢复，不重复计费。
→ 应对：所有写任务端点必须携带 `idempotency_key`（建议值为 `{chapter_id}-attempt-{n}`）；服务端以此键做去重，返回已有 task_id 而不重新入队。

**挑战4：FeedbackNote 历史规模**

500 章 × 平均 3 轮重做 = 1500 条 FeedbackNote。历史查询不能全量加载。
→ 应对：FeedbackNote 按 target_id / chapter_id 范围建索引；列表端点支持 target_type / target_id 过滤；前端虚拟滚动 + 分页（limit=20）。

**挑战5：Imagination 库膨胀**

写到第 300 章时 Imagination 库可能积累数百条。status 过滤 + 向量检索必须高效。
→ 应对：(work_id, status) 复合索引；`GET /works/{id}/imaginations` 支持 status 多值过滤；embedding 向量检索走内部服务，不通过 API 层直接暴露原始向量。

**挑战6：OptionSet 并发决策**

作者可能同时面对第 14 章的意见反馈、第 15 章的方案选择、第 16 章的想象排期。多个 SSE 通道并发。
→ 应对：每个 FeedbackNote / OptionSet 生成任务独立 task_id，独立 SSE channel；前端按 task_id 订阅，互不干扰。

---

## 3. 详细设计

### 3.1 统一约定

#### 3.1.1 Base URL

```
/api/v1
```

所有端点均以此前缀开头。版本通过路径管理，不使用 Header 版本号（【设计决策】，便于前端路由和 API 网关缓存区分）。

#### 3.1.2 资源命名约定

- URL 路径：小写 kebab-case（`setting-items`、`entity-relations`、`consistency-flags`、`author-intent`、`feedback-notes`、`taste-model`、`preference-signals`）
- JSON 字段：小写 snake_case（`work_id`、`nl_critique`、`parsed_directive`、`chosen_option_id`）
- 实体 ID：UUID v7 字符串（`"019018ab-..."`），全部用字符串传输，不用整数 ID
- 路径段与 00 §4 实体名对应关系：

| URL 路径段 | 00 §4 实体 |
|---|---|
| `imaginations` | Imagination |
| `author-intent` | AuthorIntent |
| `optionsets` | OptionSet |
| `feedback-notes` | FeedbackNote |
| `taste-model` | TasteModel |
| `preference-signals` | PreferenceSignal |
| `works` | Work |
| `volumes` | Volume |
| `chapters` | Chapter |
| `segments` | Segment |
| `characters` | Character + CharState |
| `setting-items` | SettingItem |
| `entity-relations` | EntityRelation |
| `timeline-events` | TimelineEvent |
| `foreshadows` | Foreshadow |
| `consistency-flags` | ConsistencyFlag |
| `memory` | MemoryEntry |
| `snapshots` | Snapshot |
| `materials` | Material + MaterialRef |

#### 3.1.3 游标分页规范

所有返回列表的端点均支持游标分页。**禁止**无参数全量拉取大集合（`chapters`、`segments`、`imaginations`、`setting-items`、`feedback-notes` 等）——无 cursor 且无 limit 参数时返回 `400 PAGINATION_REQUIRED`。

**请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `cursor` | string | null | 上一页末尾的游标（不透明字符串，服务端 Base64 编码） |
| `limit` | integer | 20 | 每页条数，上限 100；超出返回 `400 PAGINATION_LIMIT_EXCEEDED` |
| `order` | string | `"asc"` | `asc` / `desc`，按 seq 或 created_at 排序 |

**响应体结构**（所有列表响应统一包装）：

```json
{
  "data": [ "..." ],
  "pagination": {
    "cursor": "eyJzZXEiOjIwfQ==",
    "has_more": true,
    "total_count": 312
  }
}
```

`cursor` 为 Base64 编码的内部偏移凭证，客户端不解析其内容，仅原样传给下一次请求的 `cursor` 参数。`total_count` 为近似值（允许缓存 5 分钟），仅用于 UI 显示进度条，不作精确语义保证。

#### 3.1.4 过滤与排序约定

过滤参数以 query string 传递，字段名与 00 §4 对齐：

```
GET /api/v1/works/{work_id}/imaginations?status=scheduled&status=structured&order=asc&limit=50
GET /api/v1/works/{work_id}/feedback-notes?target_type=segment&target_id={segment_id}
GET /api/v1/works/{work_id}/foreshadows?state=planted&state=triggered
GET /api/v1/works/{work_id}/chapters?status=draft&volume_id={volume_id}
```

多值过滤（如 `status`）允许重复参数名（符合 HTML Form 规范）。字符串包含过滤使用 `__contains` 后缀（如 `name__contains=神器`）。

#### 3.1.5 部分响应（字段裁剪）

对于含大文本字段的资源（`Segment.text`、`Imagination.raw_text`、`Snapshot.content`、`FeedbackNote.nl_critique`），提供 `fields` 参数裁剪：

```
GET /api/v1/works/{work_id}/chapters?fields=id,seq,title,status,word_count
GET /api/v1/works/{work_id}/imaginations?fields=id,type,status,scheduled_for,created_at
```

不指定 `fields` 时默认返回完整资源（含大字段）。`embedding` 字段默认永不返回（纯向量无前端展示意义），需调试时显式加 `fields=embedding`。

#### 3.1.6 Content-Type

- 请求体：`application/json`（除文件上传端点外）
- 响应体：`application/json`
- SSE：`text/event-stream`

#### 3.1.7 幂等性约定

所有触发异步 LLM 任务的 POST 端点**必须**携带 `idempotency_key` 字段（string，建议格式见各端点）。服务端以此键做去重：

- 相同 key 且任务已存在 → 返回 `409 TASK_ALREADY_SUBMITTED`，响应体含已有 `task_id` 和 `status`
- 相同 key 且任务已完成 → 同上，前端可直接用已有 `task_id` 查结果
- 不同 key → 正常创建新任务

不携带 `idempotency_key` 的任务提交请求返回 `400 MISSING_REQUIRED_FIELD`。

#### 3.1.8 软删除行为

重要实体（Work、Volume、Chapter、Segment、Imagination、FeedbackNote、OptionSet、Snapshot、Material 等）均支持软删除（`deleted_at` 字段）。软删除后：
- 默认从列表中消失（等同于物理删除对调用方的语义）
- 可通过 `include_deleted=true` 参数查询已删除资源（需特殊权限）
- 软删除后的资源仍可被 GET 单条查询（返回带 `deleted_at` 的完整对象）

---

### 3.2 鉴权占位

> 【设计决策】鉴权细节由工程7-工程化与路线图展开。本文仅定义 API 层的鉴权头约定与行为占位。

所有端点（除 `/health` 和 `/api/v1/auth/*`）均要求在请求头中携带：

```http
Authorization: Bearer <token>
```

`token` 可为 API Key（机器对机器调用）或会话 JWT（前端用户会话），由工程7 决定具体签发机制。

**鉴权失败（401）**：

```json
{
  "error_code": "AUTH_INVALID_TOKEN",
  "message": "Token is missing, invalid, or expired.",
  "request_id": "req_01j8x..."
}
```

**权限不足（403）**：

```json
{
  "error_code": "AUTH_FORBIDDEN",
  "message": "You do not have permission to access this resource.",
  "request_id": "req_01j8x..."
}
```

---

### 3.3 错误响应结构与状态码规范

#### 3.3.1 统一错误响应体

所有 4xx / 5xx 响应均使用以下 JSON 结构：

```json
{
  "error_code": "CHAPTER_NOT_FOUND",
  "message": "Chapter with id '019018ab-...' not found.",
  "detail": {
    "chapter_id": "019018ab-..."
  },
  "request_id": "req_01j8xkm..."
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `error_code` | string | 机读枚举，见下表 |
| `message` | string | 人读描述，英文 |
| `detail` | object | 可选，额外的结构化上下文 |
| `request_id` | string | 链路追踪 ID，每请求唯一 |

#### 3.3.2 HTTP 状态码使用规范

| 状态码 | 场景 |
|---|---|
| `200 OK` | GET / PUT / PATCH 成功 |
| `201 Created` | POST 创建资源成功，响应体含完整新资源 |
| `202 Accepted` | POST 提交异步任务成功，响应体含 `task_id` |
| `204 No Content` | DELETE 成功（无响应体） |
| `400 Bad Request` | 请求体格式错误、参数校验失败、缺少必填字段 |
| `401 Unauthorized` | Token 缺失/无效/过期 |
| `403 Forbidden` | Token 有效但无权访问 |
| `404 Not Found` | 资源不存在（含软删除资源） |
| `409 Conflict` | 幂等键冲突（task 已提交）、状态机冲突（如对 done 章节重复触发生成）、硬红线删除需确认 |
| `422 Unprocessable Entity` | 业务逻辑校验失败（如章节 seq 重复、OptionSet 方案差异不足） |
| `429 Too Many Requests` | 速率限制 |
| `500 Internal Server Error` | 服务端未预期错误 |
| `503 Service Unavailable` | LLM Provider 不可用或任务队列满 |

#### 3.3.3 error_code 枚举（完整版）

```
# 资源类（门槛层）
WORK_NOT_FOUND
VOLUME_NOT_FOUND
CHAPTER_NOT_FOUND
SEGMENT_NOT_FOUND
CHARACTER_NOT_FOUND
SETTING_ITEM_NOT_FOUND
FORESHADOW_NOT_FOUND
CONSISTENCY_FLAG_NOT_FOUND
SNAPSHOT_NOT_FOUND
MEMORY_ENTRY_NOT_FOUND
MATERIAL_NOT_FOUND

# 资源类（内核层）——新增
IMAGINATION_NOT_FOUND
AUTHOR_INTENT_NOT_FOUND
OPTIONSET_NOT_FOUND
FEEDBACK_NOTE_NOT_FOUND
TASTE_MODEL_NOT_FOUND
PREFERENCE_SIGNAL_NOT_FOUND

# 状态机冲突
CHAPTER_STATUS_CONFLICT
TASK_ALREADY_SUBMITTED
TASK_NOT_FOUND
FORESHADOW_STATE_INVALID
IMAGINATION_STATUS_INVALID
OPTIONSET_ALREADY_CHOSEN        # OptionSet 已有选择，不可重复 choose
FEEDBACK_NOT_CONFIRMED          # FeedbackNote 未确认 directive，不可触发重做
FEEDBACK_REWRITE_IN_PROGRESS    # 重做任务已在执行中

# 业务校验
SEQ_DUPLICATE
VOLUME_CHAPTER_MISMATCH
WORK_MISMATCH
CONSISTENCY_FLAG_ALREADY_ADJUDICATED
OPTIONSET_DIFF_INSUFFICIENT     # OptionSet 方案差异度不足（内部校验失败重试时）
HARD_REDLINE_DELETE_REQUIRES_CONFIRM  # 删除 hard 红线需要二次确认

# 参数错误
PAGINATION_REQUIRED             # 大集合端点未提供分页参数
PAGINATION_LIMIT_EXCEEDED       # limit > 100
MISSING_REQUIRED_FIELD
INVALID_FIELD_VALUE
IDEMPOTENCY_KEY_MISSING

# 鉴权
AUTH_INVALID_TOKEN
AUTH_FORBIDDEN

# 服务
LLM_PROVIDER_UNAVAILABLE
TASK_QUEUE_FULL
CONTEXT_BUDGET_EXCEEDED
EMBEDDING_SERVICE_UNAVAILABLE
```

### 3.4 内核端点：imaginations

**资源路径**：`/api/v1/works/{work_id}/imaginations`

对应 00 §4.1 实体：`Imagination`（`id, work_id, raw_text, type, structured, status, scheduled_for, resulted_in_chapter, embedding, obsolete, created_at, deleted_at`）

`type` 枚举：`scene_wish` / `character_impulse` / `plot_what_if` / `world_idea` / `theme_seed` / `mood` / `twist`

`status` 枚举：`captured` / `structured` / `scheduled` / `used`

---

#### `POST /api/v1/works/{work_id}/imaginations` — 捕获新想象

这是内核协作回路的**主入口之一**。立即返回 `captured` 态的 Imagination；LLM 结构化异步进行，不阻塞捕获动作。

**请求体**：

```json
{
  "raw_text": "我想要一场雨夜的背叛，两人在茶馆相遇，没有正面冲突但全是张力",
  "type_hint": "scene_wish",
  "scheduled_for": {
    "type": "volume",
    "ref_id": "019018ab-vol2-...",
    "label": "第二卷"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `raw_text` | string | 是 | 作者原始输入，永不修改，max 2000 字符 |
| `type_hint` | string | 否 | 作者提示的类型（枚举同 type），不填则由 LLM 自动推断 |
| `scheduled_for` | object | 否 | 排期：`{ type: "chapter"\|"volume"\|"range", ref_id, label, from_seq?, to_seq? }`；不填则 LLM 推荐 |

**响应体（201）**：

```json
{
  "id": "019018ab-imag-0001",
  "work_id": "019018ab-...",
  "raw_text": "我想要一场雨夜的背叛，两人在茶馆相遇，没有正面冲突但全是张力",
  "type": null,
  "structured": null,
  "status": "captured",
  "scheduled_for": {
    "type": "volume",
    "ref_id": "019018ab-vol2-...",
    "label": "第二卷"
  },
  "resulted_in_chapter": null,
  "obsolete": false,
  "created_at": "2026-06-19T10:00:00Z"
}
```

> `type` 和 `structured` 初始为 null，LLM 结构化完成后异步更新为 `structured` 态，前端可通过 SSE 订阅 `imagination.structured` 事件（见 §3.24）或轮询 GET 获取。

---

#### `GET /api/v1/works/{work_id}/imaginations` — 列出想象库

```
GET /api/v1/works/{work_id}/imaginations?status=scheduled&status=structured&order=desc&limit=20&cursor=...
```

**过滤参数**：

| 参数 | 说明 |
|---|---|
| `status` | 多值：`captured` / `structured` / `scheduled` / `used` |
| `type` | 多值：`scene_wish` / `character_impulse` / ... |
| `obsolete` | `true` / `false`（默认 false，不返回已标记过时的） |
| `scheduled_for_chapter_id` | 精确排期到某章的想象 |
| `scheduled_for_volume_id` | 精确排期到某卷的想象 |

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "019018ab-imag-0001",
      "work_id": "019018ab-...",
      "raw_text": "我想要一场雨夜的背叛……",
      "type": "scene_wish",
      "structured": {
        "core_intent": "雨夜茶馆，两人无声对峙，张力全靠细节传递",
        "implementation_hint": "写茶馆场景，克制情绪，全用环境和动作",
        "type_confidence": 0.93,
        "estimated_chapters": ["第14章", "第15章"]
      },
      "status": "scheduled",
      "scheduled_for": {
        "type": "volume",
        "ref_id": "...",
        "label": "第二卷"
      },
      "resulted_in_chapter": null,
      "obsolete": false,
      "created_at": "2026-06-19T10:00:00Z"
    }
  ],
  "pagination": {
    "cursor": "eyJzZXEiOjF9",
    "has_more": false,
    "total_count": 47
  }
}
```

---

#### `GET /api/v1/works/{work_id}/imaginations/{imagination_id}` — 获取单条想象

**响应体（200）**：完整 Imagination 对象（同上，含全部字段）。

---

#### `PATCH /api/v1/works/{work_id}/imaginations/{imagination_id}` — 更新想象（手动排期/标记过时）

作者可手动修改排期、标记过时，或在 LLM 结构化完成后修正 `structured` 内容。

**请求体**（只传需要更新的字段）：

```json
{
  "scheduled_for": {
    "type": "chapter",
    "ref_id": "019018ab-chap-014",
    "label": "第14章"
  },
  "obsolete": false
}
```

**可更新字段**：`scheduled_for`、`obsolete`、`structured`（允许人工修正 LLM 结构化结果）。

**不可更新字段**：`raw_text`（永不修改，保护作者原始输入）、`status`（由状态机控制）。

**响应体（200）**：完整更新后的 Imagination 对象。

---

#### `POST /api/v1/works/{work_id}/imaginations/{imagination_id}/confirm-schedule` — 确认排期

作者在前端看到 LLM 推荐排期后，点击确认或修改后确认，将 Imagination 从 `structured` 推进到 `scheduled`。

**请求体**：

```json
{
  "scheduled_for": {
    "type": "chapter",
    "ref_id": "019018ab-chap-014",
    "label": "第14章·天机城"
  }
}
```

**响应体（200）**：

```json
{
  "id": "019018ab-imag-0001",
  "status": "scheduled",
  "scheduled_for": {
    "type": "chapter",
    "ref_id": "019018ab-chap-014",
    "label": "第14章·天机城"
  },
  "updated_at": "2026-06-19T10:05:00Z"
}
```

**状态机约束**：仅 `structured` 态可调用此端点；`captured` 态（LLM 还未处理完）返回 `409 IMAGINATION_STATUS_INVALID`。

---

#### `DELETE /api/v1/works/{work_id}/imaginations/{imagination_id}` — 软删除想象

**响应（204）**：无响应体。软删除后 embedding 仍保留供内核2 品味分析使用。

---

### 3.5 内核端点：author-intent

**资源路径**：`/api/v1/works/{work_id}/author-intent`

对应 00 §4.1 实体：`AuthorIntent`（`id, work_id(1:1), reader_feeling, core_emotional_arc, why_write, central_promise, do_not_betray, version, updated_at`）

AuthorIntent 与 Work 是 1:1 关系，无列表端点，只有 GET/PUT/PATCH。

---

#### `GET /api/v1/works/{work_id}/author-intent` — 获取北极星

**响应体（200）**：

```json
{
  "id": "019018ab-intent-0001",
  "work_id": "019018ab-...",
  "reader_feeling": "一种温热的孤独感——被爱过，但爱本身是短暂的，而孤独比任何人都长寿",
  "core_emotional_arc": "从麻木到在意到再次失去到接受失去本身",
  "why_write": "我想写一个从不被人认真对待但始终认真对待他人的人",
  "central_promise": "每一章都会让你觉得某件小事突然有了重量",
  "do_not_betray": [
    {
      "id": "rl-001",
      "description": "不能出现任何形式的'爱情能解决一切'",
      "severity": "hard",
      "added_at": "2026-06-19T10:00:00Z"
    },
    {
      "id": "rl-002",
      "description": "主角的核心缺陷不能被外部力量治愈，只能被他自己接受",
      "severity": "hard",
      "added_at": "2026-06-19T10:00:00Z"
    },
    {
      "id": "rl-003",
      "description": "尽量避免大团圆结局",
      "severity": "soft",
      "added_at": "2026-06-19T10:05:00Z"
    }
  ],
  "version": 3,
  "updated_at": "2026-06-19T11:00:00Z"
}
```

若该作品尚未创建 AuthorIntent，返回 `404 AUTHOR_INTENT_NOT_FOUND`（提示前端引导作者填写书写向导）。

---

#### `PUT /api/v1/works/{work_id}/author-intent` — 初始化或整体替换北极星

用于书写向导完成后首次保存，或整体覆盖更新。

**请求体**：

```json
{
  "reader_feeling": "一种温热的孤独感——被爱过，但爱本身是短暂的，而孤独比任何人都长寿",
  "core_emotional_arc": "从麻木到在意到再次失去到接受失去本身",
  "why_write": "我想写一个从不被人认真对待但始终认真对待他人的人",
  "central_promise": "每一章都会让你觉得某件小事突然有了重量",
  "do_not_betray": [
    {
      "description": "不能出现任何形式的'爱情能解决一切'",
      "severity": "hard"
    }
  ],
  "change_reason": "初始化书写向导"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `reader_feeling` | string | 是 | 读者情感落点，max 500 字符 |
| `core_emotional_arc` | string | 是 | 核心情感弧线，max 300 字符 |
| `why_write` | string | 否 | 写作驱动（私密），max 500 字符 |
| `central_promise` | string | 否 | 核心承诺，max 300 字符 |
| `do_not_betray` | array | 否 | RedLine 数组；每条含 `description`(string)、`severity`("hard"\|"soft") |
| `change_reason` | string | 否 | 本次更新原因，记入历史快照 |

**响应体（200/201）**：完整 AuthorIntent 对象，`version` 递增。

---

#### `PATCH /api/v1/works/{work_id}/author-intent` — 增量更新北极星

只传需要修改的字段。`do_not_betray` 采用**列表替换**语义（传入完整新列表，服务端计算 diff）。

**请求体**（示例：新增一条软红线）：

```json
{
  "do_not_betray": [
    {
      "id": "rl-001",
      "description": "不能出现任何形式的'爱情能解决一切'",
      "severity": "hard"
    },
    {
      "id": "rl-002",
      "description": "主角的核心缺陷不能被外部力量治愈，只能被他自己接受",
      "severity": "hard"
    },
    {
      "id": "rl-003",
      "description": "尽量避免大团圆结局",
      "severity": "soft"
    },
    {
      "description": "不要安排一个'命中注定的强者身份'来解救他",
      "severity": "hard"
    }
  ],
  "change_reason": "第50章后感觉需要强化这条红线"
}
```

**硬红线保护机制**：若 `do_not_betray` 更新导致已有 `hard` 红线消失（id 不在新列表中），返回 `409 HARD_REDLINE_DELETE_REQUIRES_CONFIRM`：

```json
{
  "error_code": "HARD_REDLINE_DELETE_REQUIRES_CONFIRM",
  "message": "Removing hard redlines requires explicit confirmation.",
  "detail": {
    "removing_hard_redlines": [
      { "id": "rl-001", "description": "不能出现任何形式的'爱情能解决一切'" }
    ],
    "confirm_token": "confirm_rl_delete_xk9z..."
  },
  "request_id": "..."
}
```

客户端需在请求体中附带 `confirm_token` 才能执行删除：

```json
{
  "do_not_betray": [ "..." ],
  "confirm_token": "confirm_rl_delete_xk9z..."
}
```

**响应体（200）**：完整更新后的 AuthorIntent 对象，附加：

```json
{
  "...": "...",
  "version": 4,
  "changed_fields": ["do_not_betray"],
  "updated_at": "2026-06-19T12:00:00Z"
}
```

服务端自动创建 `AuthorIntentSnapshot`（历史快照）。

---

#### `GET /api/v1/works/{work_id}/author-intent/history` — 获取北极星历史版本列表

```
GET /api/v1/works/{work_id}/author-intent/history?limit=20&order=desc
```

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "019018ab-intent-snap-0003",
      "intent_id": "019018ab-intent-0001",
      "version": 3,
      "changed_fields": ["do_not_betray", "reader_feeling"],
      "change_reason": "第50章后感觉需要强化",
      "created_at": "2026-06-19T12:00:00Z"
    }
  ],
  "pagination": { "cursor": null, "has_more": false, "total_count": 3 }
}
```

---

#### `GET /api/v1/works/{work_id}/author-intent/history/{version}` — 获取特定版本北极星快照

**响应体（200）**：完整的历史 AuthorIntent 快照（`snapshot` jsonb 展开为完整字段）。

---

### 3.10 资源端点：works

**资源路径**：`/api/v1/works`

对应 00 §4.2 实体：`Work`（`id, title, premise, genre, structure_type, created_at, updated_at`）

> 注意：Work 的「主题锚」已废弃（旧版 `theme_anchor` 字段），由 AuthorIntent 实体（1:1 绑定 work）承担。创建 Work 后应引导作者通过 `/author-intent` 端点填写北极星。

---

#### `POST /api/v1/works` — 创建作品

**请求体**：

```json
{
  "title": "凡人修仙传 2.0",
  "premise": "平民少年韩立，在乱世中以谨慎和坚韧走上修仙之路，最终成为超越时代的存在。",
  "genre": "xuanhuan",
  "structure_type": "three_act"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | string | 是 | 作品标题，max 200 字符 |
| `premise` | string | 是 | 核心前提，max 1000 字符 |
| `genre` | string | 是 | 枚举：`xuanhuan` / `wuxia` / `scifi` / `fantasy` / `romance` / `other` |
| `structure_type` | string | 否 | 枚举：`three_act` / `save_the_cat` / `seven_point` / `kishotenketsu`，默认 `three_act` |

**响应体（201）**：

```json
{
  "id": "019018ab-0000-7000-8000-000000000001",
  "title": "凡人修仙传 2.0",
  "premise": "平民少年韩立……",
  "genre": "xuanhuan",
  "structure_type": "three_act",
  "author_intent_initialized": false,
  "created_at": "2026-06-19T10:00:00Z",
  "updated_at": "2026-06-19T10:00:00Z"
}
```

`author_intent_initialized`：是否已创建 AuthorIntent（北极星）。`false` 时前端应展示书写向导引导。

---

#### `GET /api/v1/works` — 列出所有作品

```
GET /api/v1/works?limit=20&order=desc
```

**响应体（200）**：列表包装结构，data 为 Work 摘要列表（不含 premise 全文，加 `fields=premise` 可显式请求）。

---

#### `GET /api/v1/works/{work_id}` — 获取单部作品

**响应体（200）**：完整 Work 对象，附加 `author_intent_initialized`、`total_chapters`、`total_word_count` 统计字段。

---

#### `PATCH /api/v1/works/{work_id}` — 更新作品元数据

**请求体**（只传需要更新的字段）：

```json
{
  "title": "凡人修仙传（新版）",
  "genre": "xuanhuan"
}
```

**响应体（200）**：完整更新后的 Work 对象。

---

#### `DELETE /api/v1/works/{work_id}` — 软删除作品

级联软删除该作品下所有 volumes、chapters、segments、imaginations、feedback-notes 等。**响应（204）**：无响应体。

---

### 3.11 资源端点：volumes

**资源路径**：`/api/v1/works/{work_id}/volumes`

对应 00 §4.2 实体：`Volume`（`id, work_id, seq, title, arc_goal, structure_beats, status`）

`status` 枚举：`draft` / `generating` / `reviewing` / `done`

---

#### `POST /api/v1/works/{work_id}/volumes` — 创建卷

**请求体**：

```json
{
  "seq": 1,
  "title": "第一卷 · 黄枫谷",
  "arc_goal": "韩立从平民弟子成长为炼气期修士，完成第一次真正意义上的生死考验。",
  "structure_beats": [
    { "beat_type": "setup", "description": "入黄枫谷，平民身份，谨慎观察" },
    { "beat_type": "inciting_incident", "description": "意外获得七彩云丹秘方" },
    { "beat_type": "midpoint", "description": "韩立独自击败师兄弟，暗藏实力暴露" },
    { "beat_type": "climax", "description": "黄枫谷危机，韩立舍命保护核心秘密" },
    { "beat_type": "resolution", "description": "离开黄枫谷，踏上未知旅程" }
  ]
}
```

**响应体（201）**：完整 Volume 对象，`status` 初始为 `draft`。

---

#### `GET /api/v1/works/{work_id}/volumes` — 列出卷

**响应体（200）**：列表包装结构。`structure_beats` 字段默认不返回（加 `fields=structure_beats` 显式请求）。

---

#### `GET /api/v1/works/{work_id}/volumes/{volume_id}` — 获取单卷

**响应体（200）**：完整 Volume 对象（含 `structure_beats`）。

---

#### `PATCH /api/v1/works/{work_id}/volumes/{volume_id}` — 更新卷

**响应体（200）**：完整更新后的 Volume 对象。

---

#### `DELETE /api/v1/works/{work_id}/volumes/{volume_id}` — 软删除卷

级联软删除卷下所有 chapters。**响应（204）**。

---

### 3.12 资源端点：chapters

**资源路径**：`/api/v1/works/{work_id}/chapters` 及 `/api/v1/works/{work_id}/volumes/{volume_id}/chapters`

对应 00 §4.2 实体：`Chapter`（`id, volume_id, seq, title, outline, beat_targets, hook_text, hook_strength, word_count, status`）

`status` 枚举：`draft` → `generating` → `reviewing` → `done`（单向，逆向需 `force: true`）

---

#### `POST /api/v1/works/{work_id}/volumes/{volume_id}/chapters` — 创建章

**请求体**：

```json
{
  "seq": 1,
  "title": "第一章 · 入谷",
  "outline": {
    "events": ["韩立抵达黄枫谷", "初见七层弟子等级制度", "发现云房分配规则"],
    "pov_character": "韩立",
    "estimated_word_count": 3000
  },
  "beat_targets": ["setup_ordinary_world"],
  "hook_text": "黄枫谷的云雾里，有什么东西一直在等着他。",
  "hook_strength": null
}
```

**响应体（201）**：完整 Chapter 对象，`word_count` 初始为 0。

---

#### `GET /api/v1/works/{work_id}/volumes/{volume_id}/chapters` — 列出章

```
GET /api/v1/works/{work_id}/volumes/{volume_id}/chapters?status=draft&limit=50&order=asc&fields=id,seq,title,status,word_count,hook_strength
```

**响应体（200）**：列表包装结构，`outline` 字段默认不返回。

---

#### `GET /api/v1/works/{work_id}/chapters/{chapter_id}` — 获取单章

**响应体（200）**：完整 Chapter 对象，附加 `segments_count`。正文通过 Segment 端点分页获取，不在此处返回全文。

---

#### `PATCH /api/v1/works/{work_id}/chapters/{chapter_id}` — 更新章元数据

**业务约束**：
- `status` 只能按状态机流转；逆向流转需附 `"force": true`。
- 对 `status=done` 的章节修改 `outline` 会自动将 `status` 重置为 `draft`，响应中携带 `"status_reset": true`。

**响应体（200）**：完整更新后的 Chapter 对象。

---

#### `DELETE /api/v1/works/{work_id}/chapters/{chapter_id}` — 软删除章

级联软删除章下所有 Segments。**响应（204）**。

---

### 3.13 资源端点：segments

**资源路径**：`/api/v1/works/{work_id}/chapters/{chapter_id}/segments`

对应 00 §4.2 实体：`Segment`（`id, chapter_id, seq, text, embedding, created_by`）

`created_by` 枚举：`ai` / `human`

---

#### `GET /api/v1/works/{work_id}/chapters/{chapter_id}/segments` — 获取章正文段落

```
GET /api/v1/works/{work_id}/chapters/{chapter_id}/segments?order=asc&limit=100
```

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "019018ab-seg-001",
      "chapter_id": "019018ab-chap-001",
      "seq": 1,
      "text": "黄枫谷的迎客峰，是谷中地位最低的弟子居住之地……",
      "created_by": "ai",
      "created_at": "2026-06-19T11:30:00Z",
      "updated_at": "2026-06-19T11:30:00Z"
    }
  ],
  "pagination": { "cursor": "eyJzZXEiOjF9", "has_more": true, "total_count": 8 }
}
```

`embedding` 字段默认不返回。

---

#### `POST /api/v1/works/{work_id}/chapters/{chapter_id}/segments` — 追加段落

**请求体**：`{ "seq": 9, "text": "...", "created_by": "human" }`

**响应体（201）**：完整 Segment 对象，`embedding` 异步生成（初始 null），`embedding_status: "pending"`。

---

#### `PATCH /api/v1/works/{work_id}/chapters/{chapter_id}/segments/{segment_id}` — 编辑段落文本

**请求体**：`{ "text": "修改后的段落文本" }`

**响应体（200）**：更新后的 Segment，`embedding_status: "pending"`（向量重建异步进行）。

> 提醒：Segment 文本修改是修订回流的触发点之一，编辑完成后前端应提示用户是否提交修订记录（见 §3.28）。

---

#### `DELETE /api/v1/works/{work_id}/chapters/{chapter_id}/segments/{segment_id}` — 软删除段落

**响应（204）**。

---

### 3.14 资源端点：characters

**资源路径**：`/api/v1/works/{work_id}/characters`

对应 00 §4.3 实体：`Character`（`id, work_id, name, traits, motivation, voice_profile, relations`）及 `CharState`（`id, character_id, chapter_id, state_desc, change_type`）

---

#### `POST /api/v1/works/{work_id}/characters` — 创建角色

**请求体**：

```json
{
  "name": "韩立",
  "traits": {
    "personality": ["谨慎", "坚韧", "不善表达", "极度自律"],
    "appearance": "普通相貌，左手有旧疤",
    "age": 17,
    "background": "大燕国张家堡平民，家中最聪明的孩子"
  },
  "motivation": "通过修仙脱离贫困，保护家人，弄清自身的特殊体质",
  "voice_profile": {
    "speech_style": "简短有力，少用形容词，不轻易表态",
    "catchphrases": ["无妨", "再说吧"],
    "ooc_markers": ["雍容", "温柔地笑", "感慨万千", "热泪盈眶"]
  },
  "relations": {}
}
```

**响应体（201）**：完整 Character 对象。

---

#### `GET /api/v1/works/{work_id}/characters` — 列出角色

**响应体（200）**：列表包装，`voice_profile` 和 `relations` 默认不返回（加 `fields=voice_profile` 显式请求）。

---

#### `GET /api/v1/works/{work_id}/characters/{character_id}` — 获取单角色

**响应体（200）**：完整 Character 对象（含 `voice_profile`、`relations`）。

---

#### `PATCH /api/v1/works/{work_id}/characters/{character_id}` — 更新角色

`traits`、`voice_profile`、`relations` 字段采用 JSON Merge Patch 语义（RFC 7396）——传入的 object 与现有内容深度合并。

**响应体（200）**：完整更新后的 Character 对象，附加：

```json
{
  "...": "...",
  "backflow_required": true,
  "affected_chapters_estimate": 45
}
```

`backflow_required=true`：若修改了 `traits` 或 `voice_profile`，提示前端需提交修订回流。

---

#### `DELETE /api/v1/works/{work_id}/characters/{character_id}` — 软删除角色

**响应（204）**。

---

#### `GET /api/v1/works/{work_id}/characters/{character_id}/states` — 获取角色状态时间线

```
GET /api/v1/works/{work_id}/characters/{character_id}/states?order=asc&limit=50
```

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "019018ab-cs-001",
      "character_id": "...",
      "chapter_id": "...",
      "chapter_seq": 12,
      "state_desc": "习得七层楼阁拳法第三层，可感知三十米内气息",
      "change_type": "ability",
      "created_at": "2026-06-19T12:00:00Z"
    }
  ],
  "pagination": { "..." : "..." }
}
```

`change_type` 枚举：`ability` / `relation` / `knowledge` / `psychological` / `physical`

---

#### `POST /api/v1/works/{work_id}/characters/{character_id}/states` — 手动记录角色状态变化

**请求体**：

```json
{
  "chapter_id": "019018ab-chap-012",
  "state_desc": "与厉飞鱼决裂，关系从表面友好转为潜在对立",
  "change_type": "relation"
}
```

**响应体（201）**：完整 CharState 对象。

---

### 3.15 资源端点：setting-items

**资源路径**：`/api/v1/works/{work_id}/setting-items`

对应 00 §4.3 实体：`SettingItem`（`id, work_id, type, name, content, first_chapter_id, embedding`）

`type` 枚举：`rule` / `item` / `place` / `faction` / `term`

---

#### `POST /api/v1/works/{work_id}/setting-items` — 创建设定项

**请求体**：

```json
{
  "type": "rule",
  "name": "修仙等级体系",
  "content": {
    "description": "炼气→筑基→结丹→元婴→化神→炼虚→合体→大乘→渡劫→真仙",
    "details": {
      "炼气期": "共13层，需以灵石或灵药辅助，可在数十年内完成",
      "筑基期": "需特定筑基丹，成功率不足十分之一"
    },
    "constraints": ["无灵根者无法修炼", "修为可因受伤或特殊原因下降"]
  },
  "first_chapter_id": "019018ab-chap-001"
}
```

**响应体（201）**：完整 SettingItem 对象，`embedding` 异步生成。

---

#### `GET /api/v1/works/{work_id}/setting-items` — 列出设定项

```
GET /api/v1/works/{work_id}/setting-items?type=rule&name__contains=修仙&limit=50
```

**响应体（200）**：列表包装，`content` 默认返回（完整 jsonb）；`embedding` 默认不返回。

---

#### `GET /api/v1/works/{work_id}/setting-items/{item_id}` — 获取单设定项

**响应体（200）**：完整 SettingItem 对象。

---

#### `PATCH /api/v1/works/{work_id}/setting-items/{item_id}` — 更新设定项

`content` 字段整体替换（不深度合并）。

**响应体（200）**：完整更新后的 SettingItem 对象，附加 `embedding_status: "pending"`、`backflow_required: true`。

---

#### `DELETE /api/v1/works/{work_id}/setting-items/{item_id}` — 软删除设定项

**响应（204）**。

---

### 3.16 资源端点：entity-relations

**资源路径**：`/api/v1/works/{work_id}/entity-relations`

对应 00 §4.3 实体：`EntityRelation`（`id, work_id, src_entity, dst_entity, relation, valid_from_chapter, valid_to_chapter`）

---

#### `POST /api/v1/works/{work_id}/entity-relations` — 创建实体关系

**请求体**：

```json
{
  "src_entity": "韩立",
  "dst_entity": "厉飞鱼",
  "relation": "surface_ally",
  "valid_from_chapter_id": "019018ab-chap-003",
  "valid_to_chapter_id": null
}
```

**响应体（201）**：完整 EntityRelation 对象。

---

#### `GET /api/v1/works/{work_id}/entity-relations` — 列出实体关系

```
GET /api/v1/works/{work_id}/entity-relations?src_entity=韩立&limit=50
```

过滤参数：`src_entity`、`dst_entity`、`relation`。

**响应体（200）**：列表包装结构。

---

#### `PATCH /api/v1/works/{work_id}/entity-relations/{relation_id}` — 更新关系

**请求体**：`{ "valid_to_chapter_id": "...", "relation": "enemy" }`

**响应体（200）**：更新后的 EntityRelation 对象。

---

#### `DELETE /api/v1/works/{work_id}/entity-relations/{relation_id}` — 软删除关系

**响应（204）**。

---

### 3.17 资源端点：timeline-events

**资源路径**：`/api/v1/works/{work_id}/timeline-events`

对应 00 §4.3 实体：`TimelineEvent`（`id, work_id, chapter_id, abs_time, rel_order, description, entity_refs, embedding`）

---

#### `POST /api/v1/works/{work_id}/timeline-events` — 创建时间线事件

通常由 ExtractAgent 自动创建；此端点用于人工补录。

**请求体**：

```json
{
  "chapter_id": "019018ab-chap-001",
  "abs_time": "大燕历1023年春",
  "rel_order": 1001,
  "description": "韩立抵达黄枫谷，正式成为七层弟子，开始修仙生涯",
  "entity_refs": {
    "characters": ["韩立"],
    "places": ["黄枫谷", "迎客峰"],
    "items": []
  }
}
```

**响应体（201）**：完整 TimelineEvent 对象，`embedding` 异步生成。

---

#### `GET /api/v1/works/{work_id}/timeline-events` — 列出时间线事件

```
GET /api/v1/works/{work_id}/timeline-events?chapter_id=...&order=asc&limit=100
```

过滤：`chapter_id`、`entity_refs__contains=韩立`（JSON 包含过滤）。

**响应体（200）**：列表包装结构。

---

#### `PATCH /api/v1/works/{work_id}/timeline-events/{event_id}` — 更新事件

**响应体（200）**：更新后对象，`embedding_status: "pending"`。

---

#### `DELETE /api/v1/works/{work_id}/timeline-events/{event_id}` — 软删除事件

**响应（204）**。

---

### 3.18 资源端点：foreshadows

**资源路径**：`/api/v1/works/{work_id}/foreshadows`

对应 00 §4.3 实体：`Foreshadow`（`id, work_id, summary, foreshadow_chapter_id, trigger_chapter_id, payoff_chapter_id, state, payload`）

`state` 枚举（F-T-P 状态机）：`planted` → `triggered` → `paid` 或 `planted`/`triggered` → `abandoned`

---

#### `POST /api/v1/works/{work_id}/foreshadows` — 手动创建伏笔

**请求体**：

```json
{
  "summary": "韩立左手旧疤的来历——暗示他幼年曾与某种奇异力量接触",
  "foreshadow_chapter_id": "019018ab-chap-001",
  "trigger_chapter_id": null,
  "payoff_chapter_id": null,
  "state": "planted",
  "payload": {
    "hint_text": "他习惯性地摩挲左手的旧疤，那是七岁那年落下的，至今不知来历。",
    "planned_payoff_volume": 3,
    "payoff_note": "第三卷揭示：幼年时曾被某功法短暂灌入体内，留下疤痕"
  }
}
```

**响应体（201）**：完整 Foreshadow 对象。

---

#### `GET /api/v1/works/{work_id}/foreshadows` — 列出伏笔池

```
GET /api/v1/works/{work_id}/foreshadows?state=planted&state=triggered&limit=50
```

**响应体（200）**：列表包装结构。

---

#### `PATCH /api/v1/works/{work_id}/foreshadows/{foreshadow_id}` — 推进伏笔状态

**请求体**：

```json
{
  "state": "triggered",
  "trigger_chapter_id": "019018ab-chap-078"
}
```

**业务约束**：非法状态转移返回 `422 FORESHADOW_STATE_INVALID`。

**响应体（200）**：完整更新后的 Foreshadow 对象。

---

### 3.23 异步生成：任务提交与进度轮询

> 【设计决策】所有需要调用 LLM 的操作均走异步任务模式：POST 提交任务 → 获得 `task_id` → GET 轮询 或 SSE 订阅进度。绝不阻塞 HTTP 连接等待 LLM 返回。

#### 3.23.1 任务资源模型

`GenerationTask` 字段：

```json
{
  "task_id": "019018ab-task-0001",
  "task_type": "generate_chapter",
  "work_id": "019018ab-...",
  "target_id": "019018ab-chap-014",
  "status": "running",
  "progress": {
    "stage": "writing",
    "stage_index": 3,
    "total_stages": 6,
    "message": "WritingAgent 正在生成正文（已写 1240 字，目标 3000 字）",
    "tokens_used": 8500,
    "tokens_budget": 12000
  },
  "result": null,
  "error": null,
  "idempotency_key": "gen-chap-014-attempt1",
  "created_at": "2026-06-19T11:00:00Z",
  "started_at": "2026-06-19T11:00:02Z",
  "completed_at": null,
  "estimated_seconds_remaining": 45
}
```

`status` 枚举：`queued` / `running` / `completed` / `failed` / `cancelled`

`task_type` 枚举：`generate_volume_outline` / `generate_chapter_outline` / `generate_chapter` / `generate_optionset` / `feedback_rewrite` / `consistency_check` / `foreshadow_scan` / `evaluate_chapter` / `evaluate_volume` / `rebuild_taste_model` / `memory_refresh`

---

#### `POST /api/v1/tasks/generate-volume-outline` — 触发卷大纲生成

**请求体**：

```json
{
  "work_id": "019018ab-...",
  "volume_seq": 2,
  "idempotency_key": "gen-vol-outline-work001-vol2-attempt1",
  "options": {
    "target_chapter_count": 20,
    "prev_volume_context": true,
    "inject_imaginations": true
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `work_id` | string | 是 | 目标作品 ID |
| `volume_seq` | integer | 是 | 新卷序号 |
| `idempotency_key` | string | 是 | 幂等键 |
| `options.target_chapter_count` | integer | 否 | 目标章数，默认 20 |
| `options.prev_volume_context` | boolean | 否 | 是否注入前卷记忆摘要，默认 true |
| `options.inject_imaginations` | boolean | 否 | 是否注入已排期到本卷的 Imagination，默认 true |

**响应体（202）**：

```json
{
  "task_id": "019018ab-task-voloutline-001",
  "task_type": "generate_volume_outline",
  "status": "queued",
  "work_id": "019018ab-...",
  "idempotency_key": "gen-vol-outline-work001-vol2-attempt1",
  "created_at": "2026-06-19T11:00:00Z"
}
```

**幂等冲突（409）**：

```json
{
  "error_code": "TASK_ALREADY_SUBMITTED",
  "message": "A task with this idempotency_key already exists.",
  "detail": {
    "existing_task_id": "019018ab-task-voloutline-001",
    "existing_task_status": "completed"
  }
}
```

---

#### `POST /api/v1/tasks/generate-chapter-outline` — 触发章大纲生成

**请求体**：

```json
{
  "work_id": "019018ab-...",
  "volume_id": "019018ab-vol2-...",
  "chapter_seq": 5,
  "idempotency_key": "gen-chap-outline-vol2-chap5-attempt1",
  "options": {
    "chapter_id": null,
    "use_existing_outline": false,
    "inject_imaginations": true
  }
}
```

**响应体（202）**：同上结构，`task_type: "generate_chapter_outline"`。

---

#### `POST /api/v1/tasks/generate-chapter` — 触发写一章（核心端点）

这是 **Scribe 最重要的异步端点**，触发编排引擎全流程：OutlineAgent（若需）→ PlanningAgent → WritingAgent（注入 AuthorIntent + Imagination + TasteModel）→ ReviewAgent → ExtractAgent → updateMemory → evaluate → 偏离检测。

**请求体**：

```json
{
  "work_id": "019018ab-...",
  "chapter_id": "019018ab-chap-014",
  "idempotency_key": "gen-chap-014-attempt1",
  "options": {
    "max_rewrite": 3,
    "consistency_severity_threshold": "high",
    "context_token_budget": 12000,
    "skip_outline_generation": true,
    "force_restart": false,
    "inject_imaginations": true,
    "inject_author_intent": true,
    "inject_taste_model": true
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `work_id` | string | 是 | 作品 ID |
| `chapter_id` | string | 是 | 目标章节 ID（需已存在，status 为 draft） |
| `idempotency_key` | string | 是 | 幂等键（建议：`gen-chap-{chapter_id}-attempt{n}`） |
| `options.max_rewrite` | integer | 否 | 写作→审校回炉最大次数，默认 3 |
| `options.consistency_severity_threshold` | string | 否 | 审校强制修复最低级别，默认 `high` |
| `options.context_token_budget` | integer | 否 | 上下文 token 预算，默认 12000 |
| `options.inject_imaginations` | boolean | 否 | 是否注入活跃 Imagination，默认 true |
| `options.inject_author_intent` | boolean | 否 | 是否注入 AuthorIntent，默认 true |
| `options.inject_taste_model` | boolean | 否 | 是否注入 TasteModel，默认 true |
| `options.force_restart` | boolean | 否 | 强制重启（忽略已有检查点），默认 false |

**业务约束**：章节 `status` 必须为 `draft`，否则返回 `409 CHAPTER_STATUS_CONFLICT`。

**响应体（202）**：

```json
{
  "task_id": "019018ab-task-genchap-014",
  "task_type": "generate_chapter",
  "status": "queued",
  "work_id": "019018ab-...",
  "target_id": "019018ab-chap-014",
  "idempotency_key": "gen-chap-014-attempt1",
  "created_at": "2026-06-19T11:00:00Z",
  "estimated_seconds": 90
}
```

---

#### `GET /api/v1/tasks/{task_id}` — 轮询任务状态

**运行中（status=running）响应体（200）**：

```json
{
  "task_id": "019018ab-task-genchap-014",
  "task_type": "generate_chapter",
  "status": "running",
  "progress": {
    "stage": "writing",
    "stage_index": 3,
    "total_stages": 6,
    "message": "WritingAgent 正在生成正文（已写 1240 字，目标 3000 字）",
    "tokens_used": 8500,
    "tokens_budget": 12000
  },
  "result": null,
  "error": null,
  "started_at": "2026-06-19T11:00:02Z",
  "estimated_seconds_remaining": 45
}
```

**完成时（status=completed）**：

```json
{
  "task_id": "019018ab-task-genchap-014",
  "status": "completed",
  "result": {
    "chapter_id": "019018ab-chap-014",
    "word_count": 3012,
    "hook_strength": 0.84,
    "snapshot_id": "019018ab-snap-0023",
    "consistency_flags_count": 1,
    "consistency_flags_high_count": 0,
    "imaginations_used": ["019018ab-imag-0003"],
    "deviation_report": {
      "has_hard_violations": false,
      "arc_deviation_score": 0.08,
      "arc_deviation_note": "本章情感走向与北极星高度一致"
    },
    "quality_score": 0.81
  },
  "completed_at": "2026-06-19T11:01:35Z"
}
```

**失败时（status=failed）**：

```json
{
  "task_id": "019018ab-task-genchap-014",
  "status": "failed",
  "error": {
    "error_code": "LLM_PROVIDER_UNAVAILABLE",
    "message": "WritingAgent 调用 LLM Provider 超时（已重试 3 次）",
    "failed_stage": "writing",
    "retry_count": 3,
    "recoverable": true,
    "resume_hint": "任务可使用相同 chapter_id 重新提交（force_restart=false 将从 writing 阶段恢复）"
  },
  "completed_at": "2026-06-19T11:02:00Z"
}
```

`recoverable: true` 表示编排引擎保留了检查点，新任务提交时（`force_restart: false`）会从断点恢复。

---

#### `POST /api/v1/tasks/{task_id}/cancel` — 取消任务

**响应体（200）**：`{ "task_id": "...", "status": "cancelled", "cancelled_at": "..." }`

仅 `queued` / `running` 状态任务可取消；`completed` / `failed` 任务返回 `409 Conflict`。

---

#### `GET /api/v1/works/{work_id}/tasks` — 列出作品下的任务

```
GET /api/v1/works/{work_id}/tasks?status=running&status=queued&task_type=generate_chapter&limit=20
```

**响应体（200）**：列表包装结构，data 为任务摘要列表（不含 `result` 和 `progress.tokens_*`）。

---

### 3.24 SSE 进度订阅

> 【设计决策】除轮询外，提供 SSE（Server-Sent Events）endpoint 供前端实时订阅任务进度及回路关键事件。SSE 比 WebSocket 更简单（单向推送），对 HTTP/2 友好，前端浏览器原生 `EventSource` API 支持，无需额外库。

#### `GET /api/v1/tasks/{task_id}/stream` — 章节生成 SSE 进度流

**请求头**：

```http
GET /api/v1/tasks/019018ab-task-genchap-014/stream HTTP/1.1
Accept: text/event-stream
Authorization: Bearer <token>
Cache-Control: no-cache
```

**事件流格式**：

```
event: stage_started
data: {"task_id":"...","stage":"outline","stage_index":1,"total_stages":6,"message":"OutlineAgent 开始细化章节大纲","timestamp":"2026-06-19T11:00:02Z"}

event: stage_completed
data: {"task_id":"...","stage":"outline","stage_index":1,"output_preview":{"events":["韩立目睹背叛","茶馆无声对峙","章尾留白"]},"timestamp":"2026-06-19T11:00:08Z"}

event: imagination_injected
data: {"task_id":"...","stage":"writing","imagination_id":"019018ab-imag-0003","implementation_hint":"写茶馆场景，克制情绪，全用环境和动作","timestamp":"2026-06-19T11:00:10Z"}

event: stage_started
data: {"task_id":"...","stage":"writing","stage_index":3,"message":"WritingAgent 开始生成正文（注入 AuthorIntent + TasteModel）","timestamp":"2026-06-19T11:00:16Z"}

event: writing_progress
data: {"task_id":"...","stage":"writing","words_written":820,"words_target":3000,"timestamp":"2026-06-19T11:00:30Z"}

event: writing_progress
data: {"task_id":"...","stage":"writing","words_written":1900,"words_target":3000,"timestamp":"2026-06-19T11:00:50Z"}

event: stage_completed
data: {"task_id":"...","stage":"writing","message":"正文生成完成，共 3012 字","timestamp":"2026-06-19T11:01:05Z"}

event: review_result
data: {"task_id":"...","stage":"reviewing","passed":false,"flags_count":2,"flags_high_count":1,"rewrite_triggered":true,"rewrite_attempt":2,"timestamp":"2026-06-19T11:01:20Z"}

event: stage_completed
data: {"task_id":"...","stage":"reviewing","message":"审校通过（第 2 次），1 个 low 级标记已记录","timestamp":"2026-06-19T11:01:30Z"}

event: deviation_checked
data: {"task_id":"...","has_hard_violations":false,"arc_deviation_score":0.08,"note":"本章情感走向与北极星高度一致","timestamp":"2026-06-19T11:01:38Z"}

event: imagination_used
data: {"task_id":"...","imagination_id":"019018ab-imag-0003","resulted_in_chapter":"019018ab-chap-014","timestamp":"2026-06-19T11:01:40Z"}

event: task_completed
data: {"task_id":"...","status":"completed","word_count":3012,"hook_strength":0.84,"snapshot_id":"...","quality_score":0.81,"timestamp":"2026-06-19T11:01:45Z"}
```

**事件类型说明**：

| event 类型 | 触发时机 |
|---|---|
| `stage_started` | 每个 Agent 阶段开始 |
| `stage_completed` | 每个 Agent 阶段正常完成 |
| `writing_progress` | WritingAgent 流式输出期间，每约 500 字发一次 |
| `imagination_injected` | Imagination 被注入写作 Prompt 时 |
| `imagination_used` | Imagination 被标记为 used（写作完成后） |
| `review_result` | ReviewAgent 审校完成，含通过/回炉信息 |
| `deviation_checked` | 偏离检测完成，含是否触犯红线 |
| `optionset_created` | OptionSet 生成完成（生成方案任务） |
| `rewrite_complete` | FeedbackNote 重做完成，含新 snapshot_id |
| `task_completed` | 任务完成，含最终 result |
| `task_failed` | 任务失败，含错误信息 |
| `keepalive` | 每 15 秒发一次（防连接超时） |

**断线重连**：客户端携带 `Last-Event-ID` 请求头，服务端从该事件之后继续推送（服务端保留最近 100 条事件 5 分钟）。

---

#### `GET /api/v1/works/{work_id}/stream` — 作品级事件流（全局订阅）

前端可订阅整个作品的所有关键事件（无需知道具体 task_id），用于侧边栏实时通知。

```http
GET /api/v1/works/019018ab-.../stream HTTP/1.1
Accept: text/event-stream
Authorization: Bearer <token>
```

推送所有与该作品相关的回路事件：`imagination.structured`、`optionset.created`、`feedback.parsed`、`rewrite_complete`、`intent.deviation_detected` 等。

---

### 3.25 服务型端点：上下文拼装与语义检索

#### `GET /api/v1/works/{work_id}/chapters/{chapter_id}/context` — 查看章节上下文包

前端"AI 面板"查询该章生成时使用（或将要使用）的上下文包内容，用于可解释性展示。此端点只读，不触发任何写操作。

```
GET /api/v1/works/{work_id}/chapters/{chapter_id}/context?token_budget=12000
```

**响应体（200）**：

```json
{
  "chapter_id": "019018ab-chap-014",
  "token_budget": 12000,
  "tokens_used": 9847,
  "context_bundle": {
    "author_intent_summary": {
      "reader_feeling": "一种温热的孤独感……",
      "hard_redlines": ["不能出现任何形式的'爱情能解决一切'"],
      "tokens": 280
    },
    "active_imaginations": [
      {
        "imagination_id": "019018ab-imag-0003",
        "type": "scene_wish",
        "implementation_hint": "写茶馆场景，克制情绪，全用环境和动作",
        "tokens": 85
      }
    ],
    "taste_model_digest": {
      "negative_list_preview": ["陈词滥调", "AI腔模板", "大段心理独白"],
      "preferred_style": "克制情感，短句节奏",
      "tokens": 120
    },
    "global_memory": {
      "summary_text": "主角韩立自黄枫谷出走后……",
      "tokens": 320
    },
    "recent_chapter_summaries": [
      { "chapter_seq": 12, "summary": "...", "tokens": 180 },
      { "chapter_seq": 13, "summary": "...", "tokens": 175 }
    ],
    "relevant_setting_items": [
      {
        "setting_item_id": "...",
        "name": "修仙等级体系",
        "type": "rule",
        "relevance_score": 0.91,
        "tokens": 210
      }
    ],
    "relevant_characters": [
      { "character_id": "...", "name": "韩立", "relevance_score": 1.0, "tokens": 430 }
    ],
    "active_foreshadows": [
      { "foreshadow_id": "...", "summary": "韩立左手旧疤的来历", "state": "planted", "tokens": 85 }
    ]
  },
  "assembled_at": "2026-06-19T11:00:00Z",
  "cached": true
}
```

---

#### `POST /api/v1/works/{work_id}/search` — 语义检索设定/记忆/想象/事件

前端"设定圣经"搜索栏、"想象库"搜索、"AI 面板"手动查询用。

**请求体**：

```json
{
  "query": "茶馆 张力 无声对峙",
  "types": ["setting_items", "imaginations", "memory", "timeline_events"],
  "limit": 10,
  "min_score": 0.7
}
```

`types` 可选值：`setting_items` / `imaginations` / `memory` / `timeline_events` / `characters` / `foreshadows`

**响应体（200）**：

```json
{
  "results": [
    {
      "type": "imagination",
      "id": "019018ab-imag-0003",
      "raw_text": "我想要一场雨夜的背叛，两人在茶馆相遇，没有正面冲突但全是张力",
      "excerpt": "雨夜茶馆，两人无声对峙，张力全靠细节传递",
      "score": 0.95,
      "status": "scheduled"
    },
    {
      "type": "setting_item",
      "id": "...",
      "name": "天机城地理布局",
      "excerpt": "天机城分内外两区，外区有数十家茶楼……",
      "score": 0.78
    }
  ],
  "query": "茶馆 张力 无声对峙",
  "total": 2
}
```

---

### 3.26 服务型端点：一致性校验与伏笔扫描

#### `POST /api/v1/works/{work_id}/chapters/{chapter_id}/check` — 触发一致性校验（异步）

通常由 ReviewAgent 自动调用；此端点供前端手动触发（如人工修改章节后）。

**请求体**：

```json
{
  "idempotency_key": "check-chap014-20260619",
  "options": {
    "severity_threshold": "medium",
    "error_classes": ["character_ooc", "timeline_logic", "world_rule_violation"]
  }
}
```

**响应体（202）**：`{ "task_id": "...", "task_type": "consistency_check", "status": "queued", "chapter_id": "..." }`

校验完成后，新产生的 ConsistencyFlag 可通过 §3.19 端点查询。

---

#### `POST /api/v1/works/{work_id}/chapters/{chapter_id}/scan-foreshadows` — 触发伏笔扫描（异步）

**请求体**：`{ "idempotency_key": "scan-foreshadow-chap014-20260619" }`

**响应体（202）**：`{ "task_id": "...", "task_type": "foreshadow_scan", "status": "queued", "chapter_id": "..." }`

扫描完成后，新增或状态更新的 Foreshadow 可通过 §3.18 端点查询。

---

### 3.27 服务型端点：质量评估

#### `POST /api/v1/works/{work_id}/chapters/{chapter_id}/evaluate` — 触发章节质量评估（异步）

**请求体**：

```json
{
  "idempotency_key": "eval-chap014-20260619",
  "options": {
    "metrics": ["coherence", "hook_strength", "pacing", "ooc_score", "intent_alignment"]
  }
}
```

`metrics` 新增 `intent_alignment`：与 AuthorIntent 的对齐分数（利用偏离检测结果）。

**响应体（202）**：`{ "task_id": "...", "task_type": "evaluate_chapter", "status": "queued" }`

---

#### `GET /api/v1/works/{work_id}/chapters/{chapter_id}/quality-report` — 获取最新质量报告

**响应体（200）**：

```json
{
  "chapter_id": "019018ab-chap-014",
  "evaluated_at": "2026-06-19T12:00:00Z",
  "scores": {
    "coherence": 0.82,
    "hook_strength": 0.84,
    "pacing": 0.76,
    "ooc_score": 0.96,
    "intent_alignment": 0.91,
    "overall": 0.82
  },
  "flags": [
    { "metric": "pacing", "severity": "low", "detail": "第 4–5 段节奏偏缓，建议压缩或增加悬念密度" }
  ],
  "intent_report": {
    "has_hard_violations": false,
    "arc_deviation_score": 0.08,
    "arc_deviation_note": "本章情感走向与北极星高度一致"
  },
  "benchmark": {
    "hook_strength_avg_work": 0.77,
    "hook_strength_avg_volume": 0.80
  }
}
```

---

#### `POST /api/v1/works/{work_id}/volumes/{volume_id}/evaluate` — 触发卷级质量评估（异步）

**响应体（202）**：同章节评估。

---

#### `GET /api/v1/works/{work_id}/volumes/{volume_id}/quality-report` — 获取卷级质量报告

**响应体（200）**：

```json
{
  "volume_id": "...",
  "evaluated_at": "2026-06-19T13:00:00Z",
  "chapters_evaluated": 20,
  "aggregate_scores": {
    "avg_coherence": 0.81,
    "avg_hook_strength": 0.79,
    "avg_pacing": 0.74,
    "avg_intent_alignment": 0.88,
    "theme_drift_score": 0.89,
    "read_through_estimate": 0.72
  },
  "low_performing_chapters": [
    { "chapter_id": "...", "seq": 8, "overall_score": 0.57, "weakest_metric": "pacing" }
  ],
  "imagination_usage": {
    "total_scheduled": 12,
    "total_used": 11,
    "used_rate": 0.917
  }
}
```

新增 `imagination_usage`：展示本卷内 Imagination 排期与实际使用情况（回路健康度指标）。

---

### 3.28 修订回流端点

> 背景：人工修订/裁决必须回写为系统记忆与设定，后续生成才能自动遵守。本节定义该机制的 HTTP 入口。

#### `POST /api/v1/works/{work_id}/revisions` — 提交修订记录

人工完成章节编辑、设定修改等操作后，正式提交修订，触发回流流水线。

**请求体**：

```json
{
  "revision_type": "chapter_text_edit",
  "target_type": "segment",
  "target_id": "019018ab-seg-042",
  "diff_summary": "将'雍容地一笑'改为'短促地哼了一声，转身离去'",
  "diff_detail": {
    "segment_id": "019018ab-seg-042",
    "old_text": "他雍容地一笑，转身离去。",
    "new_text": "他短促地哼了一声，转身离去。"
  },
  "backflow_options": {
    "update_memory": true,
    "update_voice_profile": true,
    "retrigger_consistency_check": true
  }
}
```

`revision_type` 枚举：`chapter_text_edit` / `setting_item_update` / `character_update` / `flag_adjudication` / `outline_update`

**响应体（201）**：

```json
{
  "revision_id": "019018ab-rev-001",
  "work_id": "019018ab-...",
  "revision_type": "chapter_text_edit",
  "target_id": "019018ab-seg-042",
  "backflow_status": "processing",
  "backflow_task_id": "019018ab-task-backflow-001",
  "created_at": "2026-06-19T13:00:00Z"
}
```

---

#### `GET /api/v1/works/{work_id}/revisions` — 列出修订历史

```
GET /api/v1/works/{work_id}/revisions?revision_type=chapter_text_edit&limit=20&order=desc
```

**响应体（200）**：列表包装结构。

---

#### `GET /api/v1/works/{work_id}/revisions/{revision_id}` — 获取单修订记录

**响应体（200）**：完整 RevisionRecord 对象。

---

#### `GET /api/v1/works/{work_id}/impact-analysis` — 修订影响分析查询

在提交修订前，查询影响范围预估（只读）。

```
GET /api/v1/works/{work_id}/impact-analysis?target_type=setting_item&target_id=...&change_type=content_update
```

**响应体（200）**：

```json
{
  "target_type": "setting_item",
  "target_id": "...",
  "target_name": "修仙等级体系",
  "impact": {
    "affected_chapters_count": 38,
    "affected_chapters": [
      { "chapter_id": "...", "seq": 12, "impact_reason": "直接引用该设定项" }
    ],
    "affected_memory_entries": 2,
    "affected_foreshadows": 1,
    "consistency_recheck_required": true
  },
  "warning": "此修改将影响 38 章已生成内容，建议先做影响评估再决定是否提交。",
  "analyzed_at": "2026-06-19T13:00:00Z"
}
```

---

### 3.29 批量操作端点

#### `POST /api/v1/works/{work_id}/chapters/batch-generate` — 批量触发多章生成

**请求体**：

```json
{
  "volume_id": "019018ab-vol2-...",
  "chapter_ids": ["019018ab-chap-021", "019018ab-chap-022", "019018ab-chap-023"],
  "idempotency_prefix": "batch-gen-vol2-20260619",
  "options": {
    "max_rewrite": 2,
    "consistency_severity_threshold": "high",
    "inject_imaginations": true
  }
}
```

**响应体（202）**：

```json
{
  "batch_id": "batch-019018ab-001",
  "tasks": [
    { "chapter_id": "019018ab-chap-021", "task_id": "...", "status": "queued" },
    { "chapter_id": "019018ab-chap-022", "task_id": "...", "status": "queued" },
    { "chapter_id": "019018ab-chap-023", "task_id": "...", "status": "queued" }
  ],
  "total_queued": 3,
  "estimated_total_seconds": 270
}
```

**百万字约束**：单次最多提交 20 章，超出返回 `400`；同一 work 下同时运行任务数不超过 3（可配置）。

---

#### `GET /api/v1/works/{work_id}/chapters/batch-generate/{batch_id}` — 查询批量任务状态

**响应体（200）**：

```json
{
  "batch_id": "batch-019018ab-001",
  "status": "running",
  "tasks_total": 3,
  "tasks_completed": 1,
  "tasks_failed": 0,
  "tasks_running": 1,
  "tasks_queued": 1,
  "tasks": [
    { "chapter_id": "...", "task_id": "...", "status": "completed", "word_count": 3012 },
    { "chapter_id": "...", "task_id": "...", "status": "running", "stage": "writing" },
    { "chapter_id": "...", "task_id": "...", "status": "queued" }
  ]
}
```

**批量中途单章失败**：批量任务暂停，`batch_status` 变为 `paused_on_failure`；前端人工确认后可继续或重试。

---

#### `POST /api/v1/works/{work_id}/consistency-flags/batch-adjudicate` — 批量裁决一致性标记

**请求体**：

```json
{
  "flag_ids": ["...", "...", "..."],
  "verdict": "dismissed",
  "note": "批量驳回：low 级标记经人工审阅均为误报"
}
```

**响应体（200）**：

```json
{
  "adjudicated_count": 3,
  "skipped_count": 0,
  "results": [
    { "flag_id": "...", "status": "dismissed" },
    { "flag_id": "...", "status": "dismissed" },
    { "flag_id": "...", "status": "dismissed" }
  ]
}
```

已裁决的标记自动跳过（计入 `skipped_count`），不返回错误。

#### `GET /api/v1/works/{work_id}/foreshadows/overdue` — 查询逾期未回收的伏笔

```
GET /api/v1/works/{work_id}/foreshadows/overdue?chapters_threshold=50&limit=20
```

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "...",
      "summary": "韩立左手旧疤的来历",
      "state": "planted",
      "foreshadow_chapter_seq": 1,
      "current_chapter_seq": 65,
      "chapters_elapsed": 64,
      "chapters_threshold": 50,
      "payload": { "planned_payoff_volume": 3 }
    }
  ],
  "pagination": { "..." : "..." }
}
```

---

#### `DELETE /api/v1/works/{work_id}/foreshadows/{foreshadow_id}` — 软删除伏笔

仅允许对 `state=abandoned` 的伏笔软删除；其余返回 `409 Conflict`。**响应（204）**。

---

### 3.19 资源端点：consistency-flags

**资源路径**：`/api/v1/works/{work_id}/consistency-flags`

对应 00 §4.3 实体：`ConsistencyFlag`（`id, chapter_id, error_class, severity, detail, evidence_refs, status`）

`error_class`：ConStory 五大类 19 子类枚举（见 00 §5）

`severity` 枚举：`low` / `medium` / `high` / `critical`

`status` 枚举：`open` / `confirmed` / `dismissed` / `fixed`

---

#### `GET /api/v1/works/{work_id}/consistency-flags` — 列出一致性标记

```
GET /api/v1/works/{work_id}/consistency-flags?status=open&severity=high&severity=critical&limit=50
```

过滤参数：`status`（多值）、`severity`（多值）、`chapter_id`、`error_class`。

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "019018ab-cf-001",
      "chapter_id": "019018ab-chap-023",
      "chapter_seq": 23,
      "error_class": "character_ooc",
      "severity": "high",
      "detail": "韩立在第23章第4段使用了与其声音档案不符的表达：'雍容地一笑'（ooc_marker）",
      "evidence_refs": {
        "segment_id": "019018ab-seg-042",
        "segment_text_excerpt": "他雍容地一笑，转身离去。",
        "voice_profile_ooc_markers": ["雍容", "温柔地笑"]
      },
      "status": "open",
      "created_at": "2026-06-19T12:00:00Z"
    }
  ],
  "pagination": { "..." : "..." }
}
```

---

#### `GET /api/v1/works/{work_id}/consistency-flags/{flag_id}` — 获取单标记

**响应体（200）**：完整 ConsistencyFlag 对象。

---

#### `PATCH /api/v1/works/{work_id}/consistency-flags/{flag_id}/adjudicate` — 裁决一致性标记

**请求体**：

```json
{
  "verdict": "confirmed",
  "note": "确认：韩立此处行为不符合人物设定，需要修改。",
  "fix_description": "将'雍容地一笑'改为'短促地哼了一声，转身离去'"
}
```

**响应体（200）**：

```json
{
  "id": "019018ab-cf-001",
  "status": "confirmed",
  "verdict": "confirmed",
  "adjudicated_at": "2026-06-19T13:00:00Z",
  "backflow_triggered": true,
  "backflow_revision_id": "019018ab-rev-001"
}
```

**约束**：已裁决标记（`confirmed/dismissed/fixed`）不可重复裁决，返回 `409 CONSISTENCY_FLAG_ALREADY_ADJUDICATED`。

---

### 3.20 资源端点：memory

**资源路径**：`/api/v1/works/{work_id}/memory`

对应 00 §4.4 实体：`MemoryEntry`（`id, work_id, scope, summary_text, source_chapter_range, embedding, updated_at`）

`scope` 枚举：`chapter` / `volume` / `global`

---

#### `GET /api/v1/works/{work_id}/memory` — 列出记忆条目

```
GET /api/v1/works/{work_id}/memory?scope=global&limit=10
```

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "019018ab-mem-001",
      "work_id": "019018ab-...",
      "scope": "global",
      "summary_text": "主角韩立自黄枫谷出走后踏上修仙之路，目前已达炼气期12层，持有七彩云丹秘方，正前往天机城……",
      "source_chapter_range": { "from_seq": 1, "to_seq": 50 },
      "updated_at": "2026-06-19T12:00:00Z"
    }
  ],
  "pagination": { "..." : "..." }
}
```

---

#### `GET /api/v1/works/{work_id}/memory/{entry_id}` — 获取单记忆条目

**响应体（200）**：完整 MemoryEntry 对象。

---

#### `PATCH /api/v1/works/{work_id}/memory/{entry_id}` — 手动修正记忆摘要

**请求体**：`{ "summary_text": "修正后的摘要" }`

**响应体（200）**：完整更新后的 MemoryEntry，`embedding_status: "pending"`。

---

#### `POST /api/v1/works/{work_id}/memory/refresh` — 触发记忆刷新（异步）

**请求体**：

```json
{
  "scope": "volume",
  "volume_id": "019018ab-vol1-...",
  "idempotency_key": "refresh-vol1-20260619"
}
```

**响应体（202）**：`{ "task_id": "...", "status": "queued" }`

---

### 3.21 资源端点：snapshots

**资源路径**：`/api/v1/works/{work_id}/chapters/{chapter_id}/snapshots`

对应 00 §4.4 实体：`Snapshot`（`id, chapter_id, content, created_by, parent_id, branch_label, created_at`）

---

#### `GET /api/v1/works/{work_id}/chapters/{chapter_id}/snapshots` — 列出章快照

```
GET /api/v1/works/{work_id}/chapters/{chapter_id}/snapshots?order=desc&limit=20
```

**响应体（200）**：列表包装，默认不含 `content`（全文可达数千字，加 `fields=content` 显式请求）。

---

#### `GET /api/v1/works/{work_id}/chapters/{chapter_id}/snapshots/{snapshot_id}` — 获取单快照（含全文）

**响应体（200）**：完整 Snapshot 对象含 `content`。

---

#### `POST /api/v1/works/{work_id}/chapters/{chapter_id}/snapshots` — 手动保存快照

**请求体**：

```json
{
  "content": "章节全文...",
  "created_by": "human",
  "branch_label": "human-edit-20260619"
}
```

**响应体（201）**：Snapshot 对象（不含 `content`，需时重新 GET）。

---

#### `POST /api/v1/works/{work_id}/chapters/{chapter_id}/snapshots/{snapshot_id}/restore` — 从快照恢复

**请求体**：`{ "reason": "恢复到 AI 初稿" }`

**响应体（200）**：

```json
{
  "restored_snapshot_id": "...",
  "new_snapshot_id": "...",
  "chapter_id": "...",
  "segments_replaced": 8,
  "restored_at": "2026-06-19T14:00:00Z"
}
```

---

#### `GET /api/v1/works/{work_id}/chapters/{chapter_id}/snapshots/{snapshot_id}/diff` — 查看快照对比

对比指定快照与当前版本（或另一个快照）的文本差异。

```
GET /api/v1/works/{work_id}/chapters/{chapter_id}/snapshots/{snapshot_id}/diff?compare_to=current
```

`compare_to` 参数：`current`（与当前正文对比）或另一个 `snapshot_id`。

**响应体（200）**：

```json
{
  "snapshot_id": "...",
  "compare_to": "current",
  "diff": [
    { "type": "delete", "text": "他雍容地一笑，转身离去。" },
    { "type": "insert", "text": "他短促地哼了一声，转身离去。" }
  ],
  "change_summary": "1处修改，涉及1个段落"
}
```

---

### 3.22 资源端点：materials

**资源路径**：`/api/v1/materials` 及 `/api/v1/works/{work_id}/materials`（作品级过滤）

对应 00 §4.4 实体：`Material`（`id, owner_id, work_id, type, title, content, source, tags, embedding, status, created_at`）及 `MaterialRef`（`id, material_id, used_in, target_id, ref_type, relevance, created_at`）

`type` 枚举：`inspiration` / `reference` / `research` / `snippet` / `name` / `place_idea` / `image` / `quote` / `worldbuilding` / `style_sample`

---

#### `POST /api/v1/materials` — 创建素材

**请求体**：

```json
{
  "work_id": "019018ab-...",
  "type": "style_sample",
  "title": "克制写法范本",
  "content": {
    "text": "韩立停住了脚步。前方那个被拦住的身影，发髻上还插着他在黄枫谷见过的那种木簪。他不认识她。他也没有任何理由停在这里。",
    "notes": "行动取代心理描写的典型范本"
  },
  "source": "原创",
  "tags": ["克制", "show-dont-tell", "韩立视角"]
}
```

**响应体（201）**：完整 Material 对象，`embedding` 异步生成。

---

#### `GET /api/v1/works/{work_id}/materials` — 列出作品素材

```
GET /api/v1/works/{work_id}/materials?type=style_sample&type=inspiration&limit=20
```

**响应体（200）**：列表包装结构。

---

#### `GET /api/v1/materials/{material_id}` — 获取单素材

**响应体（200）**：完整 Material 对象。

---

#### `PATCH /api/v1/materials/{material_id}` — 更新素材

**响应体（200）**：完整更新后的 Material 对象。

---

#### `DELETE /api/v1/materials/{material_id}` — 软删除素材

**响应（204）**。

---

#### `POST /api/v1/materials/{material_id}/refs` — 记录素材引用

记录某素材被引用到具体章节/段落/设定。

**请求体**：

```json
{
  "used_in": "chapter",
  "target_id": "019018ab-chap-014",
  "ref_type": "style_inspiration",
  "relevance": 0.88
}
```

**响应体（201）**：完整 MaterialRef 对象。

---

### 3.6 内核端点：optionsets

**资源路径**：`/api/v1/works/{work_id}/optionsets` 及 `/api/v1/works/{work_id}/chapters/{chapter_id}/optionsets`

对应 00 §4.1 实体：`OptionSet`（`id, work_id, decision_point, options, chosen_option_id, choose_rationale, imagination_refs, generated_by, created_at`）

---

#### `POST /api/v1/works/{work_id}/optionsets/generate` — 触发 OptionSet 生成（异步）

这是**关键决策点多方案生成**的入口。提交后返回 task_id，完成后通过 SSE 推送 `optionset.created` 事件。

**请求体**：

```json
{
  "chapter_id": "019018ab-chap-014",
  "question": "韩立是否主动出手救南宫婉？",
  "n_options": 3,
  "trigger_type": "manual_scene",
  "context_summary": "天机城内，韩立目睹南宫婉被天机阁长老针对，此刻动手将暴露他的真实修为",
  "idempotency_key": "gen-optionset-chap014-attempt1"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `chapter_id` | string | 是 | 发生决策的章节 ID |
| `question` | string | 是 | 具体的选择问题，max 200 字符 |
| `n_options` | integer | 否 | 方案数量，2–4，默认 3 |
| `trigger_type` | string | 否 | `auto_plot` / `auto_char` / `manual_scene` / `manual_outline`，默认 `manual_scene` |
| `context_summary` | string | 否 | 决策点前情摘要，max 500 字符；不填则系统自动生成 |
| `idempotency_key` | string | 是 | 幂等键 |

**响应体（202）**：

```json
{
  "task_id": "019018ab-task-optionset-001",
  "task_type": "generate_optionset",
  "status": "queued",
  "work_id": "019018ab-...",
  "chapter_id": "019018ab-chap-014",
  "idempotency_key": "gen-optionset-chap014-attempt1",
  "created_at": "2026-06-19T11:00:00Z",
  "estimated_seconds": 30
}
```

生成完成后，新 OptionSet 通过 SSE `optionset.created` 事件推送，并可通过以下 GET 端点查询。

---

#### `GET /api/v1/works/{work_id}/optionsets` — 列出作品下的所有 OptionSet

```
GET /api/v1/works/{work_id}/optionsets?pending_only=true&limit=20
```

**过滤参数**：

| 参数 | 说明 |
|---|---|
| `pending_only` | `true` 则只返回 `chosen_option_id` 为 null 的待决策 OptionSet |
| `chapter_id` | 按章节过滤 |

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "019018ab-os-0001",
      "work_id": "019018ab-...",
      "decision_point": {
        "chapter_id": "019018ab-chap-014",
        "chapter_seq": 14,
        "trigger_type": "manual_scene",
        "context_summary": "天机城内，韩立目睹南宫婉被天机阁长老针对……",
        "question": "韩立是否主动出手救南宫婉？"
      },
      "options": [
        {
          "option_id": "A",
          "label": "主动出手（暴露实力）",
          "summary": "韩立出手相救，但暴露了修为，引来天机阁注意",
          "draft_excerpt": "韩立站在人群边缘，眼看着那名长老举起手掌……",
          "emotional_direction": "紧张 → 意外温情",
          "character_cost": "韩立暴露修为，失去最重要的隐匿优势",
          "plot_consequence": "埋下韩立-南宫婉情感线，但引来天机阁长老的注意",
          "intent_alignment": "契合北极星：人物在关键时刻显露内心真实，情感代价清晰",
          "redline_check": "无"
        },
        {
          "option_id": "B",
          "label": "按兵不动（保持隐匿）",
          "summary": "韩立选择不暴露，南宫婉被另一人所救",
          "draft_excerpt": "他知道他不该动……",
          "emotional_direction": "压抑 → 事后愧疚",
          "character_cost": "韩立安然无恙，但内心出现一个新的裂缝",
          "plot_consequence": "南宫婉获救，但韩立与她的关系增加了一层未说出的东西",
          "intent_alignment": "与北极星情感弧有一定张力：主角过度封闭可能影响情感节奏",
          "redline_check": "无"
        },
        {
          "option_id": "C",
          "label": "间接施援（不暴露）",
          "summary": "韩立用隐秘手段干预，不直接出面",
          "draft_excerpt": "他的手指微微动了一下……",
          "emotional_direction": "暗流涌动 → 隐秘满足",
          "character_cost": "几乎无代价，但错失了真实情感触碰的机会",
          "plot_consequence": "南宫婉不知是韩立所为，伏笔待后续揭晓",
          "intent_alignment": "高度契合：既保持了韩立的谨慎性格，又让情感线隐而不发",
          "redline_check": "无"
        }
      ],
      "chosen_option_id": null,
      "choose_rationale": null,
      "imagination_refs": ["019018ab-imag-0003"],
      "generated_by": "OptionSetAgent-v1",
      "created_at": "2026-06-19T11:05:00Z"
    }
  ],
  "pagination": { "cursor": null, "has_more": false, "total_count": 1 }
}
```

---

#### `GET /api/v1/works/{work_id}/chapters/{chapter_id}/optionsets` — 获取章节下的 OptionSet 列表

等价于 `GET /api/v1/works/{work_id}/optionsets?chapter_id={chapter_id}`，推荐使用此路径以强约束章节归属。

**响应体（200）**：同上列表结构。

---

#### `GET /api/v1/works/{work_id}/optionsets/{optionset_id}` — 获取单个 OptionSet

**响应体（200）**：完整 OptionSet 对象（同列表中的单条）。

---

#### `POST /api/v1/works/{work_id}/optionsets/{optionset_id}/choose` — 记录作者选择

这是**关键决策点的执行动作**。记录选择后，自动触发 PreferenceSignal 回流（内核2），并返回继续写作的任务 ID。

**请求体**：

```json
{
  "chosen_option_id": "C",
  "choose_rationale": "C 更符合韩立的性格，他不会轻易暴露自己，但也不会真的袖手旁观",
  "trigger_writing": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `chosen_option_id` | string | 是 | 选择的方案 ID（"A"/"B"/"C"/"D"） |
| `choose_rationale` | string | 否 | 作者的选择理由，建议填写（回流到 PreferenceSignal） |
| `trigger_writing` | boolean | 否 | 是否立即触发以所选方案继续写作，默认 false |

**响应体（200）**：

```json
{
  "optionset_id": "019018ab-os-0001",
  "chosen_option_id": "C",
  "choose_rationale": "C 更符合韩立的性格……",
  "preference_signals_created": 3,
  "writing_task_id": "019018ab-task-write-014",
  "writing_task_status": "queued",
  "updated_at": "2026-06-19T11:10:00Z"
}
```

`preference_signals_created`：本次选择产生的 PreferenceSignal 数量（1 条正向 + 2 条负向）。
`writing_task_id`：若 `trigger_writing=true`，此字段非空，前端可订阅该任务的 SSE 流。

**状态机约束**：`chosen_option_id` 已非 null 的 OptionSet 不可再次 choose，返回 `409 OPTIONSET_ALREADY_CHOSEN`。

---

### 3.7 内核端点：feedback-notes

**资源路径**：`/api/v1/works/{work_id}/feedback-notes`

对应 00 §4.1 实体：`FeedbackNote`（`id, work_id, target_type, target_id, nl_critique, parsed_directive, confirmed, resulted_snapshot_id, parent_feedback_id, created_at`）

`target_type` 枚举：`segment` / `chapter` / `option` / `setting` / `outline`

---

#### `POST /api/v1/works/{work_id}/feedback-notes` — 提交意见

这是**协作回路主交互入口**：作者提交自然语言批评，系统同步解析为结构化指令（ParsedDirective），返回解析结果供作者确认。

**请求体**：

```json
{
  "target_type": "segment",
  "target_id": "019018ab-seg-042",
  "nl_critique": "这段感觉不像韩立，太冲动了，他不会这么直接表达情绪"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | string | 是 | `segment` / `chapter` / `option` / `setting` / `outline` |
| `target_id` | string | 是 | 被批评对象的 ID |
| `nl_critique` | string | 是 | 自然语言批评，max 1000 字符 |

**响应体（201）**：

```json
{
  "id": "019018ab-fb-0001",
  "work_id": "019018ab-...",
  "target_type": "segment",
  "target_id": "019018ab-seg-042",
  "nl_critique": "这段感觉不像韩立，太冲动了，他不会这么直接表达情绪",
  "parsed_directive": {
    "critique_type": "characterization",
    "primary_instruction": "重写该段，确保韩立的行为与其'谨慎、内敛'的性格设定一致",
    "constraints": [
      "保留事件本身（韩立仍然到达了天机阁）",
      "只改行为方式和内心活动"
    ],
    "style_direction": "更克制，减少主动情绪，增加观察和计算",
    "scope": "segment",
    "scope_refs": ["019018ab-seg-042"],
    "parse_confidence": 0.87
  },
  "confirmed": false,
  "resulted_snapshot_id": null,
  "parent_feedback_id": null,
  "created_at": "2026-06-19T12:00:00Z"
}
```

> 当 `parse_confidence < 0.7` 时，前端必须展示"意图确认"对话框，作者确认或修正后再调用 confirm 端点。当 `parse_confidence >= 0.7` 时，前端可选择直接调用 confirm 端点（无需手动确认）。

---

#### `POST /api/v1/works/{work_id}/feedback-notes/{feedback_id}/confirm` — 确认解析并触发重做

作者确认 ParsedDirective 正确（或修正后确认），触发异步重做任务。

**请求体**：

```json
{
  "confirmed_directive": null,
  "idempotency_key": "rewrite-fb-0001-attempt1"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `confirmed_directive` | object\|null | 否 | null 表示接受自动解析结果；传入完整 ParsedDirective 对象则覆盖（作者手动修正理解） |
| `idempotency_key` | string | 是 | 重做任务的幂等键 |

**响应体（202）**：

```json
{
  "feedback_id": "019018ab-fb-0001",
  "confirmed": true,
  "rewrite_task_id": "019018ab-task-rewrite-001",
  "task_status": "queued",
  "estimated_seconds": 60
}
```

前端可通过 `GET /api/v1/tasks/{rewrite_task_id}` 轮询或 `GET /api/v1/tasks/{rewrite_task_id}/stream` 订阅 SSE 进度。

**状态机约束**：`confirmed=true` 的 FeedbackNote 若已有进行中的重做任务，返回 `409 FEEDBACK_REWRITE_IN_PROGRESS`。

---

#### `GET /api/v1/works/{work_id}/feedback-notes` — 列出意见历史

```
GET /api/v1/works/{work_id}/feedback-notes?target_type=segment&target_id={segment_id}&limit=20&order=desc
```

**过滤参数**：

| 参数 | 说明 |
|---|---|
| `target_type` | 枚举过滤 |
| `target_id` | 精确过滤某段落/章节的全部意见 |
| `confirmed` | `true` / `false` |
| `chapter_id` | 按章节范围过滤（查询该章所有 segment/chapter 的意见） |

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "019018ab-fb-0001",
      "target_type": "segment",
      "target_id": "019018ab-seg-042",
      "nl_critique": "这段感觉不像韩立……",
      "parsed_directive": { "..." : "..." },
      "confirmed": true,
      "resulted_snapshot_id": "019018ab-snap-0023",
      "parent_feedback_id": null,
      "created_at": "2026-06-19T12:00:00Z"
    }
  ],
  "pagination": { "cursor": null, "has_more": false, "total_count": 8 }
}
```

---

#### `GET /api/v1/works/{work_id}/feedback-notes/{feedback_id}` — 获取单条意见

**响应体（200）**：完整 FeedbackNote 对象，附加 `chain`（链式反馈链，从根节点到当前节点的路径）：

```json
{
  "id": "019018ab-fb-0002",
  "parent_feedback_id": "019018ab-fb-0001",
  "chain": [
    { "id": "019018ab-fb-0001", "nl_critique": "这段感觉不像韩立……", "resulted_snapshot_id": "..." },
    { "id": "019018ab-fb-0002", "nl_critique": "重做版好多了，但结尾那句话还是太直白……", "resulted_snapshot_id": "..." }
  ],
  "...": "..."
}
```

---

#### `GET /api/v1/works/{work_id}/feedback-notes/{feedback_id}/rewrite-status` — 查询重做进度

```
GET /api/v1/works/{work_id}/feedback-notes/{feedback_id}/rewrite-status
```

**响应体（200）**：

```json
{
  "feedback_id": "019018ab-fb-0001",
  "confirmed": true,
  "rewrite_task_id": "019018ab-task-rewrite-001",
  "task_status": "completed",
  "resulted_snapshot_id": "019018ab-snap-0023",
  "diff_available": true,
  "deviation_report": {
    "has_hard_violations": false,
    "arc_deviation_score": 0.12,
    "arc_deviation_note": "本章情感走向与北极星高度一致"
  }
}
```

---

### 3.8 内核端点：taste-model

**资源路径**：`/api/v1/works/{work_id}/taste-model` 及 `/api/v1/users/{user_id}/taste-model`

对应 00 §4.1 实体：`TasteModel`（`id, owner_id, work_id(nullable), positive_exemplars, negative_list, learned_preferences, version, updated_at`）

TasteModel 有两种作用域：
- **作品级**（`work_id` 非 null）：该作品专属的品味模型，由该作品的 PreferenceSignal 学习生成
- **作者级**（`work_id` 为 null）：跨作品的通用品味模型（Phase 4 功能）

---

#### `GET /api/v1/works/{work_id}/taste-model` — 获取作品级品味模型

**响应体（200）**：

```json
{
  "id": "019018ab-taste-0001",
  "owner_id": "user-001",
  "work_id": "019018ab-...",
  "positive_exemplars": [
    {
      "label": "克制情感写法",
      "sample_text": "韩立停住了脚步。前方那个被拦住的身影，发髻上还插着他在黄枫谷见过的那种木簪。",
      "style_descriptors": {
        "keywords": ["行动取代心理", "细节承载情感", "留白"],
        "tone": "克制",
        "sentence_rhythm": "短句为主"
      }
    }
  ],
  "negative_list": [
    "陈词滥调：'眼眶湿润了'",
    "AI腔套路：'心中涌现出复杂的情感'",
    "过度修饰：连续三个以上形容词叠加",
    "告诉读者情感而非展示：'他感到非常悲伤'"
  ],
  "learned_preferences": {
    "preferred_pacing": "中快节奏，对话密度高",
    "preferred_pov": "限制第三人称，贴近主角心理",
    "disliked_patterns": ["大段心理独白", "冗长环境描写", "人物行为动机外化"],
    "signal_count": 47,
    "last_learned_at": "2026-06-19T11:00:00Z"
  },
  "version": 8,
  "updated_at": "2026-06-19T11:00:00Z"
}
```

若该作品尚无 TasteModel（信号不足），返回 `404 TASTE_MODEL_NOT_FOUND`，附 `detail.signal_count`（当前已有多少信号，提示还需多少才能建模）。

---

#### `PATCH /api/v1/works/{work_id}/taste-model` — 手动更新品味模型

作者可手动添加正面范例、补充黑名单条目，或调整 learned_preferences。

**请求体**：

```json
{
  "positive_exemplars_add": [
    {
      "label": "场景节奏示范",
      "sample_text": "他不认识她。他也没有任何理由停在这里。脚步停了三息，然后他慢慢转过身。",
      "style_descriptors": {
        "keywords": ["极简", "动作序列", "内心通过行为暗示"],
        "tone": "冷静克制"
      }
    }
  ],
  "negative_list_add": [
    "过度使用感叹号表达情绪",
    "用天气隐喻角色心情（太陈旧）"
  ]
}
```

**可操作字段**：`positive_exemplars_add`（追加范例）、`positive_exemplars_remove`（按 label 移除）、`negative_list_add`（追加黑名单）、`negative_list_remove`（按内容移除）。

**响应体（200）**：完整更新后的 TasteModel 对象，`version` 递增。

---

#### `POST /api/v1/works/{work_id}/taste-model/rebuild` — 触发品味模型重建（异步）

基于当前所有 PreferenceSignal 重新计算 learned_preferences（内核2 学习算法）。通常由系统自动触发（每积累 N 条信号触发一次），也支持手动触发。

**请求体**：

```json
{
  "idempotency_key": "rebuild-taste-work001-20260619"
}
```

**响应体（202）**：

```json
{
  "task_id": "019018ab-task-taste-rebuild-001",
  "task_type": "rebuild_taste_model",
  "status": "queued"
}
```

---

### 3.9 内核端点：preference-signals

**资源路径**：`/api/v1/works/{work_id}/preference-signals`

对应 00 §4.1 实体：`PreferenceSignal`（`id, owner_id, work_id, source, signal, polarity, weight, created_at`）

PreferenceSignal 通常由系统内部自动创建（OptionSet 选择 / FeedbackNote 提交时），不需要前端手动 POST。但提供只读查询端点供调试和品味模型透明化展示使用。

---

#### `GET /api/v1/works/{work_id}/preference-signals` — 列出偏好信号

```
GET /api/v1/works/{work_id}/preference-signals?source=option_choice&polarity=%2B&limit=20&order=desc
```

**过滤参数**：

| 参数 | 说明 |
|---|---|
| `source` | `option_choice` / `feedback` / `rating` / `revision_diff` / `exemplar` |
| `polarity` | `+` / `-`（URL 编码：`%2B` / `-`） |
| `since` | ISO 8601 时间戳，只返回该时间之后的信号 |

**响应体（200）**：

```json
{
  "data": [
    {
      "id": "019018ab-ps-0001",
      "owner_id": "user-001",
      "work_id": "019018ab-...",
      "source": "option_choice",
      "signal": {
        "chosen_emotional_direction": "暗流涌动 → 隐秘满足",
        "chosen_character_cost": "几乎无代价，但错失了真实情感触碰的机会",
        "optionset_id": "019018ab-os-0001",
        "chosen_option_id": "C",
        "choose_rationale": "C 更符合韩立的性格……"
      },
      "polarity": "+",
      "weight": 1.0,
      "created_at": "2026-06-19T11:10:00Z"
    }
  ],
  "pagination": { "cursor": null, "has_more": true, "total_count": 47 }
}
```

---

#### `GET /api/v1/works/{work_id}/preference-signals/summary` — 获取偏好信号汇总

前端"品味画像"面板使用，展示当前作品的偏好信号统计概览。

**响应体（200）**：

```json
{
  "work_id": "019018ab-...",
  "total_signals": 47,
  "by_source": {
    "option_choice": 18,
    "feedback": 24,
    "revision_diff": 5
  },
  "by_polarity": {
    "positive": 31,
    "negative": 16
  },
  "top_positive_patterns": [
    "克制情感写法（14次正向信号）",
    "短句节奏（9次正向信号）"
  ],
  "top_negative_patterns": [
    "大段心理独白（8次负向信号）",
    "AI腔模板句式（6次负向信号）"
  ],
  "last_signal_at": "2026-06-19T11:10:00Z",
  "taste_model_version": 8
}
```

---

至此第二部分（§3.4–§3.9）内容结束。

---

## 4. 数据契约

本模块使用的全部实体与 00 §4 严格对齐。以下为完整映射（内核实体标注★）：

| API 路径段 | 00 §4 实体 | 关键字段 |
|---|---|---|
| ★ `imaginations` | Imagination | id, work_id, raw_text, type, structured, status, scheduled_for, resulted_in_chapter, embedding, obsolete |
| ★ `author-intent` | AuthorIntent | id, work_id(1:1), reader_feeling, core_emotional_arc, why_write, central_promise, do_not_betray, version |
| ★ `optionsets` | OptionSet | id, work_id, decision_point, options, chosen_option_id, choose_rationale, imagination_refs |
| ★ `feedback-notes` | FeedbackNote | id, work_id, target_type, target_id, nl_critique, parsed_directive, confirmed, resulted_snapshot_id, parent_feedback_id |
| ★ `taste-model` | TasteModel | id, owner_id, work_id, positive_exemplars, negative_list, learned_preferences, version |
| ★ `preference-signals` | PreferenceSignal | id, owner_id, work_id, source, signal, polarity, weight |
| `works` | Work | id, title, premise, genre, structure_type |
| `volumes` | Volume | id, work_id, seq, title, arc_goal, structure_beats, status |
| `chapters` | Chapter | id, volume_id, seq, title, outline, beat_targets, hook_text, hook_strength, word_count, status |
| `segments` | Segment | id, chapter_id, seq, text, embedding, created_by |
| `characters` | Character + CharState | id, work_id, name, traits, motivation, voice_profile, relations |
| `setting-items` | SettingItem | id, work_id, type, name, content, first_chapter_id, embedding |
| `entity-relations` | EntityRelation | id, work_id, src_entity, dst_entity, relation, valid_from_chapter, valid_to_chapter |
| `timeline-events` | TimelineEvent | id, work_id, chapter_id, abs_time, rel_order, description, entity_refs, embedding |
| `foreshadows` | Foreshadow | id, work_id, summary, foreshadow_chapter_id, trigger_chapter_id, payoff_chapter_id, state, payload |
| `consistency-flags` | ConsistencyFlag | id, chapter_id, error_class, severity, detail, evidence_refs, status |
| `memory` | MemoryEntry | id, work_id, scope, summary_text, source_chapter_range, embedding |
| `snapshots` | Snapshot | id, chapter_id, content, created_by, parent_id, branch_label |
| `materials` | Material + MaterialRef | id, owner_id, work_id, type, title, content, source, tags, embedding, status |

**通用字段约定**：
- 所有实体含 `created_at`（ISO 8601 UTC）
- 重要实体含 `updated_at`
- 重要实体含 `deleted_at`（软删除，null 表示未删除）
- ID 全部为 UUID v7 字符串

---

## 5. 对外接口：端点全索引

### 5.1 内核端点（新增，★ 标注）

| 类别 | 方法 | 路径 | 说明 |
|---|---|---|---|
| ★ **Imaginations** | POST | `/api/v1/works/{id}/imaginations` | 捕获新想象 |
| | GET | `/api/v1/works/{id}/imaginations` | 列出想象库 |
| | GET | `/api/v1/works/{id}/imaginations/{id}` | 获取单条想象 |
| | PATCH | `/api/v1/works/{id}/imaginations/{id}` | 更新想象（排期/过时） |
| | POST | `/api/v1/works/{id}/imaginations/{id}/confirm-schedule` | 确认排期 |
| | DELETE | `/api/v1/works/{id}/imaginations/{id}` | 软删除想象 |
| ★ **AuthorIntent** | GET | `/api/v1/works/{id}/author-intent` | 获取北极星 |
| | PUT | `/api/v1/works/{id}/author-intent` | 初始化/整体替换北极星 |
| | PATCH | `/api/v1/works/{id}/author-intent` | 增量更新北极星 |
| | GET | `/api/v1/works/{id}/author-intent/history` | 历史版本列表 |
| | GET | `/api/v1/works/{id}/author-intent/history/{version}` | 特定版本快照 |
| ★ **OptionSets** | POST | `/api/v1/works/{id}/optionsets/generate` | 触发方案生成（异步） |
| | GET | `/api/v1/works/{id}/optionsets` | 列出所有 OptionSet |
| | GET | `.../chapters/{id}/optionsets` | 按章节列出 OptionSet |
| | GET | `/api/v1/works/{id}/optionsets/{id}` | 获取单个 OptionSet |
| | POST | `/api/v1/works/{id}/optionsets/{id}/choose` | 记录作者选择 |
| ★ **FeedbackNotes** | POST | `/api/v1/works/{id}/feedback-notes` | 提交意见（含同步解析） |
| | POST | `.../feedback-notes/{id}/confirm` | 确认并触发重做（异步） |
| | GET | `/api/v1/works/{id}/feedback-notes` | 列出意见历史 |
| | GET | `.../feedback-notes/{id}` | 获取单条意见（含链） |
| | GET | `.../feedback-notes/{id}/rewrite-status` | 查询重做进度 |
| ★ **TasteModel** | GET | `/api/v1/works/{id}/taste-model` | 获取作品级品味模型 |
| | PATCH | `/api/v1/works/{id}/taste-model` | 手动更新品味模型 |
| | POST | `/api/v1/works/{id}/taste-model/rebuild` | 触发模型重建（异步） |
| ★ **PreferenceSignals** | GET | `/api/v1/works/{id}/preference-signals` | 列出偏好信号 |
| | GET | `/api/v1/works/{id}/preference-signals/summary` | 获取偏好信号汇总 |

### 5.2 正文与设定资源端点

| 类别 | 方法 | 路径 | 说明 |
|---|---|---|---|
| **Works** | POST/GET | `/api/v1/works` | 创建/列出作品 |
| | GET/PATCH/DELETE | `/api/v1/works/{id}` | 获取/更新/软删除作品 |
| **Volumes** | POST/GET | `/api/v1/works/{id}/volumes` | 创建/列出卷 |
| | GET/PATCH/DELETE | `.../volumes/{id}` | 获取/更新/软删除卷 |
| **Chapters** | POST/GET | `.../volumes/{id}/chapters` | 创建/列出章 |
| | GET/PATCH/DELETE | `/api/v1/works/{id}/chapters/{id}` | 获取/更新/软删除章 |
| **Segments** | GET/POST | `.../chapters/{id}/segments` | 获取段落列表/追加段落 |
| | PATCH/DELETE | `.../segments/{id}` | 编辑/软删除段落 |
| **Characters** | POST/GET | `/api/v1/works/{id}/characters` | 创建/列出角色 |
| | GET/PATCH/DELETE | `.../characters/{id}` | 获取/更新/软删除角色 |
| | GET/POST | `.../characters/{id}/states` | 角色状态时间线 |
| **SettingItems** | POST/GET | `/api/v1/works/{id}/setting-items` | 创建/列出设定项 |
| | GET/PATCH/DELETE | `.../setting-items/{id}` | 获取/更新/软删除设定项 |
| **EntityRelations** | POST/GET | `/api/v1/works/{id}/entity-relations` | 创建/列出实体关系 |
| | PATCH/DELETE | `.../entity-relations/{id}` | 更新/软删除关系 |
| **TimelineEvents** | POST/GET | `/api/v1/works/{id}/timeline-events` | 创建/列出事件 |
| | PATCH/DELETE | `.../timeline-events/{id}` | 更新/软删除事件 |
| **Foreshadows** | POST/GET | `/api/v1/works/{id}/foreshadows` | 创建/列出伏笔 |
| | PATCH/DELETE | `.../foreshadows/{id}` | 更新/软删除伏笔 |
| | GET | `.../foreshadows/overdue` | 查询逾期未回收伏笔 |
| **ConsistencyFlags** | GET | `.../consistency-flags` | 列出一致性标记 |
| | GET | `.../consistency-flags/{id}` | 获取单标记 |
| | PATCH | `.../consistency-flags/{id}/adjudicate` | 裁决标记 |
| **Memory** | GET | `.../memory` | 列出记忆条目 |
| | GET/PATCH | `.../memory/{id}` | 获取/修正记忆条目 |
| | POST | `.../memory/refresh` | 触发记忆刷新（异步） |
| **Snapshots** | GET/POST | `.../chapters/{id}/snapshots` | 列出/保存快照 |
| | GET | `.../snapshots/{id}` | 获取单快照（含全文） |
| | POST | `.../snapshots/{id}/restore` | 从快照恢复 |
| | GET | `.../snapshots/{id}/diff` | 查看快照对比 |
| **Materials** | POST | `/api/v1/materials` | 创建素材 |
| | GET | `/api/v1/works/{id}/materials` | 列出作品素材 |
| | GET/PATCH/DELETE | `/api/v1/materials/{id}` | 获取/更新/软删除素材 |
| | POST | `/api/v1/materials/{id}/refs` | 记录素材引用 |

### 5.3 异步任务与 SSE

| 类别 | 方法 | 路径 | 说明 |
|---|---|---|---|
| **Tasks** | POST | `/api/v1/tasks/generate-volume-outline` | 触发卷大纲生成 |
| | POST | `/api/v1/tasks/generate-chapter-outline` | 触发章大纲生成 |
| | POST | `/api/v1/tasks/generate-chapter` | 触发写一章（核心） |
| | GET | `/api/v1/tasks/{task_id}` | 轮询任务状态 |
| | POST | `/api/v1/tasks/{task_id}/cancel` | 取消任务 |
| | GET | `/api/v1/works/{id}/tasks` | 列出作品下任务 |
| **SSE** | GET | `/api/v1/tasks/{task_id}/stream` | 单任务 SSE 进度流 |
| | GET | `/api/v1/works/{id}/stream` | 作品级全局事件流 |

### 5.4 服务型与回流

| 类别 | 方法 | 路径 | 说明 |
|---|---|---|---|
| **服务型** | GET | `.../chapters/{id}/context` | 查看章节上下文包 |
| | POST | `.../search` | 语义检索 |
| | POST | `.../chapters/{id}/check` | 触发一致性校验（异步） |
| | POST | `.../chapters/{id}/scan-foreshadows` | 触发伏笔扫描（异步） |
| | POST | `.../chapters/{id}/evaluate` | 触发章节质量评估（异步） |
| | GET | `.../chapters/{id}/quality-report` | 获取章节质量报告 |
| | POST | `.../volumes/{id}/evaluate` | 触发卷级质量评估（异步） |
| | GET | `.../volumes/{id}/quality-report` | 获取卷级质量报告 |
| **修订回流** | POST | `.../revisions` | 提交修订记录 |
| | GET | `.../revisions` | 列出修订历史 |
| | GET | `.../revisions/{id}` | 获取单修订记录 |
| | GET | `.../impact-analysis` | 修订影响分析（只读） |
| **批量** | POST | `.../chapters/batch-generate` | 批量触发章节生成 |
| | GET | `.../chapters/batch-generate/{batch_id}` | 查询批量任务状态 |
| | POST | `.../consistency-flags/batch-adjudicate` | 批量裁决一致性标记 |

---

## 6. 失败模式与缓解

| 失败场景 | 影响 | 缓解设计 |
|---|---|---|
| **LLM Provider 超时，章生成失败** | 任务 `status=failed`，章未生成 | `error.recoverable=true` + 检查点保留；新任务 `force_restart=false` 从断点恢复；前端展示 `resume_hint` |
| **前端重复提交同一章任务** | 浪费计费，产生重复内容 | `idempotency_key` 必填；重复提交返回 `409` 含已有 `task_id` |
| **Imagination 结构化失败** | `structured` 字段为 null，排期推荐缺失 | 自动重试 ≤ 3 次；超过则保持 `captured` 态，前端标记"待整理"；作者可手动填写 `structured` |
| **OptionSet 方案差异不足** | 内部差异度校验失败，任务报 `422 OPTIONSET_DIFF_INSUFFICIENT` | 重试生成（最多 2 次）；仍不足则返回最佳结果并在响应中标注 `diff_warning` |
| **FeedbackNote 解析置信度低（<0.7）** | 意见被误解导致错误改写 | `confirmed=false`；前端必须展示确认对话框；`confirmed_directive=null` 确认前不触发重做 |
| **重做破坏非目标内容** | 段落 A 的意见导致段落 B 被意外修改 | `ParsedDirective.scope_refs` 严格限定改写范围；重做完成后前端提供 diff 预览，作者可拒绝接受 |
| **SSE 连接中断** | 前端丢失进度推送 | 客户端携带 `Last-Event-ID` 重连；服务端保留最近 100 条事件 5 分钟；重连后回放断点后事件 |
| **大集合全量拉取超时** | 响应体过大，网关超时 | 强制游标分页；`limit` 默认 20，上限 100；`fields` 参数裁剪大文本字段 |
| **硬红线被意外删除** | 偏离检测失去保护 | 删除 `hard` 红线返回 `409 HARD_REDLINE_DELETE_REQUIRES_CONFIRM`；需附 `confirm_token` 才能执行 |
| **AuthorIntent 偏离检测误报** | 每章都提示红线违反，作者疲劳 | 偏离检测 `confidence < 0.85` 时不显示警告；作者可一键"标记误报"；误报率超 20% 时提示细化红线描述 |
| **品味模型信号不足** | TasteModel 无法建立，返回 404 | 响应 detail 中告知当前信号数量及建议；未达阈值前用默认品质要求替代 |
| **批量生成中途某章失败** | 后续章节依赖前章摘要，连锁错误 | 批量任务串行执行；单章失败后 `batch_status=paused_on_failure`；前端人工确认后可继续或重试 |
| **软删除资源被引用** | 关联查询返回空，UI 状态异常 | 软删除前检查下游引用；有引用返回 `409` 含 `referenced_by` 清单；前端决定是否强制删除 |
| **修订提交后记忆未同步** | 后续章节使用过期记忆 | 修订提交触发 `backflow_task`；任务完成前前端展示"记忆待更新"警告 |

---

## 7. MVP vs 完整版

### 7.1 MVP（可跑通协作回路主线的最小端点集）

MVP 标准：能跑通"人想象→AI写→人看选项→人提意见→AI重做"这条主线。

| 功能类别 | MVP 必须上线（P0） |
|---|---|
| **内核端点** | `POST /imaginations`（捕获）、`GET /imaginations`、`PATCH /imaginations/{id}`（排期/过时）、`POST /imaginations/{id}/confirm-schedule` |
| | `GET/PUT/PATCH /author-intent`（北极星读写，含硬红线保护） |
| | `POST /optionsets/generate`（触发生成）、`GET /optionsets`、`POST /optionsets/{id}/choose`（记录选择） |
| | `POST /feedback-notes`（提交意见+同步解析）、`POST /feedback-notes/{id}/confirm`（触发重做）、`GET /feedback-notes/{id}/rewrite-status` |
| **正文资源** | works / volumes / chapters / segments 完整 CRUD |
| **设定** | characters（含 states）、setting-items 完整 CRUD |
| **异步任务** | `POST /tasks/generate-chapter`（全流程，含注入 AuthorIntent + Imagination + TasteModel）、`GET /tasks/{id}` 轮询、SSE stream |
| **记忆** | `GET /memory`、`PATCH /memory/{id}` |
| **快照** | `GET/POST /snapshots`、`POST /snapshots/{id}/restore` |
| **一致性** | `GET /consistency-flags`、`PATCH /consistency-flags/{id}/adjudicate` |

**MVP 阶段可延后（P1/P2）**：

- `taste-model` 端点（MVP 阶段 TasteModel 靠默认规则，Phase 2 加学习算法）
- `preference-signals` 端点（内部自动创建，前端不展示信号列表）
- `author-intent/history` 历史版本（MVP 只保存最新版）
- `entity-relations` / `timeline-events` 完整 CRUD
- `foreshadows` CRUD（MVP 由 ExtractAgent 自动管理）
- `evaluate` / `quality-report`（MVP 只看 hook_strength）
- `impact-analysis`（影响分析延后）
- `batch-generate`（MVP 手动逐章生成）
- `POST /search` 语义检索（MVP 用全文搜索代替）
- `materials` 端点（MVP 不上素材库）

### 7.2 完整版路线图

```
Phase 1 (MVP):
  ├── 内核四件套 imaginations / author-intent / optionsets / feedback-notes
  ├── 写章任务（注入 AuthorIntent + Imagination）
  ├── works / volumes / chapters / segments / characters / setting-items
  └── SSE 单任务进度流

Phase 2 (品味学习闭环):
  ├── taste-model 端点（读写 + rebuild）
  ├── preference-signals 端点（列表 + 汇总）
  ├── author-intent/history 版本管理
  ├── 写章任务注入 TasteModel
  ├── quality-report 含 intent_alignment 指标
  └── 作品级全局 SSE 流

Phase 3 (百万字规模):
  ├── entity-relations / timeline-events / foreshadows 完整 CRUD
  ├── foreshadows/overdue 逾期查询
  ├── POST /search 语义检索
  ├── batch-generate 批量生成
  ├── impact-analysis 影响分析
  └── snapshots/diff 快照对比

Phase 4 (完整护城河):
  ├── materials 端点（素材库）
  ├── 跨作品偏好迁移（TasteModel.work_id=null）
  ├── 偏好信号可视化面板
  └── 成本统计端点（GET /works/{id}/cost-report）
```

---

## 8. 证据与引用

| 设计决策 | 证据级别 | 来源/备注 |
|---|---|---|
| 内核实体（Imagination / AuthorIntent / OptionSet / FeedbackNote）作为一等公民，有独立 REST 端点 | 【设计决策】 | 旧版 15 完全缺失这些端点——这是本次重构的核心补全。设计依据：00 §3 原则1–4，内核1 §5 对外接口 |
| 异步任务模式（POST task → GET poll / SSE） | 【设计决策】 | 章生成 P95 ≤ 120s（内核1 §2.1 G-4），HTTP 同步连接不可行；SSE 优于 WS 的决策参考 HTTP/2 规范及常见实践 |
| idempotency_key 必填 | 【设计决策】 | 参考 Stripe API 幂等设计；配合编排引擎断点续跑防重复计费 |
| 游标分页（强制，禁止全量拉取大集合） | 【设计决策】 | 百万字下章节可达 300–500（00 §3 原则10）；offset 分页在大偏移时性能差；keyset pagination 为常见最佳实践 |
| FeedbackNote 同步解析 + 异步重做分离 | 【设计决策】 | ParsedDirective 的同步返回使前端可立即展示"意图确认"对话框（内核1 §3.4.4）；重做走异步任务避免阻塞 |
| OptionSet.choose 自动触发 PreferenceSignal 回流 | 【设计决策】 | 内核1 §3.3.6；每次选择产生 1 正向 + N-1 负向信号，驱动内核2 品味模型学习 |
| 硬红线删除需 confirm_token | 【设计决策】 | 内核1 §3.2.5 `update_author_intent` 保护机制；防止误操作删除对偏离检测至关重要的约束 |
| TasteModel PATCH 支持 positive_exemplars_add/remove 增量操作 | 【设计决策】 | 避免前端每次都传入完整 exemplars 列表（可能丢失其他端上新增的范例），增量操作更安全 |
| SSE 事件类型新增 imagination_injected / imagination_used / deviation_checked | 【设计决策】 | 回路透明化需求——作者需要知道 AI 到底用了哪些想象、是否触犯了红线（00 §3 原则6） |
| 软删除 | 【设计决策】 | 00 §4 明确要求 embedding 等保留供内核2 品味分析；同一原则推广至所有重要实体 |
| UUID v7 | 【设计决策】 | 00 §4 规定；v7 时间有序，便于按创建时间游标分页 |
| 五大类 19 子类 error_class | 【已核实】 | ConStory（arXiv 2603.05890）分类体系，见 00 §5 |
| F-T-P 伏笔状态机 | 【已核实】 | CFPG（arXiv 2601.07033），见 00 §5 |
| BooookScore 式质量指标 | 【已核实】 | arXiv 2310.00785 |
| LLM 默认趋向训练均值（AI腔/平庸化），需 Imagination 注入对抗 | 【稳定知识】 | 设计哲学文档 §2 已核实引用；BooookScore arXiv 2310.00785；主题漂移 arXiv 2508.03137 |

---

## 9. 开放问题

| 编号 | 问题 | 影响范围 | 当前占位方案 |
|---|---|---|---|
| Q-01 | `FeedbackNote` 的 ParsedDirective 解析是同步还是异步更好？当前设计是同步（submit 时立即返回解析结果），但复杂意见的 LLM 解析可能需要 3–5 秒 | 前端体验、FeedbackNote 端点 | 当前 MVP 同步解析（用规则先行+LLM 补充，内核1 §3.4.3）；若 P95 > 3s 则改为异步，submit 返回 task_id |
| Q-02 | `idempotency_key` 的有效期应设多长？7 天？30 天？ | 任务管理、编排引擎 | 暂定 7 天（覆盖正常写作周期），由工程7 最终确定 |
| Q-03 | OptionSet 的 `generate` 端点应该等待 OptionSet 生成完再返回（同步，约 30s），还是走异步 task？ | 前端交互体验 | 当前设计为异步（返回 task_id）；若用户体验需要更快响应可改为同步（≤ 30s 在可接受范围） |
| Q-04 | `POST /works/{id}/search` 语义检索是否应该支持 `imaginations` 类型的 embedding 搜索？这需要 Imagination.embedding 已完成 | 实现4-记忆与检索、MVP 范围 | 暂时支持（已列入类型枚举）；MVP 阶段若 embedding 未就绪，降级为 raw_text 全文搜索 |
| Q-05 | `writing_progress` SSE 事件是否推送流式生成文本（streaming tokens）？ | 前端体验、工程3-LLM | MVP 只推字数进度（不推文本）以降低实现复杂度；完整版可选推流式文本 |
| Q-06 | 影响分析（`/impact-analysis`）的向量相似度阈值如何定？太低假阳性多，太高漏报 | 实现4-记忆与检索 | 暂定 0.75，待实际数据测试后调整（内核1 §8【需复核】） |
| Q-07 | 多用户协作写作时，`PATCH .../chapters/{id}` 的并发冲突如何处理？乐观锁？CRDT？ | 工程2-交互与编辑器、工程4-版本 | 单用户 MVP 暂不考虑；多用户版本由工程4 设计乐观锁，工程5 增加 `ETag` / `If-Match` 头 |
| Q-08 | `TasteModel` 的最小信号阈值（启动建模所需的 PreferenceSignal 最少数量）应设多少？ | 内核2-品味与偏好模型 | 暂定 10 条（Phase 2 实测后调整）；未达阈值时 taste-model 端点返回 404 并提示当前信号数 |
| Q-09 | `author-intent/history` 的版本保留策略：永久保留还是最多 N 个版本？百万字写作周期可能产生数十个版本 | 存储成本、工程7 | 暂定永久保留（AuthorIntentSnapshot 体积小）；若成本上升则改为保留最近 50 个版本 |
| Q-10 | `feedback-notes` 链式反馈的最大深度是否应限制？作者在同一段落连续反馈 10 次都不满意可能暴露更深层的问题（北极星冲突或品味模型不准确） | 内核1 §9 O-4、内核2 | 当前不硬限制深度；系统在链深 > 3 时提示作者"是否需要检查北极星或品味设置"（前端展示，不阻塞 API） |
