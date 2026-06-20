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

## 下一步:执行阶段1 B1(后端 /chat → run 驱动)
- **B1**:scribe `/chat`(现 `_hermes_complete` 裸补全)改成调 hermes `/v1/responses`(`tools:[{type:mcp,server_label:scribe}]` + `instructions`=主编人格+当前书 + `stream:true`)→ SSE 转发前端(新端点如 `/works/{w}/chat/stream`,集中带 API_SERVER_KEY)
- 蓝图全在阶段1 spec「实测结果」段,无需再实测基础路径
- 之后:B2 前端流式渲染 → B3 写工具审批(MCP elicitation) → 阶段2(写作走hermes)→ 阶段3(设置界面)→ 阶段4(退役旧件)

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
直接说:**「读 docs/superpowers/HANDOFF.md,从阶段1 B1 继续」**
