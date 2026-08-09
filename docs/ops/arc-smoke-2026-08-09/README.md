# 弧光完善 · demo 章节冒烟（2026-08-09）

- **commit**: `f7b01a1` on `main`（已 push）
- **demo**: hot + frontend 热更后 `SMOKE_V2_PASS`
- **work**: `book_arc_smoke_demo` / empty `book_arc_empty_smoke`

## 文件
| 文件 | 含义 |
|------|------|
| demo-arc-write.log | MCP 写 + HTTP 写前/写后日志 |
| demo-chapter-pulse-before/after.json | HTTP pulse 捕获 |
| demo-char-anchors.json | URL 编码 GET alignment |
| demo-char-states.json | lie_belief=88 列表 |
| demo-arc-smoke.md | 摘要表 |

## 口径
世界 REST 写默认关；写路径验证走 MCP `commit_if_approved` 自动批。
