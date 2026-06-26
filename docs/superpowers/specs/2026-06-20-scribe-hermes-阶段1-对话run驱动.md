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


---

## ✅ 实测结果(2026-06-20,已验证,B1/B2 照此编码)

**端点**:`POST http://127.0.0.1:8642/v1/responses`,头 `Authorization: Bearer $API_SERVER_KEY`。

**请求体(挂 scribe 工具 + 流式)**:
```json
{
  "input": "用户消息",
  "instructions": "主编人格 + 当前在写《X》",
  "stream": true,
  "tools": [{"type": "mcp", "server_label": "scribe"}]
}
```
→ `server_label:"scribe"` 直接引用 config.yaml 里挂的 scribe MCP,主编自动发现全部 28 工具。

**SSE 事件流(OpenAI Responses 标准)**:
| event | 含义 | 前端渲染(B2) |
|---|---|---|
| `response.created` | run 开始 | — |
| `response.output_item.added` (item.type=`function_call`) | 工具调用(name=`mcp_scribe_<tool>`, arguments) | "🔍 正在调用 list_works…" |
| `response.output_item.added` (item.type=`function_call_output`) | 工具结果(output) | 内部/可折叠 |
| `response.output_text.delta` (delta) | 回复流式片段 | 流式打字 |
| `response.output_item.done` / `response.completed` | 完成 | 收尾 |

**实测验证**:主编自动调 `mcp_scribe_list_works`(args `{"owner_id":"u1"}`)→ 拿到真实作品(雾港迷案等)→ 流式回复列表。**端到端通,无需再实测基础路径。**

**B3 审批(待 B3 时实测)**:`tools` 项可加 `"require_approval":"always"` 触发 elicitation;具体审批 SSE 事件 B3 阶段实测。

---

## ✅ B1 已实现 + 真机端到端实测(2026-06-20)

**后端**(`scribe/scribe_mcp/api.py`):
- `_hermes_responses_events(message, instructions, model)`:`httpx.stream` POST `{HERMES}/responses`,body=上面实测蓝图;逐条解析 SSE `data:` JSON 后 yield。
- `POST /works/{work_id}/chat/stream`:校验 owner+归属 → `instructions`=`_CHIEF_SYSTEM`+当前书名+"调 scribe 工具查真实数据" → 翻成 scribe 自有 SSE:
  - `response.output_text.delta` → `{"delta": "片段"}`(累计为完整回复)
  - `response.output_item.added` 且 `item.type=="function_call"` → `{"tool": item.name, "tool_args": item.arguments}`
  - 收尾 `{"done": true, "content": 完整回复, "thread_id": ...}`;异常 → `{"error": ...}`
  - 复用 `/chat` 落库逻辑写 discussion_thread(user+editor)

**前端**:`api.ts` 加 `streamChat()`(镜像 `streamAction` 的 fetch-stream 解析);`Conversation.tsx` `ChatSection.send()` 改流式(回复气泡逐片填充 + "🔍 正在调用 X…" 工具提示 + done 兜底防丢片)。

**实测**(hermes:8642 + scribe:3320,问《雾港迷案》"有哪些人物"):
1. `{"tool":"mcp_scribe_list_characters","tool_args":"{\"work_id\":\"...\"}"}` — 主编真调工具
2. 一串 `{"delta":...}` — 流式回复
3. `{"done":true,"content":...,"thread_id":...}` — 完整回复+落库

回复基于真实设定(沈舟/陆沉,动机对得上),无瞎编。**校准结论**:`item.name`/`item.arguments` 字段名与代码假设一致;`model` 字段可传(hermes 接受 `doubao-seed-2.0-pro`)。**B1 端到端通。**

---

## ✅ B2 已实现 + hermes 原始 SSE 完整实测(2026-06-20)

**原始 SSE 事件类型实测**(直打 :8642/v1/responses,问"沈舟的动机"):
| event type | item.type | 说明 |
|---|---|---|
| `response.created` / `response.completed` | — | run 起止 |
| `response.output_item.added`/`.done` | `message` | 文本消息容器 |
| `response.output_item.added`/`.done` | `function_call` | **工具调用,`added` 时 `name`+`arguments` 已完整** |
| `response.output_item.added`/`.done` | `function_call_output` | 工具结果占位,**name/arguments 空,结果内容不透传** |
| `response.output_text.delta`/`.done` | — | 回复流式片段 / 整段 |

**关键发现**:
1. 主编是**多步 agent**——一次问答连调 4 个工具:`mcp_scribe_list_works → session_search → mcp_scribe_list_characters → mcp_scribe_search_book`,最后才流式回复。
2. **无 `reasoning`/thinking 事件**(doubao-seed 不产出)→ 思考气泡当前无数据源。
3. **`function_call_output` 不带结果内容** → 工具结果无法折叠展示。
4. 主编也用 hermes 自带工具(`session_search` 记忆检索),工具名展示需兼容非 `mcp_scribe_` 前缀。

**B2 实现**(据上述真实数据源,只做有数据的部分):`Conversation.tsx` —
- `ChatMsg.tools[]` 收集本轮工具调用序列;`ToolTimeline` 折叠组件渲染在回复气泡上方(「🔍 主编查阅了 N 项资料 ▾」,展开列每步)。
- `toolLabel()` 友好名映射(list_characters→查人物 / search_book→检索原文 / session_search→检索记忆…),并抠 `args.query` 当副标题(「沈舟」)。
- 流式中 thinking 指示器实时显示「正在查人物「沈舟」…」。
- **未做**(无数据源):reasoning 思考气泡、function_call_output 结果折叠。`tsc --noEmit` 绿;前端 dev server :3310 已起待作者亲验。
