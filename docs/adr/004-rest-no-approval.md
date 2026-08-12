# ADR-004：REST 世界写 vs MCP WRITE_GATED 审批分界

| 字段 | 值 |
|------|-----|
| 状态 | Accepted |
| 日期 | 2026-08-12 |
| 关联 | 工程健康度 P1-7 · KD-3 · `AGENTIC_BOUNDARY_DECISION.md` |

## 背景

审计将「REST 端点不走 MCP `WRITE_GATED` / `commit_if_approved`」标为门控绕过。  
实际产品存在**两条合法写路径**，语义不同。

## 决策

| 通道 | 身份 | 审批 | 默认 |
|------|------|------|------|
| **REST 世界写** | 已登录**作者**（session cookie） | **不经** MCP 审批队列 | 生产 `SCRIBE3_EMERGENCY_REST_WRITE=0` → **403**；开启时视为作者直操作 |
| **MCP `s3_*`** | AI / agent（Hermes tool） | **必须** `WRITE_GATED` + 人批后 `commit_if_approved` | 拒绝/过期不假绿 |

**原则**：作者本人在 UI/REST 上的操作 = 人已在场；AI 经 MCP 的写 = 必须人批。

## 后果

1. **不**将 REST 强制套 MCP 审批同构（除非未来产品改为「全写经收件箱」）。
2. 开启 emergency REST 时应：
   - 写 audit / 操作日志（建议 `audit_event` 或 LLM ledger 旁路）；
   - 仅管理员或显式 env 开启。
3. 文档与验收不得再称 REST=漏洞；应称 **双路径产品契约**。

## 备选（拒绝）

- **全写经 MCP 审批**：破坏作者即时编辑体验，工作量大。
- **取消 MCP 审批**：限知/正典风险不可接受。

## 参考

- `scribe3/AGENTIC_BOUNDARY_DECISION.md`
- `docs/plans/2026-08-12-engineering-health-optimal-plan.md` EH-12 / KD-3
