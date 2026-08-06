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
| **更新于** | 2026-08-07 |
| **默认分支** | `main` |
| **进行中目标** | **v5.0** 旅程 5 万字：设定 WCG → 结构 → 完整 pilot 链（无捷径） |
| **方案** | [`docs/e2e-director-journey-5w.md`](./e2e-director-journey-5w.md) **v5.0** |
| **进度** | [`设计文档/2026-08-06-旅程5万字-进度.md`](../设计文档/2026-08-06-旅程5万字-进度.md) |
| **活跃分支** | `main` |
| **未合并 / WIP** | v5 待从零执行 |

### 旅程 5 万字（v5）

- **铁律**：未过 WCG 禁止正文；章内必须 大纲→节拍→演绎→草稿→体检→交付→定稿  
- **禁止**：safe_beats/假演绎、prose_pure 灌库、伪 tape、默认 skip、EMERGENCY 主路径  
- **工具**：`v4_world_complete_gate.py`；`v2_serial_pilot.py`（接地 STOP）  
- **作废书**：v2 离线灌稿；v3 设定未齐即开写  

### 下一步

1. 新建 `《旅程五站·v5·日期》`  
2. 只做设定直到 `v4_world_complete_gate` exit 0  
3. 结构对齐后逐章真 pilot  
4. 结案八线 + SPA 证据  

### 已知坑

- Grok 机禁重活（npm ci / 本机 Surreal / 全量测）；验收打 demo  
- 融合规程要求 Playwright 点批准；API apply 仅为过渡  
- full_check 仅 AI 味 soft-pass **不等于**质量线自动 PASS  
