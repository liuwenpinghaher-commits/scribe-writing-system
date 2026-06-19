# 工程5b · 主编与协作 API(内核0/内核1 端点)

> 本文是 [工程5-API](工程5-API.md) 的拆分续篇——承载**主编智能体(内核0)与协作回路(内核1)**新增的端点。
> 拆分原因:工程5 已超 [00 §2.6 文件大小公约](00-总纲与数据模型.md) 的软上限,新增端点另立此文,不撑大原文件。
> 约定(分页/错误码/鉴权/异步任务)沿用 [工程5](工程5-API.md);实体严格用 [00 §4](00-总纲与数据模型.md)。

---

## 1. 在系统中的位置

这些端点是前端([工程2](工程2-交互与编辑器.md))与主编的接口。**落地优先复用 Hermes**(对齐 [工程8](工程8-HermesAgent复用方案.md)):
- 对话/生成可直接走 Hermes 的 **OpenAI 兼容 API Server**;
- 领域实体(想象/意图/方案/意见/讨论/札记/记忆/技能)的 CRUD 走**自建 MCP Server(PostgreSQL)**;
- 本文的 REST 端点是"业务封装层",内部转调上述二者。

---

## 2. 协作回路端点(内核1)

### 2.1 想象 Imagination
```
POST   /works/{id}/imaginations           # // 即时捕获(零摩擦):{raw_text, type?}
GET    /works/{id}/imaginations?status=    # 列表(游标分页)
PATCH  /imaginations/{id}                  # 改 status / scheduled_for
POST   /imaginations/{id}/structure        # 触发 LLM 结构化(异步 → task_id)
```
`POST` 仅要求 `raw_text` 存在即 201(status=captured),结构化异步进行。

### 2.2 北极星 AuthorIntent(与 Work 1:1)
```
GET    /works/{id}/author-intent
PUT    /works/{id}/author-intent           # 改硬红线 do_not_betray 须带 confirm_token
```

### 2.3 多方案 OptionSet
```
GET    /optionsets/{id}
POST   /optionsets/{id}/choose             # {chosen_option_id, choose_rationale}
                                           # → 回流 PreferenceSignal(内核2)
```

### 2.4 意见 FeedbackNote(意见→重做主交互)
```
POST   /segments/{id}/feedback             # {nl_critique, target_type}
                                           # → 解析 parsed_directive → 异步重做 → 新 Snapshot
GET    /feedback-notes?target_id=&chapter_id=
```
返回 `202 + task_id`;重做进度走 SSE(事件 `rewrite_complete` 见工程5)。

---

## 3. 主编端点(内核0)

### 3.1 对话(主交互入口)
```
POST   /works/{id}/chat                    # {message} → SSE 流:文本 + 可能的
                                           # discussion_thread_created / optionset_created /
                                           # citation(引用了哪些设定/记忆/伏笔)
```

### 3.2 讨论线程 DiscussionThread
```
GET    /works/{id}/discussion-threads?status=open
GET    /discussion-threads/{id}
POST   /discussion-threads/{id}/messages   # 你回一句(多轮收敛)
POST   /discussion-threads/{id}/resolve    # {decision, chosen_alternative?, human_overrode}
```
`concern_type` ∈ hard_conflict / soft_suggestion / clarifying_question;`evidence_refs` 指向冲突的 setting/foreshadow/intent。

### 3.3 主编札记 ProactiveInsight(主动引擎,后台低打扰)
```
GET    /works/{id}/proactive-insights?status=new&kind=
POST   /proactive-insights/{id}/ack        # acked
POST   /proactive-insights/{id}/act        # acted(可触发一个生成/修订任务)
POST   /proactive-insights/{id}/dismiss
POST   /works/{id}/proactive-review        # 手动触发全文体检(异步 → task_id);
                                           # 常态由 Hermes Cron 触发(对齐 工程8)
```

### 3.4 主编记忆 AgentMemory
```
GET    /works/{id}/agent-memory?namespace=episodic&q=
POST   /works/{id}/agent-memory            # 写(置信度<0.8 不入库,见 内核0 §3.3)
DELETE /agent-memory/{id}
```
`namespace` ∈ working/session/episodic/semantic/meta。

### 3.5 技能/流程 AgentSkill(自我优化,须人审批)
```
GET    /skills
GET    /skills?status=proposed             # 主编提议待批
POST   /skills/{id}/approve                # 人审批后生效(approved_by_human=true)
POST   /skills/{id}/retire
```
对齐 [内核0 §3.6](内核0-主编智能体.md):主编只能**提议**,关键改动须人批准;落地映射 Hermes `skill_manage` + `skills.write_approval=true`。

---

## 4. 安全与可靠性约束(对齐 工程9)

- 所有"执行"类端点(choose / feedback 重做 / insight act / skill approve)遵循 **Propose→Authorize→Execute**;高风险动作走 HITL 审批闸(且审批配置 Agent 不可改)。
- 写稿件相关一律经**写隔离 + 版本快照**([工程4](工程4-版本与回流.md) / [工程9](工程9-爆炸半径与故障隔离.md));禁破坏性覆盖。
- 异步任务带 `idempotency_key`,支持断点续跑;成本受 [工程3](工程3-LLM接入与成本.md) 预算与 [工程9](工程9-爆炸半径与故障隔离.md) 成本熔断约束。
- 全端点埋点对齐 [工程10](工程10-可观测日志与评测.md)(OTel,trace_id+work_id+session_id 贯穿)。

---

## 5. 开放问题

1. `/chat` 直接用 Hermes OpenAI 兼容 Server vs 自建封装层——MVP 前做 spike(对齐 工程8 开放问题)。
2. 多用户隔离:单进程多 Profile vs per-user 进程,影响这些端点的鉴权与配额。
