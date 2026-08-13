# 写路径上下文单元审计 · `drama_contract`

> 日期：2026-08-13 · 只读 · 未改代码、未跑全量测、未起本机 Surreal。  
> 库存：[`INVENTORY.md`](./INVENTORY.md) B 表 L0 / head / redline / **NEVER**。  
> 代码锚：`scribe3/injection_registry.py`、`scribe3/context_budget.py`、`scribe3/api/services/write_assemble_v1.py`、`scribe3/api/services/write_assemble_context.py`、`scribe3/drama_beats.py`、`scribe3/brief.py`。

## 身份（现网）

| 项 | 值 | 证据 |
|----|----|------|
| 注册 | `SegmentMeta("drama_contract", "L0", "head", "redline")` | `scribe3/injection_registry.py:52` |
| 密度分子 | 在 `DRAMA_CORE_NAMES` | `scribe3/injection_registry.py:84-85` |
| 层 / 裁剪 | `GENERATION_SEGMENT_LAYERS["drama_contract"]="redline"`；名在 `L0_NEVER_CUT` | `scribe3/context_budget.py:432`、`:169` |
| 自有字数帽 | `MAX_DRAMA_BLOCK = 400`（段内 clip，非整段 L2 丢） | `scribe3/drama_beats.py:647` |
| 物理序 | `event_drive` / `event_drive_hook` 之后、`drama_vacuum` 与 `outline`/`envelope` 之前 | `scribe3/context_budget.py:786-799`、`:624` |
| 产品定义 | 「唯一 GCD 执行摘要」；outline 只应带 synopsis+beat.text | `scribe3/GLOSSARY.md:62-63` |
| 软激活 | 红线，永不因激活键省略 | `scribe3/soft_activation.py:32` |

设计口径（`docs/plans/2026-08-13-scene-contract-unify.md:739`）：有场面合同时 **不改名、不降 L0**——它是**节拍走法**，不是第二句「必须发生」。

---

## 1. 流程完善性

端到端（数据 → 渲染 → 注入 → 去重 → 观测）**主链闭合**，旁路有两处漂移。

```text
作者/主编填拍  或  expand_beats（beats.v2）
        ↓  chapter.beats[].goal/conflict/turn/cost/hook
        ↓  钩：resolve_chapter_hook（写路径）
format_drama_block  →  _drama_block
        ↓
write_assemble_v1._push("drama_contract", "redline", …)
        ↓
join_generation_segments（NEVER 裁整段）
        ↘ 无 GCD → empty_drama + 可选 drama_vacuum
```

- **生产**：`scribe3/api/services/write_assemble_v1.py:271-294` 调 `_drama_block`；空串记 `empty_drama`，再 `_push` `drama_vacuum`；有正文才 `_domain_input` + `_push("drama_contract")`（`_push` 空串直接跳过）。
- **渲染**：`scribe3/api/services/write_assemble_context.py:290-324` 读章 beats，钩走 `chapter_hooks.resolve_chapter_hook`，`format_drama_block` fail-soft。
- **简报同源再剔除**：`brief.assemble_chapter_brief` 仍组 `sections["drama_contract"]`（`scribe3/brief.py:833-857`），`render_brief` 置顶（`:636-638`）；写路径 `_brief_must_sections_write_block` **pop** 掉，防双份（`write_assemble_context.py:507-508`）。讨论/面板仍能看见同一段文案。
- **上游门**：`pilot_actions/beats.expand_beats` 写 v2 GCD + `validate_drama_beats`；`SCRIBE3_DRAMA_GATE` 默认关，compat_v1 默认弱通过——**缺格仍可写**，靠真空警告补洞。
- **UI**：`scribe3/web/src/ChapterStudio.jsx:310-316` GCD 五格（目标/冲突/转折/代价/钩），PATCH 走闸外 gcd-fields。

缺口：

1. **钩 SSOT 分叉**：写路径用 `resolve_chapter_hook`（`write_assemble_context.py:308-319`，含 synopsis.meta / 上章 end_hook）；简报只用 `beats_meta.chapter_hook` → 末拍 `hook`（`brief.py:838-846`）。面板简报与真主路径可能差一行钩。
2. **pressure 差集几乎永不触发**：`write_assemble_v1.py:454-456` 把 `ch["drama_contract"]`/`ch["drama"]` 当 dict；现网戏剧合同是 **渲染串**，结构化 GCD 在 `beats[]`。`injection_compact.pressure_diff_keys`（`:170-192`）见非 dict → `None` → pressure **整块保留**，与 GCD 再叠一层「阻力/代价」。
3. **序断言不进生产 join**：`assert_physical_order_indices`（`context_budget.py:631-658`）要求组装结果**必须有** `drama_contract` 下标；`join_generation_segments`（`:491-559`）**不算**此断言。空 GCD 时生产合法缺段，单测夹具必须塞假「戏」才能过序检。
4. **写后不兑 GCD**：validate 只在 expand/park；起草后无「场上是否发生过改日子的事」对照。词表门（`TURN_COST_LEX`，`drama_beats.py:25-29`）替代场面验收。

---

## 2. 生成质量

本段自称「必须执行」的**本章戏**，实际进模型的多半是**套话 + 28 字标签残片**。

`format_drama_block`（`scribe3/drama_beats.py:703-819`）：

- 无任一 GCD/钩 → 空串（好；不造假合同）。`beats_have_drama_gcd`（`:682-696`）过宽：**仅章末钩**也算有戏。
- 有戏则标题「本章戏剧合同（必须执行，禁止风景巡礼）」+ 拍行「目标/阻力/**结果**/代价」字段帽 **28**（二次收 **16**）+ 固定 MRU 三行 + 禁令 + 可选限知。
- **超 400 先砍拍明细，再砍拍数，最后才减 MRU**（`:763-801`）。标题与限知优先于故事事实。

后果：

| 现象 | 为何伤正文 |
|------|------------|
| 固定 MRU / 「禁只逛地点」占约 140–180 字 | 与 `craft` / `anti_slop` / `structure_diversity` 同义重复；挤掉本章特有阻力/代价 |
| `turn` 渲染成「**结果**」，UI 写「**转折**」 | 模型与作者看到两套词；「结果」更像结局摘要，不像当场变故 |
| 西式四格标签原文进 L0 | 与场面合同 `desire/obstacle/turn/cost`、`event_drive` 引爆/对立同源好莱坞语法；已有审计指条款进嘴（`docs/evidence/system-audit-20260813/audit-novel.md` F-N03） |
| outline 仍拼「〔节拍〕1.text 2.text…」（`write_assemble_context.py:184-186`） | GCD 摘要与拍正文双份；设计「唯一戏剧钉」未兑现 |
| 仅钩也出「必须执行」 | 过渡/低压章被按高压走法施压 |
| 空 GCD + 默认开的真空警告 | 低压/关系回收（outline plan 明文允许无显性爽点）仍吃 L0「禁公园巡礼」 |

限知免责句与 `_outline_block` 同口径，裁剪时尽量保留——这点对，但进一步压缩了 GCD 配额。

---

## 3. 爆炸半径

改本单元会碰到的面（由近到远）：

| 圈 | 触点 | 说明 |
|----|------|------|
| 渲染核 | `drama_beats.format_drama_block` / `beats_have_drama_gcd` / `MAX_DRAMA_BLOCK` | 纯函数；单测 `tests/test_drama_block_pr4.py` |
| 写组装 | `_drama_block`、`write_assemble_v1` `_push`、`empty_drama` / `drama_vacuum` 互斥 | 物理序标记之一（`context_budget.py:619-628`） |
| 简报 | `assemble_chapter_brief` + `render_brief` 置顶；写路径 pop | 改文案则面板与讨论同步变 |
| 预算/注册 | `L0_NEVER_CUT`、`DRAMA_CORE_NAMES`、`signal_density_proxy`（`:878-886` 另用一套 drama 键） | 永不进 L2 victim；帽只能段内 400 |
| 差集 | `injection_compact.pressure_diff_keys` | 现网几乎空转；修 dict 源才会动 pressure |
| 上游门 | `validate_drama_beats`、`pilot_runtime` park、`ChapterStudio` GCD 卡 | 改字段名/标签要同步 UI `GCD_FIELDS` |
| 密度观测 | `drama_core_share` | 缩 MRU 会让 share 下降，勿当质量回退 |

**可控性**：渲染集中在一个纯函数，半径比「再加第五套戏核表」小。风险在 L0 NEVER——文案变差会**整段焊死进每章草稿**，无法靠超窗裁掉。

与相邻 L0 的职责边界（设计已写、实现未切干净）：

- `narrative_contract`：场面必须发生（四义）。
- `event_drive`：章级冲突时钟；有合同则降为 hook。
- `drama_contract`：拍级走法。
- `drama_vacuum`：无走法时的禁令。
- `outline`：synopsis + text，**不应**再当 GCD。

---

## 4. 业务完善性

作者可感知闭环：

- **有**：章工作室戏剧卡手填 → 存拍字段 → 起草头顶见合同；无 GCD 时真空警告；限知章附「帧外不得道破」。
- **弱**：`SCRIBE3_DRAMA_GATE` 默认关 + v1 弱通过 → 「戏剧卡」对高压章仍是软建议；作者可一直用纯 text 拍，每章只吃真空套话。
- **乱**：戏核产品入口叠了合同 / drive / PDC / GCD / purpose（F-N04）。本段在设计里是「拍级唯一摘要」，但对作者仍是第四张表。
- **角色冲突**：低压/修炼/信息整理允许无显性 GCD，写路径不读 `chapter_role`，一律按「禁止巡礼」红线。
- **铜炉体**：四格 + MRU（刺激→身体→决定）把岁时、笑闹、说书停评压成对峙动词；与《乱世铜炉》章法不合。

业务上本段**值得存在**（拍级走法 ≠ 场面合同），但「必须执行」的力度大于其信息精度。

---

## 五维评分（1–5，高更好）

| 维 | 分 | 一句话 |
|----|----|--------|
| 流程完善性 | **4** | 真主路径闭合、brief 去重、真空兜底；钩 SSOT 与 pressure 差集未接结构化源。 |
| 生成质量 | **2** | 400 字先保套话再保戏；标签/双份拍文/仅钩即合同，易出条款腔与假高压。 |
| 爆炸半径可控 | **3** | 改渲染函数即可，但 L0 NEVER 使坏文案全章焊死；邻段职责未切。 |
| 业务完善性 | **3** | 戏剧卡可填、定义清楚；默认门软、低压误伤、与三套戏核抢嘴。 |
| 预算与注意力纪律 | **4** | 登记 L0/head/NEVER、自帽 400、序在 envelope 前；段内优先级与「戏优先」相反。 |

**均分 3.2**。不是缺段，是**段在、钉歪**。

| P_flow | 4 |
| Q_craft | 2 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 4 |

---

## 恰好一个最优改造

**反转 `format_drama_block` 的 400 字裁剪序，并去掉固定 MRU/西式格标签：超预算先删 MRU 三行与禁令，再缩字段；每拍改为一句无标签场面走法（谁拦/谁拒/当场变了什么/留下什么痕）。仅当拍上 goal/conflict/turn/cost 皆空且无实质钩时才走 `drama_vacuum`；低压/过渡角色不推「必须执行」标题。**

- **做**：`scribe3/drama_beats.py:703-819` 一处纯函数 + `test_drama_block_pr4.py` 锁「有长拍时正文仍含冲突/代价、不含 MRU 标题」。写路径/注册/L0 档位不动。
- **不做**：不拆 `narrative_contract`、不改 registry 层、不把 GCD 并进 outline、不加第五套戏核。
- **验收**：有 3+ 拍满格时 joined 中 `drama_contract` 含本章特有名词，且 **不**出现「微观节奏」「目标：」「阻力：」「结果：」；无 GCD 的低压章 **不**出现「必须执行，禁止风景巡礼」。

---

## 关键 path:line

- `scribe3/injection_registry.py:52` — 登记 L0/head/redline  
- `scribe3/context_budget.py:169` — `L0_NEVER_CUT` 含 `drama_contract`  
- `scribe3/context_budget.py:794` — 物理序紧挨 `event_drive_hook` 之后  
- `scribe3/api/services/write_assemble_v1.py:271-294` — `_drama_block` → vacuum / `_push`  
- `scribe3/api/services/write_assemble_context.py:290-324` — 读拍 + `resolve_chapter_hook`  
- `scribe3/api/services/write_assemble_context.py:507-508` — brief 去重 pop  
- `scribe3/drama_beats.py:703-801` — 28 字帽与「先砍拍、后砍 MRU」  
- `scribe3/brief.py:838-846` — 简报钩未走 SSOT  
- `scribe3/web/src/ChapterStudio.jsx:312-316` — UI「转折」vs 注入「结果」
