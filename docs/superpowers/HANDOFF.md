# Scribe 接力说明(新会话从这里续)

> 新会话第一步:读本文件 + 总纲 spec,然后从「下一步」续。

## 当前工程:scribe 深度集成新版 hermes(三任务整合)
把 scribe 的 AI 生成从"直连 doubao"迁移到"hermes 主编主笔"(设计文档核心愿景),并融合新版 hermes 能力。三个任务(①系统设置界面 ②scribe全走hermes ③新版优化)已整合为 4 阶段。

## 真相源 spec(必读)
- **总纲**:`docs/superpowers/specs/2026-06-20-scribe-hermes-integration-overview.md`(三任务整合+4阶段最优步骤)
- **阶段1-4**:`docs/superpowers/specs/2026-06-20-scribe-hermes-阶段{1,2,3,4}-*.md`
- 阶段1 spec 末尾有**实测蓝图**(responses body + SSE schema,B1/B2 照着写)

## 已完成(全部实测验证)
- **地基**:hermes 重置到 **v0.17.0** 干净实例(不串历史项目)+ `API_SERVER_KEY` 认证打通(commit `3be261e`)+ scribe MCP(28工具)已挂 hermes、主编 agentic 能流式用工具(实测 list_works 读真实数据)
- **spec 体系**:总纲+阶段1-4(`116fc7e`/`33ae3c6`/`a95b00a`)
- **阶段1 技术验证**:`/v1/responses` 用 `tools:[{"type":"mcp","server_label":"scribe"}]` 挂 scribe 工具,SSE 为 OpenAI Responses 标准(`response.created`/`output_item.added(function_call)`/`output_text.delta`)

## 下一步:执行阶段1 B3(写工具审批)+ B2 你亲眼验收
- **B2 已编码(前端工具调用折叠时间线)**:
  - 实测发现主编是**多步 agent**(一次问答连调 list_works→session_search→list_characters→search_book);hermes 原始 SSE **无 reasoning 事件**(doubao 不产出)、`function_call_output` 事件存在但**不带结果内容**——故 B2 只做「调用了什么」的时间线,不做思考气泡/结果折叠(无数据源)
  - `Conversation.tsx`:`ChatMsg.tools[]` 收集工具序列;`ToolTimeline` 折叠组件(回复气泡上方「🔍 主编查阅了 N 项资料 ▾」)+ `toolLabel()` 友好名映射(list_characters→查人物、search_book→检索原文、session_search→检索记忆…,抠出 args.query 当副标题);流式中 thinking 指示器实时显示「正在查人物「沈舟」…」
  - `tsc --noEmit` 绿。**待你亲眼验收**:浏览器开 `localhost:3310`(vite 绑 IPv6,用 localhost 不要 127.0.0.1)→ 进《雾港迷案》→ 问"沈舟的动机" → 看流式工具提示 + 折叠时间线
- **B3**:写工具审批(MCP elicitation → 审批卡);`tools` 项加 `require_approval:"always"`,审批 SSE schema 待 B3 实测
- **B1 已完成(编码 + 真机端到端实测通过)**:
  - 后端新端点 `POST /works/{work_id}/chat/stream`([api.py](../../scribe/scribe_mcp/api.py)):`_hermes_responses_events()` 调 hermes `/v1/responses`(`tools:[{type:mcp,server_label:scribe}]`+`instructions`=主编人格+当前书名+`stream:true`,集中带 `API_SERVER_KEY`)→ 翻成 scribe SSE(`tool`/`delta`/`done{content,thread_id}`/`error`)→ 持久化 discussion_thread
  - 前端 [api.ts](../../scribe/web-app/src/api.ts) 加 `streamChat()`;[Conversation.tsx](../../scribe/web-app/src/Conversation.tsx) `ChatSection.send()` 改流式:回复气泡逐片填充 + "🔍 正在调用 X…" 工具提示
  - 测试:`tests/test_api.py::test_chat_stream_forwards_and_persists` 绿;前端 `tsc --noEmit` 绿
  - **真机实测通过(2026-06-20)**:问《雾港迷案》"有哪些人物" → 主编实际调 `mcp_scribe_list_characters` → 流式答出真实人物(沈舟/陆沉,动机对得上设定,无瞎编)→ thread 落库 2 条消息。校准结论:`item.name`/`item.arguments` 字段名与代码假设一致;`model` 字段可传(hermes 接受 doubao 名)
- 之后:B3(写工具审批)→ 阶段2(写作走hermes)→ 阶段3(设置界面)→ 阶段4(退役旧件)

## 运行状态(当前)
- hermes gateway **:8642**(v0.17.0),家目录 `~/.hermes`,key 在 `~/.hermes/.env` 的 `API_SERVER_KEY`
- scribe 后端 **:3320**(scribe_mcp,直连 doubao 做写作 + 转发对话给 hermes;已带 key 自动读 .env)
- 前端 web-app **:3310**(vite)
- **你日常 hermes 完整备份**:`~/.hermes.backup-20260620-220301`(128会话/记忆星球/人格全在;恢复:停 gateway 后 `mv` 回)

## 关键事实/坑
- scribe MCP = `scribe_mcp/server.py`(28工具),hermes `config.yaml` 的 `mcp_servers.scribe` 已挂、enabled
- scribe **写作核心仍直连 doubao**(阶段2 才迁移);主编**对话**已连干净 hermes,但当前是**裸补全**(B1 才让它主动用工具)
- 新版 hermes 有 `hermes dashboard`(web 配置界面)——阶段3 设置界面对接它,不用手搓
- 路径含中文「写作 3.0」:macOS NFC/NFD + zsh 对中文绝对路径不稳,操作 frontend/web-app 用 python listdir 定位真实字节,或从已知 cwd 相对 ASCII 导航

## 新会话怎么续
直接说:**「读 docs/superpowers/HANDOFF.md,从阶段1 B2 继续」**
