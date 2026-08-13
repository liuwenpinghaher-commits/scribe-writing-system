# 写路径单元卷宗 · event_drive

> 库存：`INVENTORY.md` B 行 · L0 / head / redline / **NEVER**。  
> 范围：只审 **`event_drive`** 注入段（`format_event_drive_block` → `_push("event_drive")`）。  
> **不展开** `event_drive_hook`（仅作「有场面合同时本段不入座」的分叉条件）。  
> 代码对照：`scribe3/context_budget.py`、`injection_registry.py`、`write_assemble_v1.py`、`write_assemble_context.py`、`narrative_drive.py`。

---

## 1 流程完善性

**主链（旗开 + 章上已有实质 `narrative_drive` + 无场面合同）是通的。**

```
ensure_narrative_drive（outline / expand_beats / draft_loop）
  → 章字段 chapter.narrative_drive（嵌套 v1：inciting_force.summary / opposition / deadline_or_cost / scene_turn / end_hook）
  → write_assemble_v1._assemble_write_instructions_v1
  → _event_drive_block(st, chapter, focalizer)
       旗关 / 无章 / 空 dict / 无实质字段 → 空串
       有场面合同 → format_event_drive_hook_only（本卷宗不审其文案）
       否则 → format_event_drive_block(drive, focalizer) ≤220
  → 无合同：_push("event_drive", "redline", …)
  → join_generation_segments：物理序 narrative_contract < … < event_drive < [hook 槽] < drama_contract < envelope
  → L0_NEVER_CUT / soft_activation 红线免疫
```

**已接线、可算完善的部分**

- 注册表：`SEGMENT_REGISTRY` L0/head/redline；`GENERATION_SEGMENT_LAYERS["event_drive"]="redline"`；`DRAMA_CORE_NAMES` 含本段；`physical_order_markers` 含本段。
- 组装：`_event_drive_block` 在 `_drama_block` 之前；`app_impl` rebind 白名单含该 helper。
- 生产：`ensure` 挂在 propose_outline / expand_beats（含 skip）/ draft_loop；`SCRIBE3_NARRATIVE_ENGINE` 的 **REGISTRY 默认是 True**（`settings.py`），与旧测试「代码默认关」叙述已漂移。
- 空合同：`format_event_drive_block` 要求 `summary | wants | scene_turn` 任一非空，否则不注入假合同。
- 有合同：本段 **不** 以 `event_drive` 名入座（改 hook），避免与场面头抢「必须发生」。

**断点（本段流程未闭合）**

1. **写路径本身不 ensure。** `chat/write`、`chapters` generate 只调 `_assemble_write_instructions`。章上没有 `narrative_drive`（作者从未走过 pilot outline/beats/draft，或 ensure 写库失败只留内存对象）→ 本段整段缺席。
2. **合同谓词双读。** `_event_drive_block` 用 `st.get_chapter().narrative_contract` 选 full/hook；v1 再用 `load_chapter_story_inputs().contract` 决定 `_ed_name` / layer。任一侧 fail-soft 吞掉 → **钩文可能被标成 `event_drive` L0**，或全文 drive 被标成 hook。
3. **空段静默。** `empty_drama` 有 `_record_write_soft_fail`；本段旗关、读章失败、格式化失败、无实质字段 **全部变空串**，assemble **不**记 `empty_event_drive`。预算报告里「没有这个 key」与「旗关」不可分。
4. **`project_drive_from_contract` 是死形状。** 产出扁平 `inciting/opposition/turn/cost`，`format_event_drive_block` 只读嵌套 `inciting_force.summary`。写路径正确选择了「不投影假 drive」，但「合同有戏、drive 空」时本段仍空，无回退。
5. 旗关（env/DB 覆盖为 0）时 helper 直接 `return ""`，即使章上已有完好 drive。

流程判断：**半闭环**。pilot 主航道齐；非 pilot 写 + 空/弱 drive + 双谓词是真实缺口。

---

## 2 生成质量

`format_event_drive_block` 把嵌套 drive 压成固定骨架：

- 标题：`## 本章事件驱动（冲突/事件主时钟·优先执行）`（本身约 24 字，吃掉 220 预算）
- 核：引爆（kind+summary≤40）/ 对立（who≤12 + wants≤28 + leverage≤12）/ 代价 / 翻转≤36 / 钩子≤28
- 引导：full / short / micro 三档；`DEFAULT_DRAMA_STEER` 开则直接 micro「对白对立；逼近戏。」
- 超长：先丢相机 → 缩引导 → 保前三行 → 仍超则 **尾截加省略号**

**优点**

- 有戏核能落地成「引爆/对立/代价」三条，模型扫一眼知道本章外力是谁、要什么。
- 无实质字段不灌水（`empty_narrative_drive` 格式化为空）。
- 裁剪纪律明确：保冲突核、丢相机与套话。

**缺点**

- **标题+「优先执行」是刑典口吻**，与模块自己的「引导优先、允许跟主角」打架；有合同后才改口，无合同时仍命令模型「优先执行」。
- **220 硬顶 + 长标题** → 对立/代价/翻转经常被 clip 成残句；`prefer_micro` 后引导几乎无场面信息。
- **compose 的 `scene_turn` 是公式**：`因「{summary}」局势被迫转向，代价面：{if_fail}`，不是作者可演的翻转，注入后像说明书。
- 种子链（库存债禁 → purpose → events 威胁词 → 大纲 stakes → 上章钩 → synopsis 外力句）合理，但 `_THREAT_LEX` 漏检则整段空；`who` 常回落「对立面/外力」空壳。
- 与 `drama_contract`（GCD）无差集：无合同时两套「必须发生」并排，模型听两张嘴。

质量判断：**结构可用，文学密度低**；是冲突时钟摘要，不是可演场面。

---

## 3 爆炸半径

| 方向 | 影响 |
|------|------|
| 裁剪 | `L0_NEVER_CUT` + layer=redline → L2/O1 **永不整段丢**；只可能本段内部 220 自裁。 |
| 注意力 | 物理序靠头（合同/燃料之后、drama 之前），占 `signal_density_proxy` / `DRAMA_CORE_NAMES` 分子。块短（≤220+前导换行），抢窗有限。 |
| 命名分叉 | 误标为 hook → 变 supplemental、可被 L2 裁；误标为本段 → 钩文享受 NEVER。 |
| 调用面 | 改 format / helper 签名：`narrative_drive` 单测、`test_r8_story_constraint_assemble`、`test_novel_first_injection` 序断言、`write_assemble` rebind。 |
| 不该动 | 不要把本段改成可裁；不要在 assemble 里为「再验一次」投影扁平 drive。 |
| 写后半环 | `EVENT_DRIVE_GATE` 默认关；DETECT 是另一条 type=event_drive finding，**不是本注入段**。改本段文案不自动改 park。 |

爆炸半径：**中低**。改文案/观测面小；改层/改名/改 NEVER 会扯断序断言与密度分子。

---

## 4 业务完善性

产品角色（空合同章）：**本章冲突/事件主时钟**——告诉模型「戏由外力推，跟主角可以但须逼近当前对立」。

- 与场面合同：U4 已规定有合同则本段退场，避免三套「必须发生」。**本段只应对「没有场面合同」的章负责。**
- 与 `drama_contract`：GCD 是节拍级必须；本段是章级外力时钟。现网无差集，空合同章仍叠嘴。
- 与 `pressure_drive`：后者偏不可逆痕迹，物理序更靠后，可裁。
- 作者锁：`ensure` 尊重 `locked` / `source=author`；注入只读章字段，不覆盖作者 drive。
- 非 pilot 写（编辑器直接 generate / chat write）：**经常没有时钟**，业务承诺落空。
- GATE 关 = 引导不执法：模型可忽略「优先执行」且写后不 park。产品是软钉子，不是合同。

业务判断：**空合同 + 已 ensure 的章，职责清楚；覆盖面受入口限制。**

---

## 5 评分

| 维 | 分 | 一句话 |
|----|----|--------|
| P_flow | **3** | pilot 闭环；assemble 不 ensure、空段无计数、合同双谓词。 |
| Q_craft | **3** | 三核结构对；标题吞预算、套话引导、公式翻转。 |
| R_safety | **4** | NEVER + 红线免疫 + fail-soft 不阻断；双谓词误挂 L0 是主要风险。 |
| B_product | **3** | 空合同章需要这颗钉；非 pilot / 弱种子时钉不在。 |
| Observability | **3** | 有段则进 `domain_lengths` / `order_indices` / density；缺席与旗关不可分。 |

| P_flow | 3 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

---

## 6 恰好一个最优改造

**assemble 单点判定 + 空段可观测（禁止双谓词、禁止静默缺席）。**

1. `_event_drive_block(..., contract=None)`：场面合同用调用方传入的同一对象（v1 已 `load_chapter_story_inputs`）；**禁止** helper 内再 `get_chapter` 判合同。full/hook 与 `_ed_name`/`_ed_layer` 只认这一次 `contract_has_scene_fields`。
2. `narrative_engine_enabled()` 且 **无场面合同** 且格式化结果为空 → `_record_write_soft_fail("empty_event_drive")`（对称 `empty_drama`）。旗关不记（那是产品关断）。
3. **不要**在 assemble 里 `ensure`（编译路径写库，爆炸半径过大）；不要改 NEVER；不要动 hook 文案。

验收：同一 `st` 上合同加载失败时不得把钩文 `_push` 成 `event_drive`；引擎开、无合同、无实质 drive 时 soft_fail 计数 +1；空合同+完好 drive 仍出现「引爆」且序在 drama 前。

---

## 7 证据

- 库存位：`docs/audits/ctx-audit-20260813/INVENTORY.md:58`（L0 / NEVER）
- 注册：`scribe3/injection_registry.py:50` `SegmentMeta("event_drive", "L0", "head", "redline")`
- 层与序：`scribe3/context_budget.py:169`（`L0_NEVER_CUT`）、`:430`（`GENERATION_SEGMENT_LAYERS`）、`:623`（`physical_order_markers`）、`:636-658`（`drive_slot` 可回落 hook）
- 组装入座：`scribe3/api/services/write_assemble_v1.py:254-270`（二次 `contract_has_scene_fields` 命名）；`:273`（仅 `empty_drama`，无 empty_event_drive）
- 读章+格式化：`scribe3/api/services/write_assemble_context.py:252-287`（旗门、二次读 `narrative_contract`、fail-soft 空串）
- 生成：`scribe3/narrative_drive.py:26` `MAX_EVENT_DRIVE_BLOCK = 220`；`:521-625` `format_event_drive_block`（标题「优先执行」、candidate 裁剪、尾截）
- 扁平投影不可喂 format：`scribe3/narrative_contract.py:229-240` vs `narrative_drive.py:535-545`
- 写路径不 ensure：`scribe3/api/routers/write.py:58` 只 assemble；ensure 仅 `pilot_actions/draft.py:25-30`、`beats.py:122-126`、`outline.py:37-38`
- 现网旗默认开：`scribe3/settings.py:244` `Setting(..., True, ...)`（`test_narrative_drive.py:148-150` 仍断言 `CODE_DEFAULTS` 为 False，与 REGISTRY 漂移）
- 密度分子：`scribe3/injection_registry.py:84-86`；`context_budget.py:883-885`
- 红线免疫：`scribe3/soft_activation.py:29-31`
- 序单测：`scribe3/tests/test_r8_story_constraint_assemble.py:24-28`、`:147-149`（空合同才含「优先执行」）
