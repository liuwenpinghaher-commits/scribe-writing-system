# SESSION.md · 跨会话交接（滚动状态）

> **用途**：本仓库唯一跨会话记忆。新会话先读 [`AGENTS.md`](../AGENTS.md) + **本文件**，再动手。

---

## 新会话开场（复制粘贴）

```
继续 https://github.com/liuwenpinghaher-commits/scribe-writing-system
先读 AGENTS.md 和 docs/SESSION.md，再继续。
```

---

## 当前状态

| 项 | 值 |
|----|----|
| **更新于** | 2026-08-09（上下文检查器 B∪C；schema mark 已修 Surreal 3） |
| **产品名（UI）** | 铜炉 / tonglu（仅品牌文案+logo，色板未改） |
| **默认分支** | `main` |
| **刚完成** | **上下文检查器 B∪C**：TurnView 读合同、TurnBind、写路径真 session 绑定、discussion 单编译、UI 诚实八块 |
| **设计** | [`设计文档/2026-08-09-上下文检查器-B合C最优方案.md`](../设计文档/2026-08-09-上下文检查器-B合C最优方案.md) |
| **进行中目标** | **v6.3** 约 2 万字新书 · chat 驱动 · **记忆可用性主轴**（见 docs/e2e-director-journey-2w-memory.md） |
| **主验收书** | **`book_aa57f17e`**（2w 记忆）/ **`book_7b918ca0`**（5w 参考） |
| **活跃分支** | `main` |

### 上下文检查器 B∪C（2026-08-09）

- **根因**：检查器只读空 `memory_trace`；讨论不编译；写路径合成 snapshot 与 UI 脱节；六块假 0。  
- **读模型**：`context_turn_view.py` · `GET .../trace/{rev}` 聚合 TurnBind（优先）+ memory_trace 明细。  
- **写模型**：migration **111** `context_turn_bind`；每次成功 compile 且带 session+revision 即落库。  
- **讨论**：`discussion.v1` Policy + `assemble_discussion_system`；禁写作围栏协议。  
- **UI**：八块预算；`not_compiled_yet` 不画假 0；ChiefDock 凡 snapshot 即绑定。  
- **测**：`scribe3/tests/test_context_turn_view.py`（8 passed）。  
- **demo**：`./scripts/deploy_demo.sh hot` 后容器内 `DEMO_SMOKE_PASS`（discuss+write bind + handler）。  

### 旅程 5 万字 / 2 万字记忆

- 方案 v6.2 / v6.3.2 见既有进度文档；A/B D7 硬门槛未达见 `设计文档/2026-08-08-旅程2万字-记忆验收-进度.md`。  

### 下一步

1. 前端 `deploy_demo.sh frontend`（若需公网 SPA 立刻见八块 UI）  
2. 待确认设定收件箱完善（P0→P1）  
3. Phase E 九线结案文（5w 规模线 PARTIAL）  

### 已知坑

- Grok 机禁重活、**禁止本机起 Surreal**；验收只打 **已部署 demo**  
- **Surreal 唯一 3.x（demo 3.2.4）**：无 2.x 回退；`_migration` 仅 `type::record`；conftest 遇 2.x 直接 fail  
- 启发式 extract 可能过召回 → 人批拒  
- full_check AI 味 soft-pass ≠ 质量线自动绿  
- **Demo 40G 盘**：`compose --build` 会堆悬空镜像；见 [`docs/ops/demo-disk-hygiene.md`](./ops/demo-disk-hygiene.md)  
