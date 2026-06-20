# Scribe 深度集成新版 Hermes · 总纲 Spec(三任务整合)

**日期**:2026-06-20  **性质**:架构集成工程。把三个任务——①系统设置界面 ②scribe 全走 hermes ③新版升级优化——整合为一条主线:**让 scribe 真正深度集成新版 hermes(v0.17.0),兑现设计文档"AI 全程由主编主笔、hermes 作运行底座"的核心愿景**。

## 0. 一句话
旧实现 scribe 直连 doubao 自己做 AI(spec §1 点名的"绕过 Hermes"根因);本工程把 AI 生成层迁移到 hermes 主编(用 scribe 工具/技能/插件),并融合新版 hermes 的 dashboard/审批/skills/cron。

## 1. 三任务 = 一件事的三个面
- **任务2(全走 hermes)= 核心主线**:写作生成(续写/改写/质量/摘取)由主编(hermes AIAgent)做,不再 scribe 直连 doubao。
- **任务3(新版优化)= 贯穿手段**:用新版 hermes 的 MCP elicitation 审批、skills、cron、dashboard、Responses API。
- **任务1(设置界面)= 相对独立**:因新版有 web dashboard,从"手搓配置"简化为"对接 dashboard + config API"。

## 2. 已就绪的地基(阶段0,已完成)
- ✅ hermes 重置到 v0.17.0,干净实例(不串历史项目),API_SERVER_KEY 认证打通(commit 3be261e)
- ✅ scribe MCP(28 工具)已挂 hermes、enabled;主编 agentic 能调 scribe 工具(已实测 list_works)
- ✅ scribe 写作核心当前直连 doubao(待迁移),主编对话已连干净 hermes

## 3. 最优步骤(按依赖+价值排序)
| 阶段 | 内容 | 对应任务 | 依赖 |
|---|---|---|---|
| 0 地基 | hermes 重置+认证+MCP 挂载 | — | ✅已做 |
| **1 对话 run 驱动** | /chat→hermes Responses(工具+流式)+前端流式+写工具审批(MCP elicitation) | 2切片1 + 3 | 0 |
| 2 写作走 hermes | 写章流程 SKILL + 品味/连贯插件 + 前端写作 run 驱动 | 2核心 + 3 | 1 |
| 3 设置界面 | 对接 hermes dashboard + scribe 配置 + config API 统一管理 | 1 + 3 | 0(可与2并行) |
| 4 记忆/技能/cron 全走 hermes | scribe 自造退役→hermes 原生 | 2 + 3 | 2 |

## 4. 各阶段独立 spec + plan
每阶段一份 spec(设计)→ 一份 plan(TDD 实施)→ 执行 → 验证。本总纲是路线;各阶段 spec 见 `2026-06-20-scribe-hermes-阶段N-*.md`。

## 5. 工程量与诚实边界
- **数周–数月**;逐阶段推进,每阶段可见可验证、可独立交付。
- 关键不确定点(新版 Responses API body/SSE schema、MCP elicitation 审批 schema)在各阶段 spec 标注"实现时实测对齐",先实测再编码。
- 不推倒重来:scribe 领域逻辑(DB/schema/编辑器/版本)保留;迁移的是"AI 生成怎么发生"(从直连 doubao → 经 hermes 主编)。

## 6. 验收(总)
- 阶段1:主编对话能流式用 scribe 工具看书,写操作弹审批
- 阶段2:续写/改写由主编(经 hermes)产出,而非 scribe 直连 doubao
- 阶段3:一个设置界面管 scribe + hermes 配置
- 阶段4:agent_memory/skills/proactive 退役,主编用 hermes 原生能力
