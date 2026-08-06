# Director 五站全链路 · 约 5 万字真实连载验收方案

| 项 | 值 |
|----|-----|
| **版本** | **4.0**（作废 1.0–3.x 执行 PASS） |
| **日期** | 2026-08-06 |
| **状态** | **已重定 · 设定优先 · 待按本版执行** |
| **产品** | scribe3 |
| **环境** | **仅 demo 已部署栈**（`www.qing.blue`） |
| **进度台账** | [`设计文档/2026-08-06-旅程5万字-进度.md`](../设计文档/2026-08-06-旅程5万字-进度.md) |

---

## 0. 为何再重定（v4）

### 0.1 用户一票否决（本轮根因）

> **设定都没定好就开始创作，写出来的不是验收要的书。**

| 轮次 | 错在哪 |
|------|--------|
| v1 | 假路径 + 模板灌文 |
| v2 | 离线长文灌库 + 伪导演 tape |
| **v3** | **pilot 能产文，但「世界/设定」只有薄壳**（角色缺 backstory/能力/关系；几乎无世界规则/势力/物件；伏笔单条；章大纲与设定未闭环）就冲 10 章正文 → **顺序反了** |

产品与融合规程的正确顺序（见 `docs/融合执行规程-真人验收×对话驱动改造.md`）：

```text
建书 → 北极星(intent)
     → 世界设定(world bible：角色/关系/规则/势力/物件/术语/伏笔…)
     → 结构(卷+章 synopsis，可与设定交叉补全)
     → 才进入 章循环(大纲/节拍/演绎/草稿/定稿)
```

**铁律（v4 硬条）：**

```text
未过「设定完成门闩 WCG」 → 禁止任何 chapter.prose 定稿 / draft_loop 作为验收证据
```

### 0.2 v3 书处置

| slug | 处置 |
|------|------|
| `book_887bb8e8` | 标题改为 **「设定未齐即开写·不作PASS」**；正文可保留作反面样例，**不得**再报 PASS |
| `book_2524fd8a` | 继续 **离线灌稿·不作PASS** |

### 0.3 v4 一句话

先在 **新书** 上用真路径 **把设定写满且 Web 可见**，门闩绿了再 pilot 连写约 5 万字；中途设定返工必须 **STOP 正文 → 改设定 → 同路径回归 → 再续写**。

---

## 1. 完成定义与七线（在 v3 上再加「设定线」）

```text
旅程总 PASS
  ⇔ 设定线  ∧  Web可见  ∧  导演  ∧  真路径  ∧  工艺  ∧  质量  ∧  规模  ∧  缺陷
```

| 线 | PASS 条件 |
|----|-----------|
| **设定线（新增）** | **WCG 全绿**（§3）；Web Codex/设定面板可见非空字段；**先于**任何验收正文 |
| **Web 可见** | 书库主书正确；设定/卷章/正文 1·5·10 可见；不误导空书 |
| **导演** | live append-only tape；≥5 种 `pilot_state`；时间跨度 >10s |
| **真路径** | `EMERGENCY=0`；世界写 orch approve / Hermes；正文 pilot 链 |
| **工艺** | 无默认 skip；定稿可审计 |
| **质量** | 文学正文；无公式注水；**正文须引用已建设定**（人物名/规则/伏笔可回指） |
| **规模** | 正文合计 **[45000, 55000]** |
| **缺陷** | 无开放 P0/P1 |

### 1.1 顺序合同（不可颠倒）

```text
Phase A  建书 + intent
Phase B  设定完成门闩 WCG（可多日，可 STOP 修产品）
Phase C  结构确认（3 卷 · 10 章 synopsis · 与设定对齐）
Phase D  串行正文（仅此时允许 draft_loop）
Phase E  账本 + 结案
```

**禁止：** 为冲字数先写后补设定、用「角色有名字」冒充世界完成、用 v3 字数冒充 v4 PASS。

---

## 2. 设定完成门闩 WCG（World Complete Gate）

> **全部勾选前，驱动脚本必须拒绝 `--phase serialize`。**  
> 审计命令：`python3 scripts/v4_world_complete_gate.py --slug <slug>` → exit 0 才可开写。

### 2.1 北极星（intent）

| 项 | 最低要求 |
|----|----------|
| reader_feeling | 非空，≥10 字 |
| emotional_arc | 非空 |
| red_lines | ≥3 条可执行红线 |
| total_word_goal | 45000–55000 或明确 50000 |

### 2.2 角色 Codex（characters）

| 项 | 最低要求 |
|----|----------|
| 数量 | ≥4（含 1 主角 + ≥1 重要配角 + ≥1 对手/阴影/导师类） |
| 每角色必填 | name, appearance, personality_detail, surface_goal, deep_need, fear, **backstory** |
| 推荐 | abilities, weaknesses, importance∈{protagonist,major,minor}, voice 若产品有 |
| Web | 设定面板打开任一角色可见上述字段非空 |

### 2.3 关系网

| 项 | 最低要求 |
|----|----------|
| 角色关系 | ≥3 条 character↔character（`s3_add_character_relation` 或等价 approve） |
| 说明 | 关系类型 + 双方 id 可回读 |

### 2.4 世界规则 / 正典事实

| 项 | 最低要求 |
|----|----------|
| 世界规则 | ≥3 条（如「不渡夜魂」「债契三夜」「灯芯写名」）`s3_add_world_rule` 或 fact 等价 |
| 核心事实 | ≥5 条可引用命题（地点/器物/习俗/禁忌） |

### 2.5 势力 / 物件 / 术语（按题材至少两类非空）

| 项 | 最低要求 |
|----|----------|
| 势力 faction | ≥1（高门/收灯一脉/镇衙等） |
| 关键物件 item | ≥2（纸钱、灯芯、伪契等） |
| 术语 term | ≥2（「到」、替死、收灯等） |

### 2.6 伏笔账本

| 项 | 最低要求 |
|----|----------|
| 书级/卷级 promise | ≥3 条，含 setup 章与 payoff 窗口 |
| 状态 | open 可追踪；Web 账本可见 |

### 2.7 结构对齐（WCG 出口的一部分）

| 项 | 最低要求 |
|----|----------|
| 卷 | 3 卷，标题+intro |
| 章 | 10 章，每章 title + synopsis（≥40 字）+ focalizer 指向已建角色 |
| 自检 | 每章 synopsis 至少点名 1 个已建角色或 1 条已建规则/伏笔 |

### 2.8 WCG 出口清单

- [ ] intent 齐  
- [ ] 角色 Codex 齐（含 backstory）  
- [ ] 关系 ≥3  
- [ ] 规则 ≥3 + 事实 ≥5  
- [ ] 势力/物件/术语满足 §2.5  
- [ ] 伏笔 ≥3  
- [ ] 卷章 synopsis 与设定对齐  
- [ ] Web：设定面板抽样截图或 API 实读入证据 `02-world.md`  
- [ ] `v4_world_complete_gate.py` exit 0  

**未全勾 → 禁止 Phase D。**

---

## 3. 拍板（v4）

| # | 决定 |
|---|------|
| D1 | **新书** `《旅程五站·v4·YYYYMMDD》` 新 slug；v3 书标注不作 PASS |
| D2 | **先设定后结构后正文**；驱动默认 `world-gate → structure → serialize` |
| D3 | 正文仍仅 pilot 真链；禁止 prose_pure 灌库 |
| D4 | 设定一律 orch **approve+execute**（EMERGENCY=0） |
| D5 | 字数仍 [45000,55000]；**质量与设定一致性优先于字数** |
| D6 | 设定返工：STOP 正文 → 改设定 → 回归 WCG → 再续写 |
| D7 | 证据目录 `artifacts/e2e-journey-5w-v4-YYYYMMDD-<slug>/` |

---

## 4. 真路径操作合同

```text
【设定】
  主编意图（对话/脚本提案）
  → orch proposal ops（s3_set_intent / s3_add_character / s3_patch_character /
     s3_add_character_relation / s3_add_world_rule / s3_add_fact /
     s3_add_faction / s3_add_item / s3_add_term / s3_plant_promise / …）
  → decision=approve execute=true
  → GET 回读 + Web 面板

【结构】
  s3_add_volume / s3_add_chapter / s3_patch_chapter_meta（synopsis/focalizer）
  → 过 §2.7

【正文 · 仅 WCG 后】
  pilot/dismiss → step/approve → draft_loop → restore → full_check → deliver → finalize
  驱动语必须绑定：本章 POV、已建角色、已建规则、本章应触伏笔

【禁止】
  未过 WCG 的 draft_loop 作证据
  EMERGENCY REST 灌设定
  离线长文 save-chapter
  伪 multi-state tape
```

---

## 5. 五站与证据

| 站 | 内容 | 硬门 |
|----|------|------|
| 0 基线 | env、归档 v2/v3 干扰书、证据目录 | EMERGENCY=0 SOFT=0 |
| 1 intent | 北极星 | Web/API |
| 2 world | **WCG 全绿** | `02-world.md` + gate 报告 |
| 3 structure | 卷+10 synopsis 对齐设定 | `03-structure.md` |
| 4 serialize | 10 章 pilot 真写 | 每章 journal；禁止先写后设 |
| 5 ledger | 伏笔/质量/结案 | `05`/`06`/`09` |

证据包：

```text
artifacts/e2e-journey-5w-v4-YYYYMMDD-<slug>/
  00-runtime-baseline.md
  00-rootcause-fixes.md
  00-world-complete-gate.json   # WCG 机器可读
  01-intent.md
  02-world.md                   # 丰满设定实读
  03-structure.md
  04-serialize/chNN.md
  05-ledger.md
  06-defect-ledger.md
  07-director-trace.jsonl
  08-wordcount-rollup.md
  09-final-closure.md           # 含设定线
  10-env-lockdown.md
  screenshots/…
```

---

## 6. 驱动与产品改动

| 组件 | 要求 |
|------|------|
| `scripts/v4_world_complete_gate.py` | 审计 WCG；失败打印缺项；exit≠0 |
| `scripts/v4_serial_pilot.py`（或改造 v2 脚本） | serialize 前强制 gate；scaffold 拆成 `world` / `structure` / `serialize` 相位 |
| score_closure | 新增 **设定线**；WCG 文件缺失或 fail → TOTAL 不得 PASS |
| （可选产品）director world_ok | 不仅 `char_count≥1`，应靠近 WCG 子集，避免旅程「世界 done」但设定空 |

---

## 7. 工期（诚实）

| 阶段 | 估计 |
|------|------|
| 设定 WCG（真路径 + 可能修工具/字段） | 1–3 日 |
| 结构对齐 | 0.5 日 |
| 10 章真 pilot | 数小时–数日 |
| 结案 | 0.5 日 |

**不做**「先写满再补设定」的最快路径。

---

## 8. 修订记录

| 版本 | 说明 |
|------|------|
| 1.0–2.x | 假路径 / 离线灌稿（作废） |
| 3.0 | pilot 真产文但 **设定未齐即开写**（执行作废） |
| **4.0** | **设定完成门闩优先；新书；先世界后正文** |
