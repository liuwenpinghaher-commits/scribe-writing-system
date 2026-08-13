# 写路径上下文单元卷宗 · outline

> 库存：`INVENTORY.md` B 行 `outline` · L1 / head / frame / **PROT**  
> 日期：2026-08-13 · 只读审计 · 未改代码、未跑全量测、未起本机 Surreal  
> 现网锚：`injection_registry.py` `SEGMENT_REGISTRY`；`context_budget.py` `GEN_SEGMENT_PROTECTED` / `generation_physical_order_names` / `apply_l2_trim`；`write_assemble_v1.py` + `write_assemble_context._outline_block`

---

## 1. 现网接线（事实）

| 项 | 现网 |
|----|------|
| 注册 | `SegmentMeta("outline", "L1", "head", "frame")` · `scribe3/injection_registry.py:54` |
| 物理序 | 默认 `SCRIBE3_OUTLINE_AFTER_DRAMA=1`：`drama_vacuum` 后、`envelope` 前 · `context_budget.py:774-798` |
| 保护 | `GEN_SEGMENT_PROTECTED` = `{outline, brief_must, voice_anchor}`，priority **8** · `context_budget.py:139-156` |
| **不是** L0 | **不在** `L0_NEVER_CUT`（防 synopsis/beats 膨胀锁死 48k） |
| 预算层 | `GENERATION_SEGMENT_LAYERS["outline"] = "supplemental"` · `context_budget.py:442`（登记 L1 ≠ 裁剪 layer） |
| 密度分子 | `DRAMA_CORE_NAMES` 含 outline · `injection_registry.py:84-86` |
| 组装 | `_assemble_write_instructions_v1` → `_outline_block(..., mode="write")` → `_push("outline", "supplemental", …)` · `write_assemble_v1.py:386-404` |
| 内容 | 章 `synopsis` + `beats[].text`，各 `_clip(..., _OUTLINE_BUDGET=1200)` · `write_assemble_context.py:152-186`；`app_impl.py:1261` |
| 信封去重 | focus **不再** `[:220]` 展开，指针「见 outline 域」· `context_assembler.py:646-659` |
| 下游折叠 | `compact_volume_intro(..., outline_text=_ol_raw)` · `write_assemble_v1.py:419-422` |
| 空段 | 无 synopsis 且无 beats → 空串 + `empty_outline` 软失败计数 · `write_assemble.py:25` / `write_assemble_v1.py:397-399` |

写路径 **已挂** `_outline_block`（历史「仅 focus 旁路 / 死函数」已过时）。`test_outline_block_wired_into_chat_write` 用长于 220 的 synopsis 尾标证明全文进 instructions 且只出现一次。

---

## 2. 流程完善性 — 4/5

**已闭环**

- 声明层（registry L1）→ 物理序（after-drama）→ 生产 join（`join_generation_segments`）→ V2 `apply_l2_trim` + 全域硬顶，链路完整。
- 写栈 `mode=write` 剥离 plan 协议三尾（字数契约 / 章节定位 / reversal），避免「生成大纲」指令漏进 draft。
- focus 指针 + volume_intro compact 明确以 outline 为 synopsis/beats 单真源。
- 保护档：T3→T2→T1 裁尽后才选 outline；单测 `test_overcap_drops_material_before_outline`。

**缺口**

1. **layer 双账本**：登记 `L1`，push/join 仍是 `supplemental`。保护只靠名字进 `GEN_SEGMENT_PROTECTED`，不是真正的 L1 预算桶（`l1_est` 只计 `layer==envelope`）。关旗或改名会立刻变普通 DEF（priority 55）。
2. **`mode=plan` 无生产 call site**（全仓仅测试）。讨论路径 `write_assemble_discuss.py` 进口 `_outline_block` 但未调用；outline/beats 讨论不走计划协议。
3. **`_clip` / `_OUTLINE_BUDGET` 不在 `write_assemble_context` 模块内**，靠 `app_impl._rebind_services` 把函数 `__globals__` 绑到 `app_impl`。经 `scribe3.app` /chat/write 正常；直调模块函数在有 synopsis 时会 `NameError`（同文件 `_volume_intro_block` 已改用本模块 `_clip_chars`）。
4. **`get_chapter` 失败**：`_outline_block` 文档写 fail-loud（`write_assemble_context.py:172`），调用方立刻 fail-soft 吞掉（`write_assemble_v1.py:387-395`），U-011 在写路径被抵消。

---

## 3. 生成质量 — 3/5

**有效信号**

- 标题「据此展开正文,勿另起炉灶」+ 〔大纲〕/〔节拍〕分栏，模型任务清楚。
- 有 beats 时追加「按各情节点字数预算分配笔墨、不得均匀注水」。
- 限知章附作者视角免责（与 drama 同口径）。
- 长大纲不再被 focus 220 腰斩（质量回归点）。

**会伤正文的点**

1. **超 cap 半裁与规格相反（本单元最大质量债）**  
   规格（`docs/plans/2026-08-12-first-principles-quality-enablement.md`）：保护段半裁时 **beats 摘要优先于 volume/大纲复述**。  
   现网 `apply_l2_trim` / `enforce_total_prompt_budget` 对任意 victim 一律 `text[:len//2]+"…"`（`context_budget.py:732-735`、`:252-254`）。  
   现网块序是：标题 → 〔大纲〕≤1200 → 〔节拍〕≤1200 → 笔墨句 → 限知免责。`tail_half` **先砍节拍与契约句，留下前半段 synopsis**。超预算时模型最该跟的节拍先死。

2. **「字数预算」是空指令**  
   write 模式要求按预算分配笔墨，但 `_outline_block` **只拼 `beats[].text`**。Pilot v2 已解析 `density`/`budget`（`pilot_runtime.py:252-290`），注入侧丢弃。GCD（goal/conflict/turn/cost/hook）也不进 outline（戏剧另段）。模型被要求执行未出示的预算。

3. **双 1200**  
   synopsis 与 beats **各** clip 1200，加上标题/免责，outline 段可达 ~2.5k 字。PROT 使其在挤爆时仍后砍，挤压 T1（codex/purpose/pressure）与信封。

4. **Pilot 把标签写进 synopsis**  
   `propose_outline` 把「压力级 / chapter_role / stakes / 章末钩子」拼进同一 `synopsis` 字段再整段注入（`pilot_actions/outline.py:22-31`）。利于钉 stakes，也增加工程词进正文的已知漏路径。

5. **空大纲不阻断**  
   无 synopsis/beats 仍继续写，只 `empty_outline++`。无纲成稿是产品允许项，但与「勿另起炉灶」契约互斥，模型只能靠 drama/envelope 即兴。

---

## 4. 爆炸半径 — 中（改 trim 则小；改块语义则中）

| 方向 | 谁被炸 |
|------|--------|
| 裁掉 / 半裁坏 | 本章跟随失败：另起炉灶、漏拍、限知免责消失 |
| 膨胀 | 吃 T1/信封；`drama_core_share` 虚高（outline 在分子里） |
| 改 `_outline_block` 文本 | `test_app.py` 大纲套件、`test_outline_block_wired_into_chat_write`、volume compact、density 分子 |
| 改 `GEN_SEGMENT_PROTECTED` / 物理序 | `test_quality_enablement_rev12.py`、`join` 全写路径 |
| 改 store 字段 | `chapter.synopsis` / `beats` 是章身份四阶段之一；**没有**独立 `outline` 列（`store/chapters.py:994-1000`）。他处 `ch.get("outline")` 是旧别名，写注入 **不读** |

**不在本单元**：`_drama_block` / PDC / narrative_contract 并行钉戏剧；改 outline 文本不必动它们。  
**禁止项**：不要把 outline 塞进 `L0_NEVER_CUT`（规格已否决）；不要复活「把 `_outline_block` 当 PDC 挂点」。

---

## 5. 业务完善性 — 3/5

作者旅程：拟纲（pilot/人工 `synopsis`）→ 扩拍（`beats`+可选 budget）→ 写正文应「按纲按拍」。

| 业务点 | 现网 |
|--------|------|
| 有纲有拍写入模型 | 有，且躲开信封重复 |
| 无纲仍写 | 允许，仅计数；主编无闸 |
| 节拍预算/密疏 | 解析有、注入无；write 口头要求无法执行 |
| 计划阶段协议 | 代码有、生产未挂 |
| 限知不泄作者纲 | 免责句有；半裁可能先丢掉 |
| 与卷纲重叠 | compact 已做 |

对「最高质量小说」：缺的不是「再多贴一段 synopsis」，而是 **超窗时保拍** + **把已有 budget/density 写进契约**。

---

## 6. 五维评分（1–5）

| 维度 | 分 | 一句话 |
|------|----|--------|
| 流程完善性 | **4** | 登记→序→join→保护已通；layer 双账本、plan 未挂、clip 靠 rebind |
| 生成质量 | **3** | 长纲能进、去重对；半裁杀拍、预算空喊 |
| 爆炸半径可控 | **4** | PROT 且非 L0，半径清楚；误半裁只伤本段后半 |
| 业务完善性 | **3** | 有纲可写；无纲不拦；拍上数字到不了模型 |
| 可观测/可测 | **4** | `empty_outline`、source_kind=outline、density、超 cap 单测在；半裁保拍无测 |

**综合：3.6 / 5**（能用、未到规格承诺的「生成段保护」语义）。

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

半裁保拍已落地。第 2 轮：无 budget/density 时不再空喊「字数预算」。

---

## 7. 恰好一个最优改造

### 标题

**outline 半裁改为「保拍砍纲」**（兑现已写规格，禁止 `tail_half` 先砍节拍）

### 为什么是唯一最优

- 直击本单元 **生成质量** 最大缺口，且规格已写死「beats 优先于 volume/大纲复述」，现网实现相反。
- 改动面 **只在** `scribe3/context_budget.py` 的半裁分支（`apply_l2_trim` 与 `enforce_total_prompt_budget` 共用同一 helper），**不**改注入文案、不改 registry、不进 L0。
- 比「把 budget 拼进 `_outline_block`」更小：后者还要碰 schema 额外键（`density`/`budget` ∉ `beats_schema.GCD_KEYS`）和 clip 双 1200 政策。
- 比「空大纲硬闸」更贴质量：无纲是产品选择；**有纲却被腰斩掉拍** 才是静默伤正文。

### 做法（实现规格，本轮不改代码）

1. 抽出 `_half_cut_segment(name, text) -> str`。
2. `name != "outline"`：保持现网 `text[:len//2]+"…"`（或过短整段丢）。
3. `name == "outline"`：按标记切块  
   `header` / `〔大纲〕…` / `〔节拍〕…` / 尾契约（笔墨句+限知免责）。  
   目标长度 ≈ `len(text)//2`（与现网半裁同量级）：  
   **必留** 标题 + 〔节拍〕（过长则只 clip 节拍栏）+ 尾契约；  
   **先砍** 〔大纲〕（可减到 0，留一行「大纲已裁，以节拍为准」）。  
   仍超则再 clip 节拍栏，**最后**才动尾契约。
4. 单测（轻量、无 Surreal）：构造 大纲 800 + 节拍 800 的 outline 段，cap 迫使半裁一次，断言 `〔节拍〕` 与至少一个 beat 文本仍在，`〔大纲〕` 可残或缺。
5. **不做**：改物理序、改 PROT 集合、把 outline 改 redline、复活 plan 尾进 write。

### 验收

- `test_overcap_drops_material_before_outline` 仍绿（material 仍先于 outline）。
- 新测：半裁后节拍在、大纲缩。
- 人工看 joined：超窗样本中「抵达义庄」类拍句仍在，「甲」×N 的 synopsis 垫可被砍。

---

## 8. 证据锚点（path:line）

- `scribe3/injection_registry.py:42` / `:54` — SEGMENT_L1 · after-drama 注释与注册  
- `scribe3/context_budget.py:139-156` — `GEN_SEGMENT_PROTECTED` + priority 8  
- `scribe3/context_budget.py:442` — layer 仍标 supplemental  
- `scribe3/context_budget.py:713-738` — 保护段最后半裁 = 盲目 `tail_half`  
- `scribe3/context_budget.py:771-798` — 默认 outline 在 `drama_vacuum` 与 `envelope` 之间  
- `scribe3/api/services/write_assemble_v1.py:386-404` — write 模式挂接 + empty_outline  
- `scribe3/api/services/write_assemble_context.py:152-186` — synopsis/beats 各 clip 1200，只取 text  
- `scribe3/context_assembler.py:646-659` — focus 指针去重  
- `scribe3/api/app_impl.py:1261-1267` — `_OUTLINE_BUDGET` / `_clip` 真源（rebind 依赖）

---

## 9. 明确不改（本卷）

- 不把 outline 列入 `L0_NEVER_CUT`。  
- 不把 `mode=plan` 塞进 draft 写栈。  
- 不在本单元复活或删除 `_outline_block`（已是真路径）。  
- 不为本审计跑全量测 / 本机 Surreal。
