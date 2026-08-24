# docs · 工程与现行说明

本目录放**实现向**文档与方案；哲学/同心层设计蓝图在 [`设计文档/`](../设计文档/README.md)。

## 现行必读

| 文档 | 用途 |
|------|------|
| [SESSION.md](./SESSION.md) | **跨会话滚动状态**（新会话与 AGENTS.md 一起读；结束前更新） |
| **[v6.3.4 真书·对话驱动·全能力](./e2e-director-journey-v634-true-chat-full-capability.md)** | **主验收协议 rev.13**（写章内核 play-contract 五层 + Wave C；唯一体验总 PASS）；WCG=`scripts/v4_world_complete_gate.py` |
| [CURRENT_ARCHITECTURE.md](./CURRENT_ARCHITECTURE.md) | **当前架构唯一入口**（栈、路径、写通道、作者面五问、文档优先级） |
| [plans/2026-08-24-surface-ownership.md](./plans/2026-08-24-surface-ownership.md) | **作者面职责**：总纲 / 旅程 / 跨章弧 / 图谱·时间线 / 仪表盘 |
| [ARCHITECTURE_SPLIT_ROADMAP.md](./ARCHITECTURE_SPLIT_ROADMAP.md) | `app.py` / `store.py` 分阶段拆分 |
| [PR_TEST_BASELINE.md](./PR_TEST_BASELINE.md) | PR / 本地最低验证命令 |
| [`scribe3/README.md`](../scribe3/README.md) | 主线代码怎么跑 |
| [`scribe3/AGENTIC_BOUNDARY_DECISION.md`](../scribe3/AGENTIC_BOUNDARY_DECISION.md) | 对话驱动写 / 禁表单直填决策 |

### 验收附录（不得单独宣称 v6.3.4 总 PASS）

| 文档 | 角色 |
|------|------|
| [e2e-director-journey-2w-memory.md](./e2e-director-journey-2w-memory.md) | 记忆子集 / 6.3.x 附录 |
| [e2e-director-journey-5w.md](./e2e-director-journey-5w.md) | 纪律与正典闭环底本 |
| [plans/2026-08-10-v633-revalidation-quality-delta.md](./plans/2026-08-10-v633-revalidation-quality-delta.md) | 变更复验 F 项 |
| [evidence/v634-true-chat-TEMPLATE/](./evidence/v634-true-chat-TEMPLATE/) | 证据包模板 + matrix ID 预填 |
| `scripts/v634_evidence_checklist.py` | 证据内容校验（非写书） |

## 作者面工作流（打开书之后）

一问一主人。禁止再加「全局规划」顶栏。旧 `storyline` / `planning` / `arcs` 进**旅程**，不进仪表盘。

```text
打开书 → 中区总纲（目录还在）     这本书是什么
顶栏「旅程」→ 下一步 + 继续        现在写哪、卡在哪
  └ 底部折叠「跨章弧（参考）」     可选标签；勾了才进写作提示
顶栏「图谱 / 时间线」              人/事在哪
顶栏「仪表盘」                     质量 · 伏笔台账 · 码字
点某一章 → 章工作台 + 右侧主编     正典写入仍走审批
```

细则与信号所有权表：[surface-ownership](./plans/2026-08-24-surface-ownership.md)。栈与写通道仍以 [CURRENT_ARCHITECTURE](./CURRENT_ARCHITECTURE.md) 为准。

## 其它子树

- `adr/` — 架构决策记录  
- `audits/` — 审计  
- `superpowers/plans/` — 规划长文  
- `系统文档/` · `系统架构/` · `改进方案/` — 专题材料（阅读前先对 CURRENT）

## 归档

- 根目录 [`交付说明.md`](../交付说明.md) — 早期 `scribe/` + SQLite 批次快照，**非运维手册**
- [`plans/2026-08-24-tonglu-qoder-deep-analyze.md`](./plans/2026-08-24-tonglu-qoder-deep-analyze.md) — Qoder 通用文学拆书提纲，**非**铜炉拆书真源；勿按 43 章/配额表开拆。真源：[`worlds/乱世铜炉-拆文/`](./worlds/乱世铜炉-拆文/)
- [`plans/2026-08-24-tonglu-yinwen-audit.md`](./plans/2026-08-24-tonglu-yinwen-audit.md) — 因文规范核验与后文四条链收口；不重抽 214 节。五句在七场批注 + [`worlds/乱世铜炉-拆文/因文.md`](./worlds/乱世铜炉-拆文/因文.md)
- [`plans/2026-08-24-tonglu-craft-thin-slice.md`](./plans/2026-08-24-tonglu-craft-thin-slice.md) — 薄切片已执行并核过。产物 [`worlds/乱世铜炉-拆文/对照.md`](./worlds/乱世铜炉-拆文/对照.md)。现网点验《腕账》不改拆文包。真源仍是拆文包 + mentor-extract / mentor-craft
