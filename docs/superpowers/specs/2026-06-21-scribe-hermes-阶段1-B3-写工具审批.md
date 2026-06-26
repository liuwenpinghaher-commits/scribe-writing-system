# 阶段1 · B3 写工具审批设计(scribe 自管审批门 · 异步待办)

**日期**:2026-06-21  **性质**:阶段1 子切片 B3。承接 B1(对话走 hermes Responses)/ B2(工具调用折叠时间线)。

## 0. 目标
主编(经 hermes agentic loop)调用**写类** scribe MCP 工具时,不直接落库,而是挂起为「待批写操作」;作者在 scribe 前端审批卡点**批准**后才真写。**只读工具自动放行**。兑现阶段1 验收「写操作弹审批卡,批准后才执行」。

## 1. 关键实测结论(决定架构,非假设)
2026-06-20/21 实测:
- hermes v0.17.0 `/v1/responses` **不支持 OpenAI 风格 `require_approval`**——加该字段无效,写工具在 hermes agentic loop 内部**直接执行**,scribe 的 SSE 转发层是只读旁观者,**等看到 function_call 时已写完,拦不住**。
- hermes **支持** MCP elicitation(`tools/mcp_tool.py` 的 `elicitation/create` handler),但表单审批路由到 **hermes 自己的 approval surface(CLI/TUI/Telegram/Slack)**,对 API 驱动 session 还会 fail-closed(超时 decline)——**到不了 scribe 浏览器**。

**结论**:审批必须在 **scribe 自己控制的层**做,不能依赖 hermes 审批能力,也不能在 SSE 转发层做。唯一能在「写发生那一刻」拦截的地方 = **scribe MCP server 的写工具实现内部**(该工具在 scribe 进程里执行)。

**否决的方案**:
- A) scribe `ctx.elicit()` → 依赖 hermes 转发,实测审批弹错地方(hermes 渠道,非 scribe 前端)。否决。
- C) 给主编只挂只读+propose 工具 → 要重做工具集语义、主编行为不可控。否决。
- **B) scribe 自管待批队列 → 采纳**(完全在 scribe 控制内,复用现有 option_set/insights 异步审阅模式)。

## 2. 交互模型:异步待办(已定)
写工具**立即返回**`awaiting_approval`,主编继续对话(MCP 工具不阻塞);待批写进入审批区,作者随时批准/拒绝,**批准才真写**。
- 主编是异步的:工具返回即「已提交」,它不知道最终批没批。若被拒,主编当轮看不到结果(作者可口头告知)。**回灌主编不在 B3 范围**。

## 3. 架构(4 个单元)

### ① MCP server 写工具门 — `scribe_mcp/server.py`
- 常量 `WRITE_GATED = {upsert_setting, save_chapter, save_snapshot, upsert_character, plant_foreshadow, advance_foreshadow, set_author_intent}`(碰正典内容的写)。
- 这些工具改为:`pid = db.enqueue_pending_write(work_id, tool_name, args)` → `return {"status":"awaiting_approval","pending_id":pid,"note":"已提交,待作者在 scribe 里确认"}`。**不调真实 db 写。**
- 不在集合内的工具(`list_*/get_*/search_book` 只读,以及低风险内部写 `raise_consistency_flag/index_segment/capture_imagination/save_feedback/propose_options`)**照常直接执行**。
- **维护约定(写进代码注释 + 本 spec)**:新增碰正典内容的写工具,必须加进 `WRITE_GATED`,否则绕过审批。

### ② pending_writes 表 + db 方法 — `schema.sql` + `scribe_mcp/db.py`
- 表 `pending_writes`:`id TEXT PK, work_id TEXT, tool_name TEXT, args_json TEXT, status TEXT(pending/approved/rejected), result_json TEXT, created_at, decided_at`。
- 方法:
  - `enqueue_pending_write(work_id, tool_name, args) -> id`
  - `list_pending_writes(work_id, status="pending") -> list`
  - `decide_pending_write(id, approve: bool) -> dict`:approve 时按 `tool_name` 查 `_WRITE_DISPATCH`(tool_name→真实写函数)注册表,`fn(**args)` 真写,结果存 `result_json`,status=approved;reject 仅标记 status=rejected。**这是唯一真正落库的地方。** **幂等**:status 非 pending(已 approved/rejected)时直接返回既有 `result_json`,不重复执行。
- `_WRITE_DISPATCH`:把 `WRITE_GATED` 每个工具名映射到对应 db 写方法(签名与 MCP 工具一致)。

### ③ REST 审批端点 — `scribe_mcp/api.py`
- `GET /works/{w}/pending-writes?status=pending` — 列待批(owner 边界校验)
- `POST /works/{w}/pending-writes/{id}/approve` — 调 `db.decide_pending_write(id, True)` 真写,返回执行结果
- `POST /works/{w}/pending-writes/{id}/reject` — 标记拒绝,不写
- 现有 `/works/{w}/events` SSE 快照加 `pending_writes` 计数字段,前端实时感知。

### ④ 前端审批卡 — `web-app/src`
- **默认放对话内联**(最贴合 B1/B2 对话心智):主编回复气泡下方,若本轮产生待批写,渲染审批卡(标题=人话「新增设定『沈舟的动机』」,展开看 args,带 批准/拒绝)。复用 `ScribeCardView` 风格 + `toolLabel()` 友好名。
- 右栏 SSE 计数加一个「N 项待批写」角标做兜底感知(可与现有 insights/option_sets 同列)。
- 批准/拒绝调 ③ 端点 → SSE 刷新 → 卡标记已应用/已拒绝。
- **可调决策**:审批卡放对话内联 vs 右栏待办区——本 spec 取对话内联+右栏角标,实施时若体验不佳可调。

## 4. 数据流
```
主编调 upsert_setting(写)
  → [MCP 门] enqueue pending_writes, status=pending
  → 返回 {awaiting_approval, pending_id}
  → 主编对话:"我提议加这条设定,已提交待你确认"
  → [前端] 审批卡(SSE 感知 pending 计数)
  → 作者点「批准」
  → [REST] approve → db.decide_pending_write(id, True)
  → [_WRITE_DISPATCH] 真实 db.upsert_setting(**args) 落库
  → SSE 刷新 → 卡标记「已应用」
```

## 5. 测试(TDD)
- **db**:`enqueue → list(pending) → approve` 后目标库真出现该数据;`reject` 后**库无变化**;approve 后 status=approved 且 result_json 有值。
- **MCP 门**:调写工具返回 `awaiting_approval` 且**查库确认未落库**;调只读工具照常返回数据。
- **REST**:approve 后 GET 对应资源能查到新数据;越权 owner 403;reject 不写;重复 approve 幂等(已 decided 不重复执行)。
- **端到端**:复用 2026-06-20 实测脚本(引导主编写设定),这次应停在 pending、**不真写**,前端可见审批卡。

## 6. 验收
- 主编调写工具 → 不落库 → 前端审批卡 → 批准才真写、拒绝不写。
- 只读工具(查人物/检索原文)仍自动放行、流式正常(B1/B2 不回归)。
- 越权审批被挡(owner 边界)。

## 7. 诚实边界 / YAGNI
- 不做主编结果回灌(批/拒结果不告诉主编)——超出 B3。
- 不做审批超时自动决策——待批项常驻,作者自己清。
- `WRITE_GATED` 白名单维护是人工约定,不做自动推断。
