# Director 五站 · 约 5 万字 · 优化方案 v6.2

| 项 | 值 |
|----|-----|
| **版本** | **6.2（落地修订：全类型正典回写已部署 · 新书验收）** |
| **日期** | 2026-08-07 |
| **状态** | **产品路径已落地（demo）· 新书体验验收进行中** |
| **产品** | scribe3 |
| **环境** | **仅 demo 已部署栈**（`www.qing.blue` / `ubuntu@82.157.130.140`） |
| **进度** | [`设计文档/2026-08-06-旅程5万字-进度.md`](../设计文档/2026-08-06-旅程5万字-进度.md) |
| **融合** | [`docs/融合执行规程-真人验收×对话驱动改造.md`](./融合执行规程-真人验收×对话驱动改造.md) |
| **正典闭环** | [`设计文档/2026-08-07-正典变更闭环.md`](../设计文档/2026-08-07-正典变更闭环.md) |
| **全类型回写** | [`设计文档/2026-08-07-正文全类型设定回写-完善方案.md`](../设计文档/2026-08-07-正文全类型设定回写-完善方案.md) |
| **前序** | v6.1 纪律（遇障同路 · 聊天/定稿强制闭环）**全部继承**；本版把「未齐」能力改为 **已部署 + 路径证据** |

---

## 0. 北极星（两句）

1. **体验**：作者 **只开旅程 + 只和主编聊天**（加「批准 / 放行 / 接受稿」），就能写完一本约 **5 万字**、可读的好书。  
2. **纪律**：**遇障 → 用真路径上的最优修法解决 → 同一旅程/主编路径继续**；禁止捷径过关。聊天改设定与正文定稿 **必须跑通全类型正典闭环**（抽取 → 候选/变更包 → 人批 → Surreal 落库），且验收要 **测到这条链**。

```text
成功 ≠ 库里有 5 万字
成功 ＝ 作者可复述路径「我只聊了天、点了批，旅程带着我走完」
       ＋ 设定先齐 ＋ 章链完整 ＋ 正典无静默写 ＋ 好书标准
       ＋ 正文/讨论增量进「待确认设定」全类型收件箱
```

---

## 0.1 相对 v6.1 的落地差分（实现真相）

| 能力 | v6.1 文档原述 | **v6.2 现状（demo 已验证）** |
|------|---------------|------------------------------|
| ChangePack 安全内核 | 已交付 | **保持**；`approved_item_ids` + 模块硬门 |
| 讨论 → ChangePack | API 钩子 | **`POST /orchestration/proposal/from-discussion` 附带 `change_pack`**；亦可 `POST /canon/change-pack` |
| 定稿 → PostFinalize | 钩子 | **pilot `finalize` → `post_finalize_report`**；亦可 `POST /canon/post-finalize-report` |
| 全类型抽取 | 方案中 | **标记 + 启发式 + 可选 LLM**（`canon_extract.py`） |
| 候选持久化 | 方案中 | **Surreal `canon_candidate`（migration 106）** |
| apply → Surreal | 未齐 | **`canon_apply_store` 真写** character/world_rule/faction/item/term/promise/fact/knowledge/… |
| 统一收件箱 UI | 仅人物 | **Codex「待确认设定」**（`listCanonCandidates` + 旧 unverified 合并） |
| 设定债 | 看板愿景 | **`GET /canon/debt`**；旅程看板数字 **仍可增强** |
| 纯 UI 跑满 5 万字 | 未齐 | **本版目标：新书 `book_*` 按 §10 跑**（见进度表当前 slug） |
| 工程参考书 | `book_052a2adb` | **仅备查**，≠ 体验 PASS |

**仍残差（诚实，不挡「闭环线」但挡「总 PASS」）**

- SPA **变更卡**与定稿报告 **分节弹层**仍可增强（当前：收件箱列表 + API 批）  
- 自然语言 Diff 依赖 Hermes LLM；标记/启发式为确定性契约  
- 启发式对整章可能过召回 → **人批/拒** 是设计，禁止自动灌库  
- 旅程看板「设定债」数字与挡 N+1 可配置门闩：可选增强  

---

## 1. 总原则：遇障怎么走

### 1.1 强制循环（每一步都适用）

```text
推进（旅程站 / 主编话轮 / pilot 步）
   │
   ├─ 绿 → 进入下一站
   │
   └─ 红 / 停靠 / 异常
         │
         ▼
      【STOP】记录：症状 · 证据 · 是否触铁律
         │
         ▼
      【最优解】只允许在真路径上修：
         · 修产品 bug（接地/LLM/UI 批准/变更包/候选 apply…）
         · 或修设定/大纲（经主编提案+批准 或 待确认设定点批）
         · 禁止：EMERGENCY、safe_beats、离线灌库、表单静默、脚本冒充作者
         │
         ▼
      【同路径回归】同一句意图 / 同一站 / 同一步再走
         │
         ▼
      绿 → 继续；仍红 → 再 STOP，升级缺陷账本，不换旁路
```

| 规则 | 说明 |
|------|------|
| **最优 ≠ 最快** | 优先修「旅程+主编+批准」能走通的解，不优先找旁路 |
| **同路径** | 修完必须用 **原来卡住的那条作者路径** 再验，禁止「脚本绿了就算过」 |
| **一次一事** | 一次 STOP 只收敛一个主因，避免堆脚手架 |

### 1.2 禁止的「假继续」

- 接地失败 → 灌 safe_beats / 假演绎  
- LLM 失败 → 磁盘 prose 灌章  
- 批准 UI 不通 → 永久 orch API 当作者路径（工程可暂用，**体验 PASS 不算**）  
- 设定未齐 → 先写后补且无 WCG  
- 改设定 → 聊天说完不进候选/变更包、静默写 L1  

---

## 2. 作者唯一合法路径

### 2.1 允许

| 动作 | 说明 |
|------|------|
| **旅程看板** | 看站位、下一动作、WCG、设定债、字数、停靠人话 |
| **主编聊天** | 意图 / 设定 / 结构 / 章推进 / 改稿 / 质量反馈 |
| **点批** | 提案、大纲放行、接受 advisory、终选、**ChangePack / 待确认设定批准** |
| **只读检视** | Codex、目录、正文；不靠表单失焦改正典 |

### 2.2 禁止当主路径

| 动作 | 原因 |
|------|------|
| 大批量表单改正典 | 正典 = 主编工具 + 批准 |
| 日常 `v2_serial_pilot` / curl 写书 | 工程工具，非作者体验 |
| EMERGENCY / prose_pure | 假路径 |

### 2.3 与工程脚本的边界

| 用途 | 是否算 v6.2 体验 PASS |
|------|----------------------|
| 作者：旅程 + 主编 + 点批（含待确认设定） | **唯一**体验 PASS |
| CI / 单测 / WCG 审计 / 路径冒烟 | 允许，须在证据注明 |
| 串行脚本代写 10 章 | **仅工程证明**；`00-author-path.md` 必须诚实，**不得**宣称体验 PASS |

---

## 3. 完成定义（九线 · 好书）

```text
总 PASS ⇔ 旅程 ∧ 主编 ∧ 设定 ∧ 正典闭环 ∧ 真路径 ∧ 工艺 ∧ 质量 ∧ 规模 ∧ 缺陷
```

| 线 | PASS |
|----|------|
| **旅程** | 站序可走通；live tape ≥5 种 pilot_state，跨度 >10s |
| **主编** | 主输入来自主编对话；世界写入来自待批提案 / 待确认设定 |
| **设定** | WCG 绿且 **先于** 验收正文；Codex 可见 |
| **正典闭环** | **聊天与定稿均触发全类型候选**；L1 仅批准列表写 Surreal；见 §5 |
| **真路径** | EMERGENCY=0；完整 pilot；无 safe_beats / prose_pure |
| **工艺** | 无默认 skip；接地 STOP |
| **质量** | 无公式注水；可读；回指设定；heavy → 读感说明 |
| **规模** | 合计 **[45000, 55000]** |
| **缺陷** | 无开放 P0/P1；路径诚实 |

**好书底线**：限知不泄、动机不 OOC、非说明书体、章有压力/钩子、弧对齐 intent。

---

## 4. 旅程站 × 主编（全链路）

| 站 | 作者对主编 | 系统 | 裁决 |
|----|------------|------|------|
| 建书 | 「开一本…约 5 万字」 | 建 work，进旅程 | 确认 |
| 意图 | 「读者感受、红线…」 | intent 提案 / ChangePack | 批准 |
| 设定 | 「角色/规则/关系/物件…」 | **全类型** 分条提案 → 候选 | 批准至 **WCG 绿** |
| 结构 | 「三卷十章梗概」 | 卷章提案 | 批准 |
| 章 N 开写 | 「写第 N 章 / 继续」 | pilot 大纲 | **放行大纲** |
| 节拍·演绎 | 「按大纲推」或默认推进 | beats→deduce | 停靠则按 §1 修 |
| 草稿 | 「写完整章」 | draft；advisory | **接受/恢复** 或重写 |
| 体检 | 「过不过」 | full_check | 改稿指令 |
| 交付终选 | 「定这版」 | deliver→终选 | **终选** |
| **定稿后（强制）** | 自动或「同步设定」 | **PostFinalize + 全类型候选持久化** | **在「待确认设定」批 L1** |
| **讨论中改设定（强制）** | 「把…改成…」 | **ChangePack + 候选** | **批准后 Surreal** |
| 结案 | 「结案」 | 九线+字数 | 确认 |

旅程看板必显：**站位 · WCG · pilot 状态/停靠 · 设定债 · 字数进度**。

---

## 5. 正典闭环（聊天 + 正文 · 强制 · 全类型 · 已部署）

> 本节与章循环同级。**实现入口以本节 API/文件为准。**

### 5.0 类型覆盖（全类型）

| module | 默认层 | 人批 |
|--------|--------|------|
| `character` / `faction` / `item` / `term` / `world_rule` | L1 | **必批** |
| `relation` / `promise` / `motif` / `char_state` / `fact` / `intent` | L1 | **必批** |
| `knowledge` | L2 客观 | 可 objective apply；仍可审计 |

模块硬门：上表 L1 即使 `layer=L2` / `requires_approval=false` / `approved=true` **无 `approved_item_ids` 不写**。

### 5.1 代码地图（v6.2）

| 部件 | 路径 |
|------|------|
| 安全内核 | `scribe3/canon_loop.py` |
| 全类型抽取 | `scribe3/canon_extract.py`（标记 + 启发式 + 可选 LLM） |
| Surreal apply | `scribe3/canon_apply_store.py` |
| 候选表 mixin | `scribe3/store/canon_candidates.py` · migration `106_canon_candidate.surql` |
| 产品钩子 | `scribe3/api/services/canon_hooks.py` |
| HTTP | `scribe3/api/routers/canon_loop.py` |
| 定稿挂载 | `pilot_runtime.finalize` → `body_confirmed_report` |
| 讨论挂载 | `director` from-discussion → `discussion_change_pack` |
| ingest 并轨 | `ingest._resolve_char` → 双写 `canon_candidate` |
| UI | `CodexDirectory.jsx`「待确认设定」· `api.js` `listCanonCandidates` / `decideCanonCandidate` |

### 5.2 聊天路径（讨论触发）

```text
主编对话出现相对 L0/L1 的共识或矛盾
  → discussion_change_pack / POST /canon/change-pack
  → 全类型 items + impact；persist → canon_candidate(pending)
  → 作者在「待确认设定」或 apply(approved_item_ids) 批准
  → Surreal 真写；设定债降级
  → 同路径继续旅程
```

**HTTP**

```http
POST /canon/change-pack?work=<slug>
  { "text": "...", "persist": true, "use_llm": true|false }

POST /orchestration/proposal/from-discussion?work=<slug>
  → 响应含 change_pack（不静默写 L1）

GET  /canon/candidates?work=<slug>&status=pending
POST /canon/candidates/{id}/decide?work=<slug>
  { "decision": "approve"|"reject" }

POST /canon/change-pack/apply?work=<slug>
  { "pack": {...}, "approved_item_ids": ["..."] }
```

**验收（路径级，不能只 unit）：**

1. demo 对话/文本主张 → 出包且 **多 module**  
2. 未批 apply → L1 字段不变（`silent_l1_blocked`）  
3. 批准后 → Surreal 回读（`/canon/store-snapshot` 或 Codex）  
4. 证据 `11-canon-loop-chat.json`

### 5.3 正文路径（定稿触发）

```text
BodyConfirmed（终选 / finalize）
  → body_confirmed_report / post_finalize_report
       · L2 客观（knowledge…）
       · L1 待批（全类型 modules）+ silent_l1_write=false
  → persist → canon_candidate
  → 作者批 L1 → Surreal
  → 下章 brief/限知可读到更新
```

**HTTP**

```http
POST /canon/post-finalize-report?work=<slug>
  { "seq": N, "prose": "...", "persist": true, "use_llm": true|false }

POST /canon/extract?work=<slug>
  { "seq": N, "use_llm": true|false }
  // 手动对一章全量抽取并落 pending

# pilot finalize 响应字段：
# post_finalize_report + canon_loop.path=body_confirmed
```

**验收：**

1. 有正文 + 主张 → 报告分节齐全；`silent_l1_write=false`  
2. 未批 L1 拒绝；批准后写入可观测  
3. 证据 `11-canon-loop-body.json`

### 5.4 安全（保持）

| 攻击 | 要求 |
|------|------|
| `approved=true` 无 id 列表 | 拒绝写 L1 |
| `requires_approval=false` 伪装 | 拒绝写正典模块 |
| `layer=L2` + `module=character/world_rule/…` | **仍须批准** |

单测：`test_canon_loop.py` + `test_canon_hooks.py`（必绿）。  
**单测绿 ≠ 闭环验收完成。**

### 5.5 设定债

```http
GET /canon/debt?work=<slug>
→ { total, high, by_module }
```

旅程看板应展示 `total`/`high`；高风险债挡 N+1 为 **可选配置**（未强制前须在证据注明）。

### 5.6 产品清单（闭环）

| 项 | 状态 |
|----|------|
| 定稿自动 PostFinalize（API） | **已** |
| 讨论自动 ChangePack（API） | **已** |
| 全类型候选 + Surreal apply | **已** |
| Codex 待确认设定收件箱 | **已** |
| 路径冒烟（多 module 批写） | **已**（demo 证据目录） |
| SPA 变更卡/定稿分节弹层美化 | 残差 |
| 旅程设定债数字 + 挡 N+1 | 残差 / 可配置 |
| 纯 UI 新书 5 万字 | **进行中（本版主目标）** |

---

## 6. 设定门闩 WCG（写前）

```bash
python3 scripts/v4_world_complete_gate.py --slug <slug> \
  --out artifacts/e2e-journey-5w-v6-YYYYMMDD-<slug>/00-world-complete-gate.json
# exit 0
```

角色≥4 丰满字段、关系≥3、规则/事实/伏笔/**母题≥3**、3 卷 10 章等：**以 gate 脚本为准**。  
开书强制：`v5_bible_build` 须 `s3_add_motif`；`v4_world_complete_gate` 检查 `motifs.ge3`；旅程 `bible_motifs` 缺口可一键批母题草案。  
**未绿禁止进入连载写正文站。** 理想由主编对话 + 待确认设定补齐，脚本仅审计。

---

## 7. 章循环 SOP（pilot · 旅程驱动）

```text
S0  结构 synopsis 已在
S1  大纲提案 → outline_proposed
S2  放行大纲
S3  节拍 → beats_ready     【接地失败 → §1 STOP，禁止 safe_beats】
S4  演绎 → deduced
S5  草稿 → drafting        【接受/恢复 advisory】
S6  体检 → checked         【仅 AI 味 heavy → 读感，不自动质量绿】
S7  交付 → delivered
S8  终选 → finalized
S9  【强制】PostFinalize + 全类型候选 → 「待确认设定」批完 L1 → 字数/tape
```

短稿：同链【强制重写】；全书超 55k：同链压缩，禁止离线灌删。

---

## 8. 质量与规模

| 项 | 规则 |
|----|------|
| 规模 | 合计 **[45000, 55000]** 去空白 |
| pad 公式尾 | FAIL |
| 限知 blocking | 改稿，不 soft 过 |
| AI heavy | 读感说明或改稿后再检 |
| 好书 | 气味锚、POV、动机、钩子、弧 |

---

## 9. 证据包（v6.2）

```text
artifacts/e2e-journey-5w-v6-YYYYMMDD-<slug>/
  00-runtime-baseline.md
  00-world-complete-gate.json
  00-author-path.md              # 必须写清：是否纯旅程+主编
  00-stop-log.md                 # 每次 STOP→最优解→回归
  01-intent.md … 03-structure.md
  04-serialize/ch01…ch10.md
  05-ledger.md
  06-defect-ledger.md
  07-director-trace.jsonl
  08-wordcount-rollup.md
  09-final-closure.md            # 九线
  10-env-lockdown.md
  11-canon-loop-chat.json        # §5.2 路径证据（强制）
  11-canon-loop-body.json        # §5.3 路径证据（强制）
  11-canon-loop-unit.log         # 单测（必要但不充分）
  11-canon-fulltype-modules.json # 多 module 批写回读（推荐）
  screenshots/                   # 旅程+聊天+待确认设定+正文
```

**结案门槛：**

- 无 `11-canon-loop-chat/body` → **正典闭环线 FAIL**  
- `00-author-path` 写「仅脚本串行」→ **旅程/主编线 PARTIAL**，不得总 PASS  

---

## 10. 分阶段执行（新书）

```text
Phase 0   环境锁 EMERGENCY=0 / SOFT=0；确认 demo 健康 + migration 106
Phase A   旅程建书 + 主编 intent（ChangePack/待确认设定）
Phase B   主编设定 → 全类型候选批到 WCG 绿
Phase C   结构 3 卷 10 章
Phase C′  【闭环验收】聊天改一条设定 → 包 → 批 → Surreal 回读
Phase D   旅程连载 10 章完整 pilot（遇障 §1）
Phase D′  【闭环验收】每章定稿 PostFinalize → 批 L1 全类型
Phase E   九线 + 作者路径诚实 + SPA 证据
```

**C′/D′ 与 D 同级：不可跳过。**  
**验收书必须是本版新建 slug**，不得用 `book_052a2adb` 冒充体验 PASS。

---

## 11. 现状切分（诚实 · 2026-08-07）

| 能力 | 状态 |
|------|------|
| WCG / pilot / 接地 STOP | 产品可用 |
| ChangePack 安全内核 + 全类型单测 | **已交付** |
| 聊天/定稿钩子 + 候选 Surreal + apply 真写 | **已部署 demo** |
| Codex 待确认设定 | **已部署** |
| 聊天自动出包（LLM Diff 体验） | **部分**（钩子有；SPA 卡仍可增强） |
| 旅程设定债 UI / 挡 N+1 | **部分**（API 有；看板可增强） |
| 纯 UI 跑通 5 万字新书 | **进行中** |

工程参考：`book_052a2adb`（约 53856 字）= 旧能力证明，**≠** v6.2 体验 PASS。

---

## 12. 工具边界

| 工具 | 角色 |
|------|------|
| 旅程 + 主编 + 点批 + 待确认设定 | **作者主路径** |
| `v4_world_complete_gate.py` | 审计 |
| `/canon/*` API | 闭环契约；UI 已挂收件箱 |
| `v2_serial_pilot.py` | 工程回归 only |
| 禁止 | EMERGENCY；prose_pure 证据；验收 force-skip WCG |

---

## 13. 捷径黑名单（勾选）

见 [`docs/e2e-journey-5w-v5-shortcut-ban.md`](./e2e-journey-5w-v5-shortcut-ban.md)（随 v6.2 维护）。

核心再列：

- [ ] 遇障换捷径继续  
- [ ] 聊天改设定无 ChangePack / 候选  
- [ ] 定稿无 PostFinalize  
- [ ] L1 静默写 / layer 伪装  
- [ ] 仅人物队列、不覆盖全类型  
- [ ] 闭环只跑单测、无 chat/body 路径证据  
- [ ] 脚本串行冒充作者路径 PASS  
- [ ] 用旧书 `book_052a2adb` 冒充本版新书 PASS  

---

## 14. 修订记录

| 版本 | 说明 |
|------|------|
| 1–3 | 假路径 / 脚手架（作废） |
| 4–5 | 设定门闩 + 工程真 pilot |
| 6.0 | 旅程+主编唯一路径 |
| 6.1 | 遇障最优同路续；聊天/正文强制闭环且路径级验证；C′/D′ |
| **6.2** | **对照落地实现修订：全类型候选/Surreal apply/收件箱已部署；§5 改为实现真相；验收必须新书；残差诚实列出** |
