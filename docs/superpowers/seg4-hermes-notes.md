# 段4 探查笔记 · Hermes 真实 API(实测自 vendor/hermes-agent/gateway/platforms/api_server.py)

## Run 生命周期(段4 主路径)
- POST /v1/runs                  -> _handle_create_run    启动 run,202 返回 run_id
- GET  /v1/runs/{run_id}         -> _handle_get_run       当前状态
- GET  /v1/runs/{run_id}/events  -> _handle_run_events    SSE 结构化生命周期事件
- POST /v1/runs/{run_id}/approval-> _handle_run_approval  解决 pending 审批
- POST /v1/runs/{run_id}/stop    -> _handle_run_stop      中断

## Sessions(有状态 + fork)
- POST/GET /api/sessions,GET/PATCH/DELETE /api/sessions/{id}
- POST /api/sessions/{id}/fork           分支
- POST /api/sessions/{id}/chat[/stream]  会话补全
- GET  /api/sessions/{id}/messages       历史

## 段5 要用的(Hermes 原生,替代本地复刻)
- memory: GET/POST/DELETE /api/memory[/{key}]
- skills: GET/POST/DELETE /api/skills[/{name}] + /api/skills/test
- cron:   GET/POST /api/cron,/api/cron/{job}/run,DELETE
- usage:  GET /api/usage[/{session_id}]
- embeddings: POST /v1/embeddings
- 兼容: /v1/chat/completions, /v1/responses

## 仍需确认(读 handler 源码)
- _handle_create_run 请求体:怎么挂 scribe MCP server?怎么设 session-key(书)?怎么设 system/主编人格?
- _handle_run_events SSE:审批事件的 type/payload schema(前端审批卡要消费)
- _handle_run_approval 请求体:approval_id / decision / 字段名

文件:vendor/hermes-agent/gateway/platforms/api_server.py(4322 行)
