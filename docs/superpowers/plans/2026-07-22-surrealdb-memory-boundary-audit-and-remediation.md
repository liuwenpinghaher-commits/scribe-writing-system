# scribe3 底层存储 · 限知 · 写路径 · 记忆边界 · 彻底审查与改造方案

> **For agentic workers:** 本文是审查结论 + 分阶段改造方案，不是从零实现 B/C/D 枢纽的旧总纲。实现时优先对照「新主轴」与「P0 接线」；禁止按 2026-06 过期诊断重开已完成工单。  
> **日期：** 2026-07-22  
> **模式：** 专家团 Review only + Planner（未改代码、未跑全量 e2e）  
> **关联：** 会话结论「SurrealDB 不错、GBrain 不换库」；`AGENTIC_BOUNDARY_DECISION.md`；`设计文档/2026-07-22-对话驱动写入-禁表单直填-决策与改造方案.md`；`docs/改进方案/00-系统改进方案总纲.md`（历史）

---

## 0. 一句话总判

| 问 | 答 |
|----|-----|
| SurrealDB 选错了吗？ | **没有。** 图+向量+文档+一书一库仍匹配产品。 |
| 该换成 GBrain 吗？ | **否。** GBrain 是 Agent 过程记忆层，不是故事正典库；仓内已有 `memory_fabric` 对齐同构能力。 |
| 最大问题是什么？ | **(1) 限知结构闭环未接线 (2) 对话写决策未落地 (3) 半迁移/双模型/门控漏网 (4) 文档与旧枢纽排期过期。** |
| 旧 A–H 枢纽还要整包重做吗？ | **不要。** 约 70–85% 已落地；只清残留 + 换新主轴。 |

**新主轴（替换 `D→B→C` 全量施工）：**

```text
门控硬化 → 结构写 MCP 补齐 → UI 灭表单 → see_event/effects 接线
         → hybrid 时间门 → 半迁移收口 → app 巨石拆分（并行）
         → 记忆织物条件开启 → 暴露前安全（条件触发）
```

---

## 1. 模块职责与成熟度（现状）

| 模块 | 职责 | 成熟度 | 一句话 |
|------|------|--------|--------|
| **SurrealDB / `store/`** | 一书一 DB 正典 + 迁移 + 单点写 | 高基建 / 中语义 | 图边、多路向量、事务拼装已有；生产语义半开 |
| **本体 `ontology.py`** | 内存 World 鸭子模型 | 中 | 投影兼容好；能力面小于 Store |
| **限知 `knowledge.py`** | `project_frame` / `see_event` / 反讽 | 读路径高 / 写派生断 | 投影真库可用；`see_event` 生产零调用 |
| **ingest** | 定稿回写账本 | 中高 | 幂等 purge 成熟；effects/see_event 未产 |
| **召回 `store/recall.py`** | semantic / hybrid / graph / material | 中高 | Graph RAG 已有；hybrid 时间门半残 |
| **MCP `mcp.py`** | `s3_*` + `commit_if_approved` | 中 | 门控设计良；漏登 + REST 并行写 |
| **REST `api/app_impl.py`** | 全 HTTP 面 | 债重 | ~9.4k 行巨石；表单直写仍活 |
| **前端写作台** | 检视/对话/表单 | 与决策冲突 | 失焦保存、CodexNew、putIntent 仍在 |
| **memory_fabric** | 经验记忆（非正典） | 设计良 / 默认关 | 正确替代 GBrain 的仓内方案 |
| **Hermes** | 主编网关 + 可选 memory | 纪律依赖 | SOUL 禁剧情进平台 memory；需守住 |
| **GBrain（外部）** | 通用 agent brain | **不引入主路径** | 类别错位 |

---

## 2. 选型落差（相对「图+向量+文档+实时」）

| 卖点 | 目标 | 现状 | 落差 |
|------|------|------|------|
| 图 | Event 图 + 遍历 + Graph RAG | 边可写可读 + `graph_recall` | **ingest 不产 causes；see_event 未自动** |
| 向量 | 原生 HNSW | 多表 HNSW + EF 形态已修 | 章向量截断 200 字 |
| 文档 | SCHEMAFULL 本体 | 大体有 | 半字段 entity_link 等 |
| 实时 | LIVE→SSE | 可用 | live 凭证硬编码；配额失效 |
| Hybrid | BM25+向量 | material/memory 真 FTS；命题 hybrid 关键词全表扫 | 命题侧假 Hybrid |
| 多租户 | NS/DB + 权限 | 内容分库 ✅ | 身份仍 root |
| 限知 | 结构自维护账本 | 投影/注入 ✅ | **结构扩边 ❌** |
| 写门控 | 对话审批唯一作者路径 | MCP 有门控 | **REST/表单并行；工具缺口** |

相对 6 月底「只兑现向量」：**已进阶到「向量深、图半用、Hybrid 半套、实时薄、权限无」**。下一刀是**接线与收口**，不是换库。

---

## 3. 问题清单（去重合并 · 按严重度）

### P0 · 正确性 / 产品铁律

| ID | 问题 | 证据锚点 | 影响 |
|----|------|----------|------|
| **P0-SEE** | 生产路径从不调用 `see_event`；ingest 不写 `effects` → `causes` 空 | `knowledge.py:see_event`；`ingest.py` add_event 无 effects；grep 生产零调用 | 限知从「结构保证」退回「LLM 概率」 |
| **P0-HYBRID-TIME** | `hybrid_recall` 宣称 chapter 门，向量路 `semantic_recall` 无 `valid_from` 过滤 | `store/recall.py:31-60` | 可召回未来命题污染联查/写作 |
| **P0-PREF-GATE** | `s3_author_pref_add` 调 `commit_if_approved` 但不在 `WRITE_GATED` → 拒绝仍写 | `mcp.py:73-84,1307-1314` | elicitation fail-closed 失效 |
| **P0-REST-UI** | REST + 前端表单完整并行写；与 2026-07-22「禁表单直填」冲突 | `app_impl` POST/PATCH；`CodexNew`/`putIntent`/失焦保存 | 决策乙名存实亡；审计链可绕开 |
| **P0-MCP-GAP** | 无 volume/chapter_meta/chapter_plan 等结构写工具 → 灭表单后功能空洞 | `mcp.py` 工具列表；对话写设计文档 §5 | PR-A 只读墙会空转 |

### P1 · 高优先结构债

| ID | 问题 | 锚点 |
|----|------|------|
| **P1-EVENT-TX** | `add_event` 多 `_execute_write` 非事务，可半落库 | `store/events.py:8-48` |
| **P1-MULTI-WITNESS** | `participants` dict 同 role 覆盖，多目击者丢失 | `ontology.Event`；`events_at` 重建 |
| **P1-FRAME-SECRET** | `s3_project_frame` 明文 secret vs 生成路径打码 | `mcp.py` vs `_frame_block` |
| **P1-GRAPH-UNTIL** | `graph()` 忽略 `until_chapter` | `store/structure.py` |
| **P1-ENTITY-LINK** | `entity_link` 半迁移无写方 | `026_record_links.surql`；`graph_recall` 注释 |
| **P1-DUAL-REL** | `character_relation` 与 `entity_relation` 双轨 | `020` / `085` |
| **P1-CLEANUP** | 删角色清理边不全 | `connection._cleanup_record_refs` |
| **P1-LIVE** | `live.py` root 硬编码；`/live` 计数在 return 后失效 | `live.py`；`app_impl` live handler |
| **P1-FOLD** | `s3_fold_voice_flags` 旁路 `commit_if_approved` | `mcp.py` |
| **P1-INGEST-GATE** | `s3_ingest_chapter` 免批可改正典账本 | 设计有意但风险高 |
| **P1-PROPOSAL** | 批量 WriteProposal 未实现 | 边界决策 vs 代码 |
| **P1-LOAD-K** | `load_knowledge` 全表拉边，热路径不规模 | `facts_knowledge.load_knowledge` |
| **P1-PROP-FTS** | 命题 hybrid 关键词全表扫无 FTS | `core_preamble._keyword_search_propositions` |

### P2 · 中等

| ID | 问题 |
|----|------|
| **P2-CH-EMB** | 章向量仅 title+prose[:200] |
| **P2-READER-STR** | `reader_knows.proposition` 仍 string |
| **P2-MIG-DEAD** | 删字段不删索引；017 EVENT 幽灵；缺 090 编号 |
| **P2-SCHEMA-FAIL** | `apply_schema` 失败后继续后续迁移 |
| **P2-FABRIC** | memory fabric 默认关；正典压制未完备；文档注释过期 |
| **P2-HERMES-MEM** | 平台 memory 若记剧情 → 双真相 |
| **P2-GRANT-FSTR** | `grant_public` f-string record 字面量 |
| **P2-APP-MONO** | `app_impl.py` ~9400 行；Phase 1 路由拆滞后 |
| **P2-DB-AUTH** | 默认 root；025 `changeme` 非生产就绪 |
| **P2-POLARITY** | 误信 `polarity=False` 无生产写入口 |

### P3 · 卫生

| ID | 问题 |
|----|------|
| 文档 06/B/E 严重过期 | 勿按「Event 蒸发 / 仅 1 索引」排期 |
| CURRENT 仍写 `store.py` | 实际为 `store/` 包 |
| certainty / preconditions 行为消费疑似死 | 用或删 |
| MCP 单文件过大 | 可选按域拆 |

---

## 4. 真相源边界（宪法草案）

```text
冲突裁决：Surreal 正典 > memory_item 经验记忆 > 会话过程 > 模型口述

必须 Surreal（一书一 db）：
  character/place/… · proposition · event · knows/reader_knows
  promise · relation · chapter 正文 · intent · 伏笔母题 …

可过程侧（非正典）：
  memory_item（working/episodic/…）· USER.md 跨书风格
  未接受的正文 proposal 缓冲 · 会话 todo

禁止：
  Hermes FTS / GBrain vault / 会话笔记 存 fact·event·knows·promise·秘密
  权威主张静默进 experience（须 pending_authority_claim 或 gated s3_add_fact）
```

**GBrain：** 主路径 **不引入**。若实验，仅只读研究素材侧车、默认 off、零写正典。

**仓内等价物：** `078_memory_fabric` + `scribe3-memory` provider + materials 召回。

---

## 5. 改造方案（分阶段 · 可执行）

### 阶段 0 · 冻结与文档纠偏（0.5–1 天）

**目标：** 停止按过期诊断施工。

- [ ] 在 `CURRENT_ARCHITECTURE.md` 标注：`store/` 包；A–H 大部分已做；新主轴指向本文  
- [ ] 给 `06-SurrealDB…` / B 枢纽文首加 **「2026-07-22 现状覆盖」** 警告（不必全文重写）  
- [ ] 冻结「禁止重开」清单：D 词汇表总包、B 从图零建、从零 Hybrid、DEFINE EVENT 聚合  

**验收：** 新人读 CURRENT 不会再「换 GBrain / 重做图库」。

---

### 阶段 1 · 门控硬化（1–2 天）· **立刻**

| 任务 | 做法 | 验收 |
|------|------|------|
| 1.1 `s3_author_pref_add` ∈ `WRITE_GATED` | 集合 + EXPECTED 镜像测 | 拒绝后 USER.md 不变 |
| 1.2 不变量：凡 `commit_if_approved("s3_*")` 的 name ∈ `WRITE_GATED` | AST/注册表扫描测试 | 漏登 CI 红 |
| 1.3 `s3_fold_voice_flags` 走统一门控 | 同 commit_if_approved | status 契约一致 |
| 1.4 （可选）`commit_if_approved` 对未知名 + `accepted=False` fail-closed | 防御未来 | 单测 |

**命令：** `scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py scribe3/tests/test_author_prefs.py -q`

---

### 阶段 2 · 对话写可走通（1–2 周）· **产品最高优先**

对齐 `2026-07-22-对话驱动写入…`：

| 批次 | 内容 | 验收 |
|------|------|------|
| **2A 工具先** | MCP：`s3_add_volume` / `s3_patch_volume` / `s3_patch_chapter_meta` / `s3_patch_chapter_plan`（synopsis/beats）等；一律 WRITE_GATED | test_mcp 绿；declined/error 不假绿 |
| **2B UI 只读** | feature flag 默认开：Codex/北极星/大纲/节拍 **只读 +「让主编处理」种子** | 组件测：无失焦直写 |
| **2C 审批体验** | 复用 Hermes approval → 再收敛批量 WriteProposal | 多 op 可一批或文档 defer |
| **2D REST 后门** | `SCRIBE3_EMERGENCY_REST_WRITE` 默认关；测试 fixture 显式开 + 审计 | 默认 POST /characters → 403 |
| **2E ingest 策略** | 评估 write profile 是否挂 `s3_ingest_chapter`；倾向 app 定稿后调 | 无交互上下文不能静默改账本 |

**关键路径：** 工具先于 UI 锁死，避免「只读墙空转」。

**验收：** 对话「登记角色+关系+北极星+一章大纲」→ 审批 → 只读面可见；**零业务表单**。

---

### 阶段 3 · 限知结构闭环（与阶段 2 可并行，1 周）· **正确性最高优先**

| 任务 | 做法 | 验收 |
|------|------|------|
| 3.1 ingest 写 `effects` + `causes` | did/关键命题 → Event.effects | 真库有 causes 边 |
| 3.2 接线 `see_event` | `add_event` 后或 `apply_delta` 末尾批量；与 LLM `seen_by` 去重幂等（结构优先） | **不手调** see_event 的集成测绿 |
| 3.3 `add_event` 事务 | `transaction()` 或单条 BEGIN…COMMIT | 中断无半事件 |
| 3.4 修 hybrid 时间门 | 向量结果按 valid_from/to 再滤；或 semantic 接 chapter | `valid_from=100` 不得出现在 ch=5 |
| 3.5 multi-WITNESS | participants 改为 list 或 multi-value；events_at 禁止 dict 压扁 | 双目击者皆得 knows |
| 3.6 `graph()` 对齐 until | 与 project_frame 同谓词 | 遗忘边不显示 |
| 3.7 project_frame secret 策略 | 拆 `s3_project_frame_reveal` 或统一打码 | 限知续写工具面不吐 secret 明文 |

**命令示例：**

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_ontology.py \
  scribe3/tests/test_integration.py \
  scribe3/tests/test_ingest*.py \
  scribe3/tests/test_mcp.py -q
# 新增：test_see_event_after_ingest_no_manual_call
# 新增：test_hybrid_recall_filters_future_facts
```

---

### 阶段 4 · 半迁移与图收口（小 PR 并行，3–5 天）

| 任务 | 二选一或明确放弃 | 验收 |
|------|------------------|------|
| entity_link | 全量回填并切换 **或** down-migrate 删字段 | 无幽灵字段；graph subject 语义钉死 |
| 关系双轨 | 文档定「角色关系用 character_relation；跨类 entity_relation」+ UI 只读对应 | 不双写同一语义 |
| reader_knows RecordLink | 升 `record<proposition>` | orphan 扫描可关联 |
| 死索引/017 | 删或接读 | schema 干净 |
| cleanup_refs | 扩 character_relation / entity_relation / causes | 删角色无孤儿 |
| grant_public | RecordID 绑参 | 无 f-string record |

---

### 阶段 5 · 性能与可维护（持续）

| 任务 | 说明 |
|------|------|
| `load_knowledge_for(knower, chapter)` | 下推 WHERE；project_frame 默认走 |
| 命题 FULLTEXT | 对齐 material 070（jieba tokens + BM25） |
| 章向量策略 | 分段/摘要，超越 200 字 |
| `app_impl` → `api/routes_*.py` | **搬迁 PR 禁止改行为**；先 chapters/codex/chat |
| MCP 按域拆（可选） | 注册表测防漂移 |

---

### 阶段 6 · 记忆织物（条件开启）

| 前置 | 动作 |
|------|------|
| 正典压制可测 | 开 `SCRIBE3_MEMORY_FABRIC_V1` |
| Hermes | `memory.provider=scribe3-memory` 或关剧情持久化；守 SOUL |
| GBrain | 仍不引入 |
| 文档 | 刷新 `memory_capture` 头注释 |

**验收：** fabric 关=写作字节等价；开=无 secret 明文泄漏；无 fact 双写。

---

### 阶段 7 · 安全暴露集（仅部署意图触发）

- live 凭证走 env  
- `/live` 配额绑流生命周期  
- 非 root + token + CORS + 限流  
- 禁止生产 `changeme` / 默认 root  

本地单用户：**不阻塞**阶段 1–3。

---

## 6. 依赖 DAG（更新）

```text
[0 文档冻结]
    │
    ├─► [1 门控硬化] ─────────────────────────────┐
    │                                              │
    ├─► [3 限知闭环] ──► [4 半迁移收口] ──► [5 性能] │
    │                                              │
    └─► [2A MCP 结构工具] ──► [2B UI 只读] ──► [2C/D/E]
                                    │
                                    ▼
                            [真书 craft-first e2e]
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            [6 memory fabric 条件开]         [7 暴露安全]
```

**禁止并行冲突：** 2B 不得早于 2A；3 与 2 可并行不同文件集。

---

## 7. 明确不做 / 延后

| 项 | 原因 |
|----|------|
| 换 SurrealDB → GBrain/Postgres 主库 | 类别错位 + 重写成本；选型未错 |
| 重开 A–H 总包 | 70–85% 已做 |
| DEFINE EVENT 书级聚合 | 底座对表 + 017 幽灵 |
| Hermes 大版本盲升绑对话写 | 独立窗口 |
| 真多用户 PERMISSIONS 本地优先 | 条件触发 |
| 反讽主动进 prompt 产品化 | P2，限知闭环后 |

---

## 8. 验收总清单（合并）

```text
□ test_mcp + WRITE_GATED 不变量
□ author_pref 拒绝不写 USER.md
□ see_event：ingest 后真库目击者有 knows（不手调）
□ hybrid_recall 不含未来命题
□ 对话建书：角色/关系/intent/章 plan 无业务表单
□ REST 紧急开关默认关
□ craft-first GATE + 禁止 REST 灌库假绿
□ fabric 关/开 secret 测
□ SOUL：Hermes memory 无 fact/promise
□ live 用 env 凭证（暴露前）
```

---

## 9. 风险

| 风险 | 缓解 |
|------|------|
| 只读 UI 无工具 → 作者失能 | 2A 先于 2B |
| see_event 与 LLM seen_by 双发 | 幂等 RELATE / 唯一 (knower,prop,since) |
| multi-WITNESS 改 ontology 炸面 | 兼容读旧 dict 一版 |
| REST 测试依赖 | fixture 开 emergency |
| 文档过期导致重复施工 | 阶段 0 冻结 |
| app 拆分混改行为 | 纯搬迁 PR |

---

## 10. 建议执行顺序（给下一任）

1. **本周：** 阶段 1 门控 + 阶段 3.4 hybrid 时间门（小而硬）  
2. **下周起：** 阶段 2A 结构 MCP → 2B 灭表单  
3. **并行：** 阶段 3.1–3.3 see_event 闭环  
4. **穿插小 PR：** 阶段 4 半迁移  
5. **不排：** GBrain POC、换库评估（除非有新硬约束）

---

## 专家团结果摘要

- **模式：** Review only + Planner  
- **启用角色：** Lead + 4× explore Reviewer（Store / 限知 / MCP·记忆 / 改进方案债务）  
- **验证：** 静态 codegraph + 源码/迁移/设计文档对照；**未**宣称全量 pytest/e2e 已跑  
- **产物：** 本文 `docs/superpowers/plans/2026-07-22-surrealdb-memory-boundary-audit-and-remediation.md`
