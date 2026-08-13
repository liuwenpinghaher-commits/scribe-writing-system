# 写路径上下文单元卷宗 · deduction_final

> W1 红线单元。只读审计，未改产品代码，未跑全量测 / 本机 Surreal。  
> 库存：`INVENTORY.md` B 表 · `L0` / `mid` / `redline` / **NEVER**。  
> 代码对照：仓库 HEAD 与库存开跑 commmit 以 `INVENTORY.md` 为准。

## 身份卡（现网）

| 项 | 值 | 源 |
|----|----|----|
| 注册名 | `deduction_final` | `scribe3/injection_registry.py:73` |
| 层 / zone / epistemic | L0 / mid / redline | 同上 |
| 裁剪档 | **NEVER**（`L0_NEVER_CUT`） | `scribe3/context_budget.py:171` |
| join 层标 | `redline` | `context_budget.py:449`；`write_assemble_v1.py:523` |
| 独立信封额度 | 无（不在 `BLOCK_BUDGETS_NOVEL`） | 库存 A 表 |
| 软激活 | 红线免疫，不可软丢 | `scribe3/soft_activation.py:39` |
| 物理序 | mid：`story_move` 后、`material_recall` / `final_reminder` 前 | `context_budget.py:823` |
| 进 prompt 相位 | **仅 `draft` / `final`** | `write_assemble_v1.py:488-523` |
| 同源不进本段 | `deduce` 相位改走 `scene_truth_proj` | `write_assemble_v1.py:533-546` |
| 生产入口 | `_assemble_write_instructions` → v1 | `write_assemble.py:187-205` |

数据真源是章记录 `scene_truth` + `scene_truth_revision` + `deductions[]`，不是检索/codex。渲染器是 `_deduction_context_segments`（`write_assemble_context.py:331-381`），经 `inject_deduction_items`（`deduce_helpers.py:356-379`）标 `fresh|stale`。

---

## 1. 流程完善性

**判定：主干闭环完整，软门与写路径未接线。**

端到端现网链路：

1. **产**：Pilot `deduce`（`pilot_actions/deduce.py`）写 `scene_truth`，按 `involved_characters`（空则内存推断、**不落库**）逐角色 LLM 五层投影；接地失败走 `_verbatim_deduction_fallback`（`prompt_blocks.py:447`）或五栏留白。手编走 `update_chapter_meta` / MCP `s3_patch_chapter_plan`。
2. **存**：`store/chapters.py:945-1024` 真相实质变化才 bump `scene_truth_revision`；`prepare_deductions_for_write` 禁止「全文重存」把缺 `based_on` 的旧文洗成当前 rev。
3. **注**：draft/final 才调 `_deduction_context_segments`；无真相且无投影 → 整段不出现（`:341-342` 返回 `[]`）。stale **不注入全文**，只留过期提示（`:357-366` + `inject_deduction_items` 置 `prose=None`）。
4. **验**：`verify_craft_compliance` B3 卡真相长度；`find_leaks_for_chapter` 用焦点「没察觉的」作泄露探针且跳过 stale（`tests/test_find_leaks_deduction.py`）。`review_deduction_grounding` 五层结构只机读、不 fail-closed（`chapters.py:414-425`）。

断裂点（不改库存身份，只影响本单元是否「按合同进稿」）：

- `soft_gate_issues`（`deduce_helpers.py:243-270`）能报 `empty_truth / missing / stale / weak_layers`，**生产 assemble / chat_write 零调用**（仅单测）。草稿不提示、不挡。
- Pilot 已有 prose 则 `continue` 不覆盖（`pilot_actions/deduce.py:91-94`），**stale 不会自动重演**；写路径只贴「请重演后再采信」。
- `_deduction_context_segments(st, seq)` **不接收 `focalizer`**，与 v1 已有焦点者参数脱节。
- 注入全集是 `deductions[]` 里所有非空 prose，**不按 `involved_characters` 过滤**。

相位隔离是对的：`test_gapfix.py:156-179` 锁死 deduce 用「唯一事实源」措辞、draft/final 用「本章演绎」块；二者不叠段。

---

## 2. 生成质量

**判定：限知合同写清楚了，载荷形态与注意力位置会伤正文。**

已做对的：

- 头：「据此以作者视角写限知初稿」；尾：「真相为骨架；未过期焦点投影当 POV；他人投影约束言行并埋反讽；过期勿采信」（`write_assemble_context.py:346-379`）。
- stale 默认不给旧限知全文，避免草稿采信过期边界。
- 五层标题 SSOT：`DEDUCTION_HEADINGS`（`deduce_helpers.py:10-16`）；verbatim 兜底强制可逐字定位。
- Manifest 按源拆：`scene_truth` / `deduction` / `deduction_stale` / `deduction_protocol`（`test_write_context_outcome.py:118-162`）。

质量风险：

1. **全员五层进红线**。含每人「没察觉的」。设计本意是作者全知写限知、方便反讽；但模型同时看见焦点者不该「忽然明白」的句子，与 `phase_role` 草稿「不得越界写焦点者不知之事」（`misc_helpers.py:258-260`）对冲。非焦点长文尤其是噪声。
2. **无单条/整包长度约束**。`_clip_chars` 未用于本段。弱五层（`weak_layers`）照样全文 `_push`。
3. **注意力偏晚**。物理序在 mid 末、一堆 L3 之后（`context_budget.py:813-825`）。L3 若未裁，演绎合同被工艺段埋住；L3 若被裁，本段仍在，但前面红线+信封已占满注意力。
4. **与 envelope 无去重**。真相全文再进 `〔场景真相·全知〕`；投影里 verbatim 又摘同一批句子 → 事实骨架重复，信号密度下降。

回归锁的是「有没有进 prompt」，不是「进得是否可写」。

---

## 3. 爆炸半径

**判定：本单元对全 prompt 的挤占半径过大。**

| 机制 | 对本段 | 对其它段 |
|------|--------|----------|
| `apply_l2_trim` | 名在 `L0_NEVER_CUT`，且 layer=`redline`，永不作 victim | 本段计入 `l0_est` → **直接缩小** `effective_l2_cap`（`context_budget.py:605-616, 678-711`） |
| `enforce_total_prompt_budget` | `name in L0_NEVER_CUT or layer == "redline"` 跳过（`:228`） | 先半裁/丢 T3→T1 乃至 PROT；只剩红线时 `over_budget=True` 仍整包送出 |
| `apply_soft_activation` | 红线保留 | 无 |
| 信封八块 | 不经过 | 无 |

因此：N 个角色 × 五层长文全部算 L0。`estimate_tokens` 实为字符数（`context_budget.py:592-594`）。若本段 8–12k 字 + 其它 L0 + 信封 22k，则 `PROMPT_HARD=48_000` 下 L2 房间可被压到接近 0，outline / brief_must / purpose / codex 先死。

二次爆炸：

- **同名多 `_push`**（头 + 真相 + 每角色 + 尾）。`join_generation_segments` 用 dict 推导 `domain_lengths`（`context_budget.py:547-549`）→ **只保留最后一片** 的字数。观测少计，密度/超顶误报。
- 改本段文本格式会影响 `test_gapfix` / `test_write_context_outcome` / leak 探针；改 NEVER 身份会波及全部 L0 裁剪。**安全改动面应停在 renderer + 一次 push，不动 registry。**

---

## 4. 业务完善性

**判定：产品语义（场景真相 · 多棱镜 · 限知初稿）已成型，写时消费策略偏「全倒」。**

业务合同（应然）：

- 全知真相是事实骨架；限知投影是 POV 与反讽边界；修订必须让投影过期而不是假装仍准。
- 草稿用**未过期焦点投影**当眼睛，他人投影只约束其嘴和手。
- 过期/缺失必须可见，不能 silently 当有效。

已落地：revision stamp、stale 不给全文、相位分流、接地兜底、MCP 拒空投影、B3 真相门槛、泄露探针吃「没察觉的」。

未落地成写作行为：

- 软门不进 assemble，作者可在 missing/stale/弱五层下直接 draft。
- 注入不区分焦点 / 龙套，与「一章单一焦点者」纪律不一致。
- `involved` 空时 Pilot 推断不落库，下次 deduce 再推断；若角色改名/未点名，投影集与场上人物易漂。
- `DRAMA_CORE_NAMES` 不含本段（`injection_registry.py:84-86`）——密度 KPI 不把它当戏剧核，但它以红线挤戏剧核预算。

---

## 5. 五维评分（1–5）

| 维 | 分 | 一句话 |
|----|:--:|--------|
| 流程完善性 | **4** | 产-存-注-验主链有、相位对；软门与 stale 重演未接写路径。 |
| 生成质量 | **3** | 合同语句清楚、stale 处理对；全员五层 + 晚位 + 真相重复伤限知稿。 |
| 爆炸半径 | **2** | NEVER×无帽×计入 L0，能抽干 L2；观测还少计。 |
| 业务完善性 | **4** | 多棱镜语义完整；消费侧未按焦点者分级。 |
| 预算与裁剪纪律 | **2** | 无段帽、无合并计量、红线身份与可变长载荷不匹配。 |

**均分 3.0。** 优先修「红线无帽」而不是再加协议句。

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 2 |
| B_product | 4 |
| Observability | 2 |

---

## 6. 恰好一个最优改造

**焦点优先压缩 + 整包硬帽 + 单段 `_push`。**

不改 `SEGMENT_REGISTRY`、不改 `L0_NEVER_CUT`、不改 `scene_truth_proj`、不动 store revision。

1. `scribe3/api/services/write_assemble_context.py:331`  
   `_deduction_context_segments(st, seq, *, focalizer="")`：
   - 协议头/尾、stale 提示保持现语义。
   - `fresh` 且 id 命中 `focalizer`：保留五层全文，单条再封顶（建议 1800 字）。
   - 其余 `fresh`：**一行边界**（可见/已做；点名「勿写其不知」），**禁止**注入其「没察觉的」长文。
   - 整包硬帽对齐 `DEFAULT_CODEX_INJECT_CAP`（4500 字）：超帽顺序砍 非焦点行 → 真相摘录 → 焦点半裁。
2. `scribe3/api/services/write_assemble_v1.py:516-523`  
   仍对每源 `_domain_input`（Manifest 分源追溯不变），但把文本拼好后 **`_push("deduction_final", "redline", joined)` 恰好一次**，让 `domain_lengths["deduction_final"]` 等于真实进模字数。
3. 把已有 `focalizer` 从 `_assemble_write_instructions_v1` 传入。不要在本改造里重跑 Pilot 或改 NEVER。

**刻意不选的次优：** 把本段降为 T1/supplemental（限知边界会被 L2 整段丢掉）；或只在 footer 再加一句「注意限知」（重复、不减 L0）。

**验收（轻量，勿本机 Surreal / 全量）：**

- 既有：`test_gapfix.py` 中 draft/final 仍含「本章演绎」+ 焦点投影正文 + 真相原文；deduce 仍无「本章演绎」、仍有「唯一事实源」。
- 新增：多角色时非焦点「没察觉的」不得出现在 draft joined；`budget_report` 里本段字数 = 拼接后全文且 ≤ 帽。
- Manifest：`test_final_manifest_separates_scene_truth_deductions_and_protocol` 仍分得出 `scene_truth` / `deduction` / `deduction_protocol`。

---

## 7. 证据锚点（path:line）

- 注入：`scribe3/api/services/write_assemble_v1.py:516-523`
- 渲染 / stale：`scribe3/api/services/write_assemble_context.py:331-381`
- 产投影：`scribe3/deduce_helpers.py:356-379`；Pilot 跳过已有：`scribe3/api/services/pilot_actions/deduce.py:91-94`
- NEVER + 层标 + 序：`scribe3/context_budget.py:171`、`:449`、`:823`
- L0 挤 L2：`scribe3/context_budget.py:605-616`、`:228`
- 同名少计：`scribe3/context_budget.py:547-549`
- 注册 / 软激活：`scribe3/injection_registry.py:73`；`scribe3/soft_activation.py:39`
- 软门未接线：`scribe3/deduce_helpers.py:243-270`（生产 grep 仅测试引用）
