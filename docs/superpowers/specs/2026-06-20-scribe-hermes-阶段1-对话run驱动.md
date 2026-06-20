# 阶段1 · 对话 run 驱动 Spec(主编对话经 hermes 用工具+流式+审批)

**目标**:scribe `/chat` 从"裸补全"改成"hermes Responses(带 scribe 工具+流式)";前端流式渲染主编**思考/工具调用/回复**,写工具弹**审批卡**。兑现"主编真懂你的书"。

## 架构
- **后端 `/chat` 改造**:收到消息 → `POST hermes /v1/responses`(input=消息, tools=scribe MCP 工具, instructions=主编人格+"当前在写《X》", stream=true)→ 流式消费 SSE → 经 scribe 自有 SSE 端点 `GET /works/{w}/chat/stream` 转发前端(集中带 `API_SERVER_KEY`、避开浏览器→:8642 CORS)。
- **前端 Conversation 改造**:发消息 → 订阅 scribe SSE → 实时渲染思考气泡 / "🔍 正在查沈舟的设定…"工具提示 / 回复流式 / 审批卡。
- **审批**:写工具命中 → 新版 hermes **MCP elicitation** → 转审批事件 → 前端卡 → 批准 → 回传 hermes 解决。

## 事件映射(hermes Responses SSE → 前端)
| hermes 事件 | 前端 |
|---|---|
| reasoning / thinking | 思考气泡(灰) |
| function_call | 工具调用提示 |
| function_call_output | 内部(可折叠) |
| output_text.delta | 回复流式打字 |
| elicitation / approval_required | 审批卡(批准/拒绝) |

## 工具范围(安全)
只读(`search_book`/`list_settings`/`get_chapter`/`list_characters`/`list_open_foreshadows`…)自动放行;写(`save_chapter`/`upsert_setting`/`save_snapshot`…)走审批卡。

## 子切片(实施顺序)
- **B1**:后端 `/chat`→Responses+SSE 转发(只读工具+流式回复),前端先纯文本流式
- **B2**:前端流式渲染(思考/工具提示/回复气泡)
- **B3**:写工具审批(MCP elicitation → 审批卡)

## 待实测对齐(实现前先写脚本实测,不靠猜)
1. hermes `/v1/responses` body 怎么挂 scribe MCP toolset(`tools` 字段格式 / 是否用 `mcp_servers` 引用)
2. Responses SSE 事件**精确 schema**(reasoning/function_call/output_text/elicitation 的字段名)
3. MCP elicitation 审批的请求/响应 schema(怎么暂停、怎么回传批准)

## 验收
- 主编对话**流式**显示思考+工具调用;回复基于真实查到的书(不瞎编)
- 写操作弹审批卡,批准后才执行;只读自动放行
- 端到端实测:问"沈舟的动机" → 看到主编 search/list_characters → 给出基于设定的回答
