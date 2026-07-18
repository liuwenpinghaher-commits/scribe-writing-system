# scribe3 真人验收运行态基线

- 验收作品：`book_d0bb19e9`《潮骨灯·真人验收·0718》；通过作品库 UI 创建，未触碰既有作品。
- 代码基线：`f67c14b`（`main`）。开始时工作树干净，分支比 `origin/main` 领先 2 个提交。
- 首次发现：后端和前端进程分别启动于 2026-07-16，未加载 2026-07-17 的 HEAD 改动；已仅重启确认的旧 PID 82450（后端）与 96219/96290（前端）。SurrealDB 与 3 个 Hermes 网关未重启。
- 重启后：后端 PID 10323，前端 Vite 8.1.4；`GET /health`、`/capabilities`、`/openapi.json` 均成功。
- 功能开关：snapshot_v1、editorial_thread_v1、memory_fabric_v1、context_inspector_v1、assembler_v1 为开；spectron_shadow 为关。
- Hermes：`/ai/runtime-status` 在 45 秒内返回 `ok=true`。default、scribe3、scribe3_write 均为 gateway 可用但 disk degraded；UI 文案正确显示为“周边降级，对话/写作不受影响”，未误报离线。
- 版本：Hermes 0.18.2，Node 26.5.0，npm 12.0.0，Python 3.14.3，SurrealDB 3.2.0。

## 证据

- 浏览器作品库创建前后 DOM 快照。
- `GET /works` 读回新作品 slug。
- `GET /health`、`/capabilities`、`/ai/runtime-status` 响应摘要。
- 运行进程和端口记录保留在本会话日志；不含凭据或环境变量。
