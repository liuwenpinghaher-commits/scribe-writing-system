# scribe3 用对 Hermes v0.17 平台能力 · 设计

> 设计日期:2026-06-23(修订:从"用上"改为"用对")
> 目标:让 scribe3 主编用上 Hermes v0.17 平台能力——但**用在最优场景**,而非为用而用。

## 设计原则:用对 > 用上

原始诉求是"Hermes v0.17 能力全用上"。但 spike 后判断:**有些能力用在某场景是过度工程**。本设计按"用对工具"重构:
- 确定性后台任务(ingest)→ scribe3 后端 `asyncio`(快、便宜、可靠),**不**用 delegate_task(spawn 一个完整 agent 跑确定性流程是杀鸡用牛刀)。
- 需要多步自主判断的后台任务(综合体检报告)→ `delegate_task(background)`(用得其所)。
- 动态 context → 关键提醒预注入 + 详情按 agentic 主编自主查(不全量灌)。

## 背景:Spike 实测结论

**版本陷阱**:Hermes editable 安装,`dist-info` 写 0.11.0 但 binary 实际 **v0.17.0**,真实源码 `~/.hermes/hermes-agent/`。

| 能力 | 结论 | 依据 |
|---|---|---|
| `delegate_task(background)` | ✅ 工具面含 | `toolsets.py:59`;`delegation.inherit_mcp_toolsets:true` → 后台 subagent 继承 scribe3 MCP |
| `skill_manage(patch)` | ✅ 工具面含 | `toolsets.py:44`;SKILL.md 已有自进化段 |
| gateway hooks | ⚠️ responses 不触发 | `agent:start` 只在 `gateway/run.py` IM 平台处理 emit;`run_agent.py`(处理 `/v1/responses`)不 emit → 用不上 |

## 架构(四块,各用对工具)

```
主编 agent(:8643 Responses,toolsets=[hermes-cli]+scribe3 MCP)
  │
  ├─【B】写完反思 → skill_manage(action="patch") 沉淀修法进 SKILL.md      [Hermes 原生]
  │
  ├─【D】对话/写作前 → _editor_system 预注入「开着的伏笔 + 本章该收的承诺」 [scribe3 工程]
  │        强提醒(防忘/漏接);母题细节/历史事件等详情让主编按需调工具查
  │
  └─ 写一章 → s3_save_chapter / 前端接受草稿 → REST save-chapter
        │
        ├─【A】后端 asyncio.create_task(ingest)  ← 确定性后台,不阻塞       [scribe3 工程]
        │        读定稿→LLM 抽 learned/did→apply_delta 落库(客观回写)
        │
        └─【C】主编 delegate_task(background=true,"对第N章综合体检")        [Hermes 原生]
                 后台 subagent 自主跑 QC+discipline+leak+一致性+causal,综合写报告
```

## 组件

### 【A】ingest 后台自动化 — scribe3 后端 asyncio(确定性)

**为何不用 delegate_task**:ingest = 读正文 + 一次 LLM 抽取 + `apply_delta`,确定性单步。用 delegate_task spawn 一个 agent 多轮跑它,贵几倍且可能跑偏。后端 asyncio 一次 LLM 抽取直接落库,最优。

**改动**:
- `scribe3/ingest.py`:抽出 `ingest_chapter(store, seq, complete_fn) -> dict`(读定稿→`build_knowledge_extract_prompt`→`hermes_complete`→`parse_knowledge_delta`→`apply_delta`),返回 `{applied, summary}`。纯函数核心(complete_fn 可注入,单测用 fake)。
- `scribe3/app.py` `save-chapter` 端点:落库后 `asyncio.create_task(_bg_ingest(work, seq))` 后台跑,**立即返回**存稿结果(加 `"ingesting": true` 字段)。`_bg_ingest` 捕获异常记日志,不影响主流程。
- ingest 是客观回写(反映已定稿正文,非创作虚构),后端直接落库,不经 elicitation。
- `s3_ingest_chapter`(MCP,主编手动 ingest 用)从 `WRITE_GATED` 移出,改为直接落库(与后端一致:ingest 客观,不待批)。`apply_delta` 只写 knowledge edges,不建虚构设定。

**测试**:`ingest_chapter` 纯函数(fake complete_fn,断言 applied 数);save-chapter 触发后台任务(mock asyncio,断言 create_task 被调);`s3_ingest_chapter` 不在 `WRITE_GATED`。

### 【B】主编自进化 — `skill_manage(action="patch")`[Hermes 原生]

**改动**:
- `scribe-novel-v2` SKILL.md "写一章的环"末尾加自检触发:"**章成后自检**:本章有没有摸出可复用修法(某类坑的解/腔调立法/QC 序列)?有 → `skill_manage(action='patch')` 追加进对应段。只沉淀流程/craft,不沉淀剧情事实(事实进 SurrealDB)。"
- 强化自进化段:写清 patch 的目标段(anchor)、安全规矩(小补丁非重写、受 skills_guard 扫描、git 可回滚)。
- 验证 `skill_manage` 能 patch `scribe-novel-v2`(过 skills_guard)——集成验证。

**测试**:集成验证 patch 一条测试修法成功 + git diff 可见(手动/脚本)。

### 【C】后台综合体检 — `delegate_task(background=true)`[Hermes 原生,用得其所]

**为何用 delegate_task**:综合体检需要**多步自主判断**——跑 QC、discipline、leak、一致性、causal 五种检查,综合权衡哪些是真问题、写成报告。这正是 agent 多步循环的价值,适合委派。

**改动**:
- `scribe-novel-v2` SKILL.md "写一章的环"加:存稿后(ingest 已后台自动)可 `delegate_task(background=true, prompt="对第N章做综合体检:依次 s3_qc_chapter / s3_discipline_check / s3_find_leaks / s3_causal_complete,综合判断哪些是真问题(别堆噪声),写一份精炼体检报告")`,主编立刻继续,不等。
- 后台 subagent 继承 scribe3 MCP(`inherit_mcp_toolsets:true`),`max_async_children:3` 限并发。
- 报告产出:subagent 的最终文本(主编下次可取,或写入某 work 笔记)。

**测试**:集成验证(手动)——delegate 一个后台体检,确认 subagent 跑完多工具产出报告。无单测(纯 Hermes agent 行为)。

### 【D】关键提醒预注入 + 详情按需查 — 增强 `_editor_system`

**为何不全量预注入**:scribe3 主编是 agentic 的(能自己调 s3_list_promises/s3_list_motifs)。全量灌伏笔/事件/母题 → instructions 膨胀,且这次对话未必用得上。**只预注入易忘的关键提醒**,详情让 agent 自主查。

**改动** `scribe3/app.py` `_editor_system`(或辅助 `_editor_reminders`),在现有(北极星+角色+设定)基础上只追加**强提醒**:
- **开着的伏笔**:`store.open_promises()` → "【⚠ 开着的承诺线·勿忘】埋于第X章:…(适时推进/回收,别让它凭空消失)"
- **本章该收的承诺**(`chat/write` 通路,知道当前章号时):open_promises 里 setup 已久或标记该收的 → "【本章宜回收】…"

母题细节、历史事件、角色全貌等**不预注入**——instructions 末尾保留现有的"你能调 s3_list_motifs/s3_get_chapter/s3_semantic_recall 等按需查"指引。

**测试**:`_editor_system` 注入含开着伏笔提醒(seed open_promise 后);无伏笔时不崩、不出空提醒段;母题/事件**不**在预注入里(断言 instructions 不含全量母题——保持按需查)。

## 关键决策记录

1. **用对 > 用上**:ingest(确定性)走 asyncio,不用 delegate_task;delegate_task 留给综合体检(多步自主)。
2. **ingest 客观回写,不待批**:后端 asyncio 自动 + MCP 工具移出 WRITE_GATED;创作虚构(add_fact/add_event)仍待批。
3. **不用 gateway hooks**:responses 通路不触发;动态 context 用 #D 的 instructions 提醒。
4. **#D 只预注入关键提醒**:agentic 主编详情自主查,不全量灌。

## 测试策略(TDD)

| 测试 | 断言 |
|---|---|
| `test_ingest.py::test_ingest_chapter_pure` | `ingest_chapter` fake complete_fn → 返回 applied 数,apply_delta 被调 |
| `test_app.py::test_save_chapter_triggers_bg_ingest` | save-chapter 落库后调 `asyncio.create_task`(mock 断言),响应含 `ingesting:true` |
| `test_mcp.py::test_ingest_not_gated` | `s3_ingest_chapter` 不在 WRITE_GATED;add_fact/add_event 仍在 |
| `test_app.py::test_editor_reminds_open_promises` | seed open_promise 后,`_editor_system` 含伏笔提醒 |
| `test_app.py::test_editor_no_full_motif_dump` | `_editor_system` 不全量灌母题(保持按需查),无数据时不崩 |
| (集成,手动) | skill_manage patch SKILL.md;delegate_task 后台体检产出报告 |

## YAGNI(不做)

- 不做前端"ingest 中/体检中"状态轮询(后端后台跑,前端暂不显示;可后加)。
- 不强制每章 patch / 每章体检(主编自判)。
- 不碰 IM 平台 hooks(scribe3 无 IM 入口)。
- #D 只预注入伏笔提醒;母题细节/角色声音库/Progressions 等留按需查或后续。

## 影响面 / 风险

- **ingest 移出 WRITE_GATED 是审批边界变更**:确认 `apply_delta` 只写 knowledge edges(客观),不建虚构设定(已核 ingest.py)。drift-guard 的 EXPECTED_WRITE_GATED 需同步移除 ingest。
- save-chapter 后台 asyncio:FastAPI 已 async,`create_task` 安全;异常需捕获记日志,不影响存稿响应。
- `delegate_task(background)` 受 `max_async_children:3` 限,有 runaway 上限。
- #D instructions 只加伏笔提醒,增量小,无窗口溢出。
- skill_manage patch 受 skills_guard 扫描,破坏性 patch 被拦。
