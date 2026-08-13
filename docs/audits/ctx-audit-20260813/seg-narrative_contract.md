# 段卷宗 · narrative_contract

> W1 红线。库存：`docs/audits/ctx-audit-20260813/INVENTORY.md`。  
> 口径：`NOVEL_PROMPT_HARD=48_000`（`scribe3/context_budget.py:129`）；默认 `SCRIBE3_ENVELOPE_NOVEL=1` + V2。  
> 本段：L0 / zone=head / epistemic=redline / 裁剪档 **NEVER**。  
> 只跟踪本段：生产 → 注入 → 裁剪 → 观测。邻段只记接口与物理序。

## 0. 身份与邻段（序）

| 项 | 现网 |
|----|------|
| 注册 | `SegmentMeta("narrative_contract", "L0", "head", "redline")` · `injection_registry.py:46` |
| 层 | `GENERATION_SEGMENT_LAYERS["narrative_contract"] = "redline"` · `context_budget.py:426` |
| 永不裁 | `L0_NEVER_CUT` 含本名 · `context_budget.py:168` |
| 密度分子 | `DRAMA_CORE_NAMES` 含本名 · `injection_registry.py:85` |
| 物理序 | `prefix` → **本段** → `story_ember` / `story_recall` / `story_causal` → `event_drive` / `event_drive_hook` → `drama_contract` / `drama_vacuum` → `outline` → `envelope` … · `context_budget.py:787-798` |
| 序断言 | `physical_order_markers` 含本名；**可缺**；有则必须 `< drive/hook` · `context_budget.py:622-650` |

**邻段接口（不审邻段正文）**

- **前**：`prefix`（身份/协议/anti_slop；`structure_diversity` 并入 prefix 字节，不单独 `_push` 本段）。
- **后（声明）**：`story_*` 燃料在注册表与序里紧随本段，但是 **`write_assemble_v1` 现网不 `_push` `story_ember/recall/causal`**（`format_story_fuel_parts` 仅测试/计划态）。
- **后（实装）**：有场面字段 → `event_drive_hook`（supplemental）；无 → `event_drive`（redline，「优先执行」）。再后 `drama_contract` / 空戏时 `drama_vacuum`。

---

## 1. 流程完善性

### 1.1 设计上的闭环（assemble 内部）

```
chapter.narrative_contract
  → load_chapter_story_inputs（零写）
  → format_story_contract_head（四义原文 + 痕迹≤3 + 禁念条款）
  → 非空才 _push(name=narrative_contract, layer=redline)
  → join_generation_segments（registry 物理序 + L2 + O1 全域硬顶）
  → budget_report.domain_lengths / order_indices
  → density_trace_for_segments.drama_core_share
```

注入点唯一：`write_assemble_v1._render_final_input`（`write_assemble_v1.py:232-253`）。  
空四义 → `format_story_contract_head` 返回 `""` → `_push` 因 `if not text` 不入列（空合同写正文合法）。  
写路径禁止 `format_contract_block`（`test_r8_story_constraint_assemble.py:219-223` 锁源码字符串）。

裁剪：`layer=redline` 且名在 `L0_NEVER_CUT` → `apply_l2_trim` / `enforce_total_prompt_budget` 永不选为 victim。禁止 `rendered[:hard]` 尾截。本段无独立 token 额度；体量靠 sanitize `clip500`（若写库真发生）。

### 1.2 生产链在 store 断开（阻塞现网）

落库列已有：`migrations/134_narrative_contract.surql`（`option<string>` JSON，注释写「读端 json.loads」）。  
REST `ChapterMetaReq.narrative_contract`、`chapters.py` sanitize、MCP `s3_patch_chapter_plan(..., narrative_contract=)` 都会把字段塞进 `update_chapter_meta`。

**`scribe3/store/chapters.py` 全文零命中 `narrative_contract`：**

1. **写丢**：`update_chapter_meta` 白名单只有 `narrative_drive` 等，不含本列（`:994-1000`）。非白名单 `continue` 静默丢弃。MCP/REST 审批成功 ≠ 列被 SET。
2. **读盲**：`get_chapter` SELECT 列表到 `pressure_drive,beats_meta,narrative_drive` 止（`:344`），不取本列；也无 json.loads 镜像。调用方永远看不到落库合同。
3. **读谓词过窄**：`load_chapter_story_inputs` 仅当 `isinstance(..., dict)` 才接收（`write_assemble_context.py:600`）。即便日后 SELECT 出 JSON **串**，仍被当成 `{}`。对比：`validate_narrative_contract` 已能 `json.loads` 字符串（`narrative_contract.py:129-131`）。

后果：现网写路径 **本段几乎永不 `_push`**；`contract_has_scene_fields` 在 assemble / `_event_drive_block` / 人灯漂移 / 场面纸 全部读空 → 事件驱动不会降为 hook，「一张嘴」设计落空。

### 1.3 其它流程缺口

- 装载/格式化 `except Exception: _nc_txt = ""`（`write_assemble_v1.py:241-243`）**不打 soft_fail**，比邻段更盲。
- `load_chapter_story_inputs` 收集了 `prior_consequences`，本段 formatter 不用；燃料段未接线（邻段债，导致本段后注意力空一截）。
- 单测覆盖 join 序 / 纯函数 / 宣称，**没有** store 白名单 + SELECT + 读回 dict 的契约测，故本洞绿测通过。

**流程结论**：assemble/join/trim 设计完整；**生产→注入的数据面未接线**。对现网是断链，不是微调。

---

## 2. 生成质量

`format_story_contract_head`（`story_constraint_prompt.py:75-104`）工艺 intentional 且对路：

- 标题「写戏，不要念条款」；四义作者原文（`field_line` 只剥 `validation.ok` / schema id，不改写）。
- 禁角色复述四行、禁「勾半笔/减半笔/暂不深探」、禁对白中句「——」、限知一句。
- 痕迹最多 3 条；声口一行可选。燃料不进本段（头/燃料分离，测锁）。

质量风险（在「真能进模型」的前提下）：

| 风险 | 说明 |
|------|------|
| 注入谓词过宽 | 任一欲望/阻力/回合/代价非空即出头；**不要求** `validation.ok`（四格≥8 字、非占位）。半成品/口号合同仍进 L0 红线。 |
| 半合同降级驱动 | `contract_has_scene_fields` 与出头同一谓词。只填一格也会把 `event_drive` 打成 hook，丢掉「优先执行」全量驱动，注意力空心。 |
| 本段无字数封顶 | `field_line(..., max_chars=0)` 默认不截。sanitize 写端 clip 500；store 未接线时无意义。若绕过 sanitize 直写库，L0 NEVER 会吃窗。 |
| 与 drive 双嘴 | 无合同时（现网常态）模型只看见 `event_drive`「必须/优先执行」——本段缺席时的质量退回旧戏核。 |

宣称侧：`story_complete._load_contract` 不再用 `migrate_contract_from_drive` 冒充 `contract.ok`（`test_story_complete_no_migrate.py`）。无人值守要 `validation.ok` + ≥1 痕迹。这些与 **注入谓词** 不一致：宣称严、注入松。

---

## 3. 爆炸半径

**本段自身体积**：sanitize 生效时约「套话 200 字 + 4×≤500 + 痕迹 3 条」，远小于 48k。不是 token 炸弹。

**真正爆炸在「缺席」与「半出席」：**

- 缺席（现网）：`DRAMA_CORE` 分子少一块；`event_drive` 仍占 L0 NEVER，与大纲/pressure 形成多套「必须发生」。注意力被驱动条款占满。
- 半出席：弱合同挤占 head 红线，同时抽掉全量 `event_drive`，head 戏剧信号变薄。
- 永不裁：48k 硬顶下 L0+信封 22k 先吃预算，L2 `effective_l2_cap` 变窄。本段小，边际可忽略；**红线全家永不裁** 才是窗压来源。
- `soft_activation.REDLINE_SEGMENT_NAMES` **未列本段**（`soft_activation.py:29-44`）。现网因 `is_soft_segment` 为假而仍保留，不丢，但不进 `kept_redline` 观测。改 soft 启发式时有误伤面。
- `signal_density_proxy` 的 drama_keys **不含** 本段（`context_budget.py:883-886`），与 `DRAMA_CORE_NAMES` 两套分子。

下游读 `get_chapter()["narrative_contract"]` 的全部产品面（场面纸、人灯 `contract_fp`、soft drift、unattended、claim）与写路径同盲。

---

## 4. 业务完善性

产品意图（`docs/plans/2026-08-13-scene-contract-unify.md`）：`chapter.narrative_contract` 是「本章必须发生」SSOT；空合同作者可写；有合同则 L0 只留场面头。

现网业务态：

| 入口 | 状态 |
|------|------|
| 作者 REST PATCH | 模型有字段、sanitize 有；**store 丢** |
| 主编 MCP plan | 审批后同一 `update_chapter_meta`；**store 丢** |
| 页眉场面纸 | `scenePaper.js` 读 `c.narrative_contract`；get_chapter 无列 → 常空 |
| 写路径 L0 | 读空 → 不 push |
| 宣称 / 人灯 | 读空 → `narrative_contract_required`；story-ack 的 `contract_fp` 恒空指纹 |
| 无人值守 | 读空 → park「需要场面合同」 |

作者/主编「定了场面」会得到 HTTP/MCP 成功与 warnings，**库与模型都看不见**。这是产品主路径空转，不是文档滞后。

空合同合法写正文仍成立（因不 push）。无人值守与宣称仍堵空合同——但作者无法经正规通道把合同写进去，堵的是死门。

---

## 5. 评分

| 维 | 分 | 一句话 |
|----|----|--------|
| **P_flow** | **2** | join/trim/红线齐；store 读写未接线，生产→注入断。 |
| **Q_craft** | **4** | 场面头工艺清楚（原文、禁念、限知）；注入不校验 `validation.ok`。 |
| **R_safety** | **4** | L0 永不裁、空合同不编戏、禁 `format_contract_block`；异常吞没、soft 红线表漏名。 |
| **B_product** | **2** | SSOT 列存在但 PATCH/MCP 写不进、读不出；场面纸/人灯/写头同盲。 |
| **Observability** | **3** | 若注入则有 domain_lengths / order_indices / drama_core_share；无 `contract_injected` 硬字段；proxy 分子不含本段；现网恒 0 无法区分「作者未定」与「store 丢列」。 |

| P_flow | 2 |
| Q_craft | 4 |
| R_safety | 4 |
| B_product | 2 |
| Observability | 3 |

---

## 6. 最优改造

### 主方案（只做一个）

**把 `narrative_contract` 按 `narrative_drive` 同构打通 store，并让读路径吃 JSON 串。**

1. `get_chapter`：SELECT 增加 `narrative_contract`；`None/""/str/dict` 解析镜像 `narrative_drive`（`:382-395`）。
2. `update_chapter_meta`：`allowed` 加入 `"narrative_contract"`；与 `pressure_drive/beats_meta/narrative_drive` 同一 JSON 串分支（`:1028-1035`）。
3. 读兜底：`load_chapter_story_inputs`（及 chapters/MCP 的 `isinstance dict` 门）对 `str` 走 `validate_narrative_contract` / `json.loads`，禁止静默 `{}`。
4. 契约测（无 Surreal）：白名单含本名；parse helper 串→dict；`load_chapter_story_inputs` + `format_story_contract_head` 在 mock `get_chapter` 返回串或 dict 时都能出「【本章必须发生的场面】」。

不做：自动 `ensure` 四义、第二套 `format_contract_block`、改 48k/ NEVER 档、本轮去接线 `story_*`（邻段债）。

### 放弃的替代

- **用 `event_drive` / migrate 当场面头 fallback**：再造第二张嘴，违反 NG4 / unify 主权。
- **先加 `contract_injected` 观测再接线**：观测会稳定报 0，不治病。
- **把本段降为 L2 可裁**：场面 SSOT 不能让给 T3。
- **只改 `load_*` 不改 store**：SELECT 不到列，读侧永远空。

接线后若仍要补刀：注入与 `contract_has_scene_fields` 对齐 `validation.ok`（或至少四格齐），避免半合同废掉 `event_drive`。那是第二刀，不是本轮主方案。

---

## 7. 证据

| 命题 | path:line |
|------|-----------|
| 库存 L0 head redline NEVER；DRAMA_CORE | `docs/audits/ctx-audit-20260813/INVENTORY.md:54`；`injection_registry.py:46`；`injection_registry.py:85` |
| 48k 硬顶；L0 永不裁 | `scribe3/context_budget.py:129`；`:164-174` |
| 物理序本段在 prefix 后、ember/drive 前 | `scribe3/context_budget.py:787-793` |
| 有合同须先于 drive/hook；可缺 | `scribe3/context_budget.py:633-650` |
| 唯一 `_push` 本段 | `scribe3/api/services/write_assemble_v1.py:232-253` |
| 装载失败静默空头 | `scribe3/api/services/write_assemble_v1.py:241-243` |
| join 后写 budget_report | `scribe3/api/services/write_assemble_v1.py:653-679` |
| density 挂 domain_lengths | `scribe3/api/services/write_assemble_v1.py:798-804` |
| 读章只要 dict | `scribe3/api/services/write_assemble_context.py:600-601` |
| 场面头格式 / 空四义空串 | `scribe3/story_constraint_prompt.py:75-85` |
| 写端 clip500（未进 store 则无效） | `scribe3/narrative_contract.py:769-783` |
| 列定义存在 | `scribe3/migrations/134_narrative_contract.surql:4` |
| get_chapter **不 SELECT** 本列 | `scribe3/store/chapters.py:341-344` |
| update 白名单 **无** 本列 | `scribe3/store/chapters.py:994-1000` |
| REST sanitize 后仍走上述 update | `scribe3/api/routers/chapters.py:459-473` |
| MCP 审批后同一 update | `scribe3/mcp/tools_write.py:1092-1148` |
| 有字段则驱动改 hook | `scribe3/api/services/write_assemble_v1.py:257-264`；`write_assemble_context.py:276-279` |
| proxy 分子不含本段 | `scribe3/context_budget.py:883-886` |
| soft 红线表漏名 | `scribe3/soft_activation.py:29-44` |
| 序/空头/禁 format_contract_block | `scribe3/tests/test_r8_story_constraint_assemble.py:24-49`；`:177-179`；`:219-223` |
