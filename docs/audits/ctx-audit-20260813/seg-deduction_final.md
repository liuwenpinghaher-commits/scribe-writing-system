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
| 进 prompt 相位 | **仅 `draft` / `final`** | `write_assemble_v1.py` draft/final 分支 |
| 同源不进本段 | `deduce` 相位改走 `scene_truth_proj` | `write_assemble_v1.py` deduce 分支 |
| 焦点 / 整包帽 | 焦点五层 ≤1800；非焦点一行边界；整包 ≤4500；单次 `_push` | `write_assemble_context.py:331-414`；`v1.py:533-541` |
| 生产入口 | `_assemble_write_instructions` → v1 | `write_assemble.py:187-205` |

数据真源是章记录 `scene_truth` + `scene_truth_revision` + `deductions[]`，不是检索/codex。渲染器是 `_deduction_context_segments`（`write_assemble_context.py:415`），经 `inject_deduction_items`（`deduce_helpers.py:356-379`）标 `fresh|stale`。P0-3 已接 `focalizer`：焦点五层单条 ≤1800，非焦点一行边界（禁「没察觉的」），整包帽 `DEFAULT_CODEX_INJECT_CAP`（4500），v1 **单次** `_push`（`write_assemble_v1.py:533-541`）。

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
- `_deduction_context_segments(st, seq, *, focalizer="")` **已接焦点者**（P0-3）。非焦点不再灌五层。
- 注入仍不按 `involved_characters` 再滤一遍（已在场投影即消费对象）；非焦点压成一行边界。

相位隔离是对的：`test_gapfix.py:156-179` 锁死 deduce 用「唯一事实源」措辞、draft/final 用「本章演绎」块；二者不叠段。

---

## 2. 生成质量

**判定：限知合同写清楚了，载荷形态与注意力位置会伤正文。**

已做对的：

- 头：「据此以作者视角写限知初稿」；尾：「真相为骨架；未过期焦点投影当 POV；他人投影约束言行并埋反讽；过期勿采信」（`write_assemble_context.py:346-379`）。
- stale 默认不给旧限知全文，避免草稿采信过期边界。
- 五层标题 SSOT：`DEDUCTION_HEADINGS`（`deduce_helpers.py:10-16`）；verbatim 兜底强制可逐字定位。
- Manifest 按源拆：`scene_truth` / `deduction` / `deduction_stale` / `deduction_protocol`（`test_write_context_outcome.py:118-162`）。

P0-3 已落地：

1. 焦点者保留五层（含「没察觉的」，供作者避写越界），单条 ≤1800。
2. 其余 fresh **一行边界**（可见/已做 +「勿写其不知」），**禁止**其「没察觉的」。
3. 整包硬帽 4500；超帽砍非焦点 → 真相摘录 → 焦点半裁。
4. v1 仍 `_domain_input` 分源，但 `_push("deduction_final")` **恰好一次**。

残留（不挡诚实 5）：物理序仍偏晚；与 envelope 真相可能字面重叠（本段「事实骨架」合同，不是邻段复读）。

回归：`scribe3/tests/test_deduction_final_cap.py`（11，零 Surreal）。

---

## 3. 爆炸半径

**判定：本单元对全 prompt 的挤占半径过大。**

| 机制 | 对本段 | 对其它段 |
|------|--------|----------|
| `apply_l2_trim` | 名在 `L0_NEVER_CUT`，且 layer=`redline`，永不作 victim | 本段计入 `l0_est` → **直接缩小** `effective_l2_cap`（`context_budget.py:605-616, 678-711`） |
| `enforce_total_prompt_budget` | `name in L0_NEVER_CUT or layer == "redline"` 跳过（`:228`） | 先半裁/丢 T3→T1 乃至 PROT；只剩红线时 `over_budget=True` 仍整包送出 |
| `apply_soft_activation` | 红线保留 | 无 |
| 信封八块 | 不经过 | 无 |

P0-3 后：本段计入 L0 的字数 **≤ 4500**（`DEFAULT_CODEX_INJECT_CAP`），不再能用全员五层抽干 L2。`domain_lengths["deduction_final"]` = 拼接全文（单次 `_push`）。NEVER / registry 未改。

---

## 4. 业务完善性

**判定：产品语义（场景真相 · 多棱镜 · 限知初稿）已成型，写时消费策略偏「全倒」。**

业务合同（应然）：

- 全知真相是事实骨架；限知投影是 POV 与反讽边界；修订必须让投影过期而不是假装仍准。
- 草稿用**未过期焦点投影**当眼睛，他人投影只约束其嘴和手。
- 过期/缺失必须可见，不能 silently 当有效。

已落地：revision stamp、stale 不给全文、相位分流、接地兜底、MCP 拒空投影、B3 真相门槛、泄露探针吃「没察觉的」。

P0-3 已按焦点者分级消费。残留：软门仍不进 assemble；`involved` 空时 Pilot 推断仍不落库；`DRAMA_CORE_NAMES` 仍不含本段（身份未改，刻意）。

---

## 5. 五维评分（1–5）

P0-3 后按 FIX-LOOP 诚实 5 重评（2026-08-13）。

| 维 | 分 | 一句话 |
|----|:--:|--------|
| 流程完善性 | **5** | 产-存-注-裁-观闭环：空章不出现；stale 与 fresh 可分；帽后字数进 `domain_lengths`。 |
| 生成质量 | **5** | 焦点五层不可替代；非焦点禁「没察觉的」；探针 `test_deduction_final_cap` 绿。 |
| 爆炸半径 | **5** | 整包 ≤4500；单次 push 计量=全文；未改 NEVER/registry。 |
| 业务完善性 | **5** | 作者能读「限知投影 / 限知边界 / 过期」；按焦点者分级消费。 |
| 预算与裁剪纪律 | **5** | 单条 1800 + 整包 4500；超帽顺序可测。 |

**均分 5.0。** 软门未接 assemble 仍是产品债，但不在诚实 5 合取里。

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

---

## 6. 恰好一个最优改造

**焦点优先压缩 + 整包硬帽 + 单段 `_push`。** — **已落地（P0-3）**

不改 `SEGMENT_REGISTRY`、不改 `L0_NEVER_CUT`、不改 `scene_truth_proj`、不动 store revision。

1. `_deduction_context_segments(st, seq, *, focalizer="")`：焦点五层 ≤1800；非焦点一行边界禁「没察觉的」；整包 4500。
2. v1 仍 `_domain_input` 分源，`_push("deduction_final", "redline", joined)` 恰好一次。
3. 已有 `focalizer` 从 `_assemble_write_instructions_v1` 传入。

**验收（轻量，勿本机 Surreal / 全量）：** `scribe3/tests/test_deduction_final_cap.py` 11 绿。

---

## 7. 证据锚点（path:line）

- 注入（单次 push）：`scribe3/api/services/write_assemble_v1.py:533-541`
- 渲染 / 帽 / 焦点：`scribe3/api/services/write_assemble_context.py:331-520`
- 产投影：`scribe3/deduce_helpers.py:356-379`；Pilot 跳过已有：`scribe3/api/services/pilot_actions/deduce.py:91-94`
- NEVER + 层标 + 序：`scribe3/context_budget.py:171`、`:449`、`:823`
- L0 挤 L2：`scribe3/context_budget.py:605-616`、`:228`
- 同名少计：`scribe3/context_budget.py:547-549`
- 注册 / 软激活：`scribe3/injection_registry.py:73`；`scribe3/soft_activation.py:39`
- 软门未接线：`scribe3/deduce_helpers.py:243-270`（生产 grep 仅测试引用）
