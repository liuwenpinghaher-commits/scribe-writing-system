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
| **更新于** | 2026-08-09（**角色弧光完善已落地** + demo 章节 pulse/brief 冒烟） |
| **产品名（UI）** | 铜炉 / tonglu（仅品牌文案+logo，色板未改） |
| **默认分支** | `main`（本地可能 ahead；demo 已 hot/frontend 热更） |
| **刚完成** | ① **弧光假绿修复 + arc_signals** ② **里程碑 MCP + lie_belief 透传** ③ **节拍 focus brief/pulse** ④ **GET anchors.alignment + Codex 消费** ⑤ demo 冒烟 |
| **设计** | [`设计文档/2026-08-09-角色弧光子系统完善改进方案.md`](../设计文档/2026-08-09-角色弧光子系统完善改进方案.md)（Accepted） |
| **进行中目标** | 记忆质量 / 人盲；流水线 residual UX（SPA hold 条等） |
| **主验收书** | **`book_aa57f17e`**（2w 记忆）/ **`book_7b918ca0`**（5w 参考）；弧光冒烟 **`book_arc_smoke_demo`** |
| **活跃分支** | `main` |

### 角色弧光完善（2026-08-09）

- **模块**：`scribe3/arc_signals.py`（纯函数）；接线 `pulse._arc_dim` / `brief.assemble_chapter_brief` / `arc_directive` focus 驱动  
- **假绿**：无 eligible → info「未启用可忽略」；主档缺 lie → decision；**禁止**「未见跳变」当健康；配置态 **不** `degraded`  
- **节拍**：`arc_beat_focus` 每角一条；`miss_belief` 有向；brief ⚠ 与 pulse decision 同文案源（工具名可执行）  
- **工具**：MCP `s3_add_arc_beat` / `s3_delete_arc_beat`；`s3_add_char_state` + REST `POST /char-states` 透传 `lie_belief`  
- **UI**：`CodexDetail` 消费 `alignment`、冷启动条、质变历史折叠  
- **测**：`scribe3/tests/test_arc_signals.py` **14 passed**  
- **demo**：hot+frontend；HTTP pulse/brief **写前/写后** 捕获；MCP `commit_if_approved` 自动批写入 belief=88 + beat add/delete；URL 编码 GET anchors.alignment  
- **证据**（goal scratch）：`demo-chapter-pulse-before/after.json`、`demo-char-anchors.json`、`demo-char-states.json`、`demo-arc-smoke.md`、`demo-arc-write.log`  
- **注**：世界 REST 写默认关；章节验证写路径走 **MCP 工具**（与产品口径一致）

### 章节流水线闭环（2026-08-09）

- **模块**：`scribe3/ingest_lease.py` · `scribe3/ingest_policy.py` · migration **112**
- **单入口**：`schedule_ingest` / `run_or_enqueue` 覆盖 save / checkpoint / loop / restore / 终选 / dedup·polish·semantic_repair / POST `/ingest` / import / accept_unverified / MCP `s3_ingest_chapter` / `_bg_ingest` 占锁
- **KD18**：advisory hold 后 `checkpoint(final)` 同 prose_fp → `active_hold_supersedes`，**不 enqueue**
- **MCP**：`s3_save_chapter` 对齐 `evaluate_save_craft_gate`；blocking 不落库
- **API**：`POST /ingest/confirm`；`GET /ingest/status` 扩 held/lease；capabilities 报 `ingest_lease`/`ingest_policy`/`mcp_craft_gate`
- **测**：`scribe3/tests/test_ingest_pipeline_policy.py` **15 passed**；证据 `/tmp/grok-goal-c24de3662f01/implementer/`
- lease CAS：migration **113** `ingest_lease` 表 + `TableLeaseBackend`；purge 前 assert owner  
- residual：SPA hold 确认条、token 哈希化（见 residuals.md）

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

1. SPA hold 确认 UX（PR-4 residual）+ 可选 token 哈希  
2. 前端 `deploy_demo.sh frontend`（若需公网 SPA 立刻见八块 UI）  
3. 待确认设定收件箱完善；记忆人盲仍须真人  
4. `git push` 后若需镜像重建再走 GHA / deploy 脚本（当前 demo 已 docker cp 热部署）  

### 已知坑

- Grok 机禁重活、**禁止本机起 Surreal**；验收只打 **已部署 demo**  
- **Surreal 唯一 3.x（demo 3.2.4）**：无 2.x 回退；`_migration` 仅 `type::record`；conftest 遇 2.x 直接 fail  
- 启发式 extract 可能过召回 → 人批拒  
- full_check AI 味 soft-pass ≠ 质量线自动绿  
- **Demo 40G 盘**：`compose --build` 会堆悬空镜像；见 [`docs/ops/demo-disk-hygiene.md`](./ops/demo-disk-hygiene.md)  
