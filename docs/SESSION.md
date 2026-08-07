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
| **进行中目标** | **v6.1 闭环已落地钩子**（讨论 ChangePack + 定稿 PostFinalize）；体验 SPA/Surreal 仍残差 |
| **方案** | [`docs/e2e-director-journey-5w.md`](./e2e-director-journey-5w.md) **v6.1** |
| **进度** | [`设计文档/2026-08-06-旅程5万字-进度.md`](../设计文档/2026-08-06-旅程5万字-进度.md) |
| **主验收书** | **v6 目标：纯旅程+主编 UI 新书**；工程参考 `book_052a2adb`（v5，不作体验 PASS） |
| **证据** | 方案 v6 文档；ChangePack 测；v5 工程包 `artifacts/e2e-journey-5w-v5-…` |
| **活跃分支** | `main` |
| **未合并 / WIP** | `canon_loop` / `pilot_runtime` / `prompt_blocks` 等待 commit |

### 旅程 5 万字

- **方案 v6.1**：只开旅程+只和主编聊天；**遇障→最优真路径修→同路回归再继续**；**聊天/定稿强制 ChangePack·PostFinalize，且要路径级证据（非仅单测）**  
- **v5 工程书** `book_052a2adb`：53856 字参考，**不作 v6.1 体验 PASS**  
- **铁律**：WCG 先于正文；完整 pilot；L1 禁静默写；禁捷径过关  

### 正典变更闭环（ChangePack）· v6.1 已挂产品路径

- **纯模块**：`scribe3/canon_loop.py`（L1 仅 `approved_item_ids`；模块硬门防 layer=L2 伪装）  
- **钩子**：`canon_hooks.discussion_change_pack` ← `POST /orchestration/proposal/from-discussion` 附带 `change_pack`  
- **钩子**：`body_confirmed_report` ← pilot `finalize` 返回 `post_finalize_report`  
- **HTTP**：`/canon/change-pack` · `/canon/post-finalize-report` · `/canon/change-pack/apply`  
- **测**：`test_canon_loop.py` + `test_canon_hooks.py`  
- **残差（非体验 PASS）**：SPA 变更卡 UI、Surreal 真写 Codex、纯 UI 跑满 5w、LLM 自由文本 Diff  

### 下一步

1. 按 [`设计文档/2026-08-07-正文全类型设定回写-完善方案.md`](../设计文档/2026-08-07-正文全类型设定回写-完善方案.md) 做 **全类型** 回写（非最小闭环）  
2. 统一设定收件箱；apply → Surreal；终选强制 extract  
3. 纯 UI 重跑 v6 书  


### 已知坑

- Grok 机禁重活（npm ci / 本机 Surreal / 全量测）；验收打 demo  
- 融合规程要求 Playwright 点批准；orch API apply 为过渡  
- full_check 仅 AI 味 soft-pass **不等于**质量线自动免检  
- `draft_loop` 超长压缩须带 `勿超过N` + `【强制重写】`；restore 用 `stats.words` 选版
