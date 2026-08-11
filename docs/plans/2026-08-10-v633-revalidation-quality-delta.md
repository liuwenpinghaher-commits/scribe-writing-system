> **总 PASS 协议（现行）**：[v6.3.4 真书·对话驱动·全能力](../e2e-director-journey-v634-true-chat-full-capability.md)
> 本文档降为：**记忆子集 / 纪律附录**，单独跑完 **不得** 宣称铜炉 v6.3.4 总 PASS。
> WCG SSOT：`scripts/v4_world_complete_gate.py`
> 体验路径：SPA 对话 + 点批/工作台；禁止脚本灌章冒充。
> 工程对照：`scripts/v632_true_chat_journey.py` ≠ SPA PASS。

# 铜炉 v6.3.3 · 变更复验与小说质量增益评估方案

| 项 | 值 |
|----|-----|
| **日期** | 2026-08-10 |
| **状态** | Done · 功能复验 + serialize ch1–5 + score（2026-08-10） |
| **文档真源** | 本文件 |
| **前序** | v6.3 记忆旅程 · v6.3.1/6.3.2 · 章节管线 · 命题 Author-UX · 校验 hybrid |
| **验收环境** | demo `www.qing.blue` 已部署栈；禁止 Grok 机全量重测/第二 Surreal |

---

## 1. 为何更新 6.3

v6.3 原聚焦 **记忆可用性 D4–D7**（双真、steer、质量增益）。  
**2026-08-09～08-10** 又合入多条会改变「能否写出更好长篇」的能力，须：

1. 把 6.3 **扩展为「记忆 + 结构真相 + 校验诚实 + 写压/时间线产品」** 一体复验包（称 **v6.3.3**）。  
2. **新开一书**，避免旧书脏数据干扰。  
3. 用 **可复现探针 + 确定性指标 + 人读协议**，回答：  
   - 这些变更对「写一本好小说」的质量提升 **大约多少**？  
   - **还有多少进步空间**？

**诚实边界（强制）：**

- **不宣称** 文学 ≥9.5 或人盲定级完成（须 `human-blind-memory-quality-protocol.md`）。  
- 数值增益是 **代理指标**（结构/记忆/假绿/限知可检性），不是最终艺术分。  
- 与 D1–D7 AB 结论并存：记忆 lead 曾卡在 ~0.4；本轮增益主要在 **可检性、可导航性、假绿消除、真相史**。

---

## 2. 昨日→今日变更地图（须逐项探针）

| 域 | 代表提交/产物 | 对写作质量的机制 |
|----|----------------|------------------|
| **校验 hybrid M0–M5** | `e48842c` `b1d22d5` · `docs/...verification-...md` | 假绿↓；台账诚实；L1 语义限知路径；severity 统一 |
| **命题 Author-UX** | UX0/UX1 · PR-4/5 · PR-3/6/7/8/9 · M2c 回填 | 事件可读；真相不刷屏；演变/谁知道；ingest source |
| **章节管线** | lease/CAS/policy | 并发 ingest 可靠，反哺不丢 |
| **写压 / PSC·PDC** | pressure 全回路 | 治匀速散步、磨戏 |
| **时间线/布局/会话** | 滚动、chat 栏、线程折叠 | 降低操作摩擦（间接质量） |
| **弧光** | 假绿修复、节拍 focus | 角色弧可检 |

---

## 3. 新书与旅程参数

| 项 | 值 |
|----|-----|
| 书名模板 | `炉灰记·v6.3.3·全量复验·YYYYMMDD-HHMM` |
| 脚本 | `scripts/v633_change_revalidation.py` |
| 证据根 | `docs/evidence/v633-reval-<stamp>/` 或 `/tmp/grok-1000/v633-reval/evidence/` |
| 记忆锚 | 继承 A1–A7（与 v6.3 同故事宇宙，便于对照） |
| 连载 | **已完成** ch1–5 pilot finalized · 合计 **22672** 字（IN_BAND）；书 `book_013bcb3b` |
| API | `API_BASE=https://www.qing.blue` + 登录 cookie |
| 证据 | `docs/evidence/v633-reval-20260810/` · 代理帮助 ~**64%** · 记忆线 **PASS** |

### 阶段

| 阶段 | 内容 | 通过标准 |
|------|------|----------|
| **S0** | 登录 · 建书 · health | 200 / slug |
| **S1** | 设定脚手架（角色/规则/事实/关系） | proposal apply 绿 |
| **S2** | **功能探针矩阵**（见 §4） | 每项 PASS/FAIL + 证据 JSON |
| **S3** | 记忆探针 M0–M2（专名/物件/规则） | scorecard |
| **S4** | 可选短连载 1–2 章 | 有 prose + post-check/coverage |
| **S5** | **质量增益评分表**（§5） | 写出 delta 与 headroom |
| **S6** | 与 v6.3.1/旧炉灰记对照 | 有则 diff；无则记 N/A |

---

## 4. 功能探针矩阵（全量变更）

| ID | 探针 | 期望 |
|----|------|------|
| F1 | `GET /issues?chapter=N` | `coverage.mode=deterministic_only`；skipped 含 llm/discipline |
| F2 | 空态文案/coverage.note | 非「全绿」假暗示 |
| F3 | `POST /review/chapter` mode=deterministic | 200；coverage 列 skipped L1 |
| F4 | review full + mock complete_fn（容器内）或 flag | L1 可出 finding；payload 无 secret value |
| F5 | normalize→triage degeneration S1 | verdict=blocking |
| F6 | `timeline` event label | 有 goal 时 label_source=goal，非纯「行动」 |
| F7 | `project_tree` 命题分类 | label=世界真相；默认无获知/行动刷屏（有数据时） |
| F8 | `list_entity_truth_history` + knowers | include_closed 段数≥open；他者 knower 可构造 |
| F9 | facts `source`/`bucket` | 新写入 ingest/author 有 source |
| F10 | causal | no_event_data 三态诚实 |
| F11 | health | ok |
| F12 | 章节 lease/policy 冒烟（若有 ready 接口） | 不 500 |

---

## 5. 质量增益怎么估（代理指标）

### 5.1 分维度 0–10（写作相关）

| 维度 | 变更前典型（8/9 记忆） | 变更后目标 | 测法 |
|------|----------------------|------------|------|
| **D 记忆可检索** | M0–M2 探针 | ≥ 前次 | chat/prefetch 命中锚 |
| **D 单真/演变可导航** | 弱 | 实体卡历史 + 树滤噪 | history 段 + 树叶 |
| **D 限知可检** | markers only | + 台账 leaks + L1 路径 | issues + review |
| **D 假绿防护** | 台账过窄 | coverage + triage 统一 | F1–F5 |
| **D 因果/结构** | 有 causal | 仍保留 | F10 |
| **D 节奏/压力** | PDC/PSC 已合 | 有 pressure findings 路径 | post-check 字段 |
| **D 产品摩擦** | 时间线空白/线程 | 已修 | 冒烟备注 |
| **L 文学/声口** | 未系统升 | **仍低**（L2–L5 未满） | 明示 headroom |

### 5.2 综合「写作系统增益」

\[
Gain_{system} = 0.25 G_{memory} + 0.25 G_{truth} + 0.25 G_{verify} + 0.15 G_{pressure} + 0.10 G_{ux}
\]

每项 \(G \in [-2,+2]\) 相对 v6.3.1 基线；再映射到 **「对写好一本小说的帮助」0–100% 代理分**：

| 代理分 | 含义 |
|--------|------|
| 0–20% | 几乎无助于成书 |
| 20–40% | 少踩坑，不直接抬文笔 |
| 40–60% | 结构/记忆明显更稳 |
| 60–80% | 接近专业责编+记忆助理 |
| 80–100% | 接近「能稳定出好小说」— **当前禁止自证到此** |

### 5.3 进步空间（headroom）

必须单独列出：

1. **人盲文学分** 未跑 → 艺术上限未知  
2. **L2–L5** 未满开 → 语义责编层缺口大  
3. **记忆 lead** 历史卡在 ~0.4 → 注入策略仍有工  
4. **人机共写闭环**（按 issue 自动改稿）未默认开  
5. **全书一致性**（人物声口/时间线矛盾）LLM 未统一进台账  

---

## 6. 执行与证据

```bash
export API_BASE=https://www.qing.blue
# cookie 由脚本登录写入
python3 scripts/v633_change_revalidation.py --phase all
```

产出：

- `00-plan-link.md` · `01-book.md` · `02-feature-matrix.json`  
- `03-memory-scorecard.md` · `04-quality-delta.md` · `05-headroom.md`  
- `99-summary.md`

---

## 7. 与旧 6.3 文档关系

| 文档 | 关系 |
|------|------|
| memory-quality-best-plan-v4 / to-9.5 | 记忆目标不变；本方案补 **产品+校验** 复验 |
| verification-capability-audit… | 校验设计真源；本方案跑 **落地验收** |
| proposition-author-ux-v2 | 真相表面；本方案跑 **探针 F6–F9** |
| chapter-pipeline-closed-loop | 管线；本方案 **F12** 轻触 |

---

## 8. Non-Goals

- 在本机全量 pytest / 第二 Surreal  
- 用本轮代理分代替人盲 ≥9.5  
- 强制 5 章全文连载（可续跑，非门禁）  
