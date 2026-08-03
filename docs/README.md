# docs · 工程与现行说明

本目录放**实现向**文档与方案；哲学/同心层设计蓝图在 [`设计文档/`](../设计文档/README.md)。

## 现行必读

| 文档 | 用途 |
|------|------|
| [SESSION.md](./SESSION.md) | **跨会话滚动状态**（新会话与 AGENTS.md 一起读；结束前更新） |
| [CURRENT_ARCHITECTURE.md](./CURRENT_ARCHITECTURE.md) | **当前架构唯一入口**（栈、路径、写通道、文档优先级） |
| [ARCHITECTURE_SPLIT_ROADMAP.md](./ARCHITECTURE_SPLIT_ROADMAP.md) | `app.py` / `store.py` 分阶段拆分 |
| [PR_TEST_BASELINE.md](./PR_TEST_BASELINE.md) | PR / 本地最低验证命令 |
| [`scribe3/README.md`](../scribe3/README.md) | 主线代码怎么跑 |
| [`scribe3/AGENTIC_BOUNDARY_DECISION.md`](../scribe3/AGENTIC_BOUNDARY_DECISION.md) | 对话驱动写 / 禁表单直填决策 |

## 其它子树

- `adr/` — 架构决策记录  
- `audits/` — 审计  
- `superpowers/plans/` — 规划长文  
- `系统文档/` · `系统架构/` · `改进方案/` — 专题材料（阅读前先对 CURRENT）

## 归档

- 根目录 [`交付说明.md`](../交付说明.md) — 早期 `scribe/` + SQLite 批次快照，**非运维手册**
