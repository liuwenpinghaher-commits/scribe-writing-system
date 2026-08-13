# ctx-audit 现网库存 · 2026-08-13

> **W0**。行名一律从现网源码抽出，禁止用对话记忆中的 96k/32k 表。  
> 源：`scribe3/injection_registry.py` `SEGMENT_REGISTRY`；`scribe3/context_budget.py` `BLOCK_BUDGETS_NOVEL` / `L0_NEVER_CUT` / `L2_DROP_TIER` / `GEN_SEGMENT_PROTECTED` / `NOVEL_PROMPT_HARD`。  
> 代码 HEAD（开跑时）：`402a46d`。

## 现网窗口数字（live）

| 常量 | 值 | 源 |
|------|----|----|
| `NOVEL_PROMPT_HARD` | **48_000** | `context_budget.py:129` |
| `NOVEL_ENVELOPE_TOKEN_BUDGET` | **22_000** | `:52` |
| `DEFAULT_PROMPT_HARD`（关 novel） | 42_000 | `:128` |
| `DEFAULT_SUPPLEMENTAL_SOFT` | 14_000 | `:125` |
| `DEFAULT_SUPPLEMENTAL_HARD` | 18_000 | `:126` |
| `DEFAULT_CODEX_INJECT_CAP` | 4_500 | `:124` |
| 对话里曾说的 96k / 信封 32k | **不是现网默认** | 以本表为准 |

默认档：`SCRIBE3_ENVELOPE_NOVEL=1` + V2 → `get_prompt_hard()` = 48k，信封 22k。

裁剪档规则：

- `NEVER` = 名在 `L0_NEVER_CUT`（L2 victim 永不整段丢）
- `PROT` = `GEN_SEGMENT_PROTECTED`（outline / brief_must / voice_anchor）
- `T3` / `T2` / `T1` = `L2_DROP_TIER`（数字越大越先丢）
- `DEF` = 不在上表；`apply_l2_trim` 默认 priority **55**（介于 T2 与 T1 之间）
- `ENV` = 信封八块（在 `envelope` 段内，不单独进 L2_DROP）

---

## A. 信封八块（`BLOCK_BUDGETS_NOVEL`）

| 单元 | 层 | 裁剪档 | 现网额度 | 源 |
|------|----|--------|----------|----|
| focus | L1-env | ENV | 1000 | `context_budget.py:43` |
| global | L1-env | ENV | 1800 | `:44` |
| canonical | L1-env | ENV | 9200 | `:45` |
| recent | L1-env | ENV | 6000 | `:46` |
| procedural | L1-env | ENV | 1400 | `:47` |
| reference | L1-env | ENV | 1800 | `:48` |
| uncertainty | L1-env | ENV | 800 | `:49` |
| provenance | L1-env | ENV | **0**（默认不进模型） | `:50` |

合计 22_000。`envelope` 整段同时是注入段（见 B）且在 `L0_NEVER_CUT`。

---

## B. 注入段（`SEGMENT_REGISTRY` · 34 行）

| 单元 | 层 | zone | epistemic | 裁剪档 |
|------|----|------|-----------|--------|
| prefix | L0 | head | redline | NEVER |
| structure_diversity | L0 | head | redline | NEVER |
| narrative_contract | L0 | head | redline | NEVER |
| story_ember | L2 | head | world | DEF |
| story_recall | L2 | head | world | DEF |
| story_causal | L2 | head | world | DEF |
| event_drive | L0 | head | redline | NEVER |
| event_drive_hook | L2 | head | world | DEF |
| drama_contract | L0 | head | redline | NEVER |
| drama_vacuum | L0 | head | redline | NEVER |
| outline | L1 | head | frame | PROT |
| envelope | L1 | mid | frame | NEVER |
| codex | L2 | mid | world | T1 |
| seed_words | L3 | mid | craft | T3 |
| craft | L3 | mid | craft | T2 |
| phase_role | L3 | mid | craft | T2 |
| avoid | L3 | mid | craft | T2 |
| revelation_discipline | L0 | mid | redline | NEVER |
| sincerity | L0 | mid | redline | NEVER |
| purpose | L2 | mid | frame | T1 |
| volume_intro | L3 | mid | world | T2 |
| brief_must | L2 | mid | frame | PROT |
| pressure_drive | L2 | mid | frame | T1 |
| author_prefs | L3 | mid | craft | T3 |
| voice_anchor | L2 | mid | frame | PROT |
| reference_craft | L3 | mid | craft | T3 |
| storyline_polish | L3 | mid | craft | T3 |
| discourse_soft | L3 | mid | craft | T3 |
| story_move | L3 | mid | craft | T3 |
| deduction_final | L0 | mid | redline | NEVER |
| material_recall | L3 | mid | craft | T3 |
| final_reminder | L0 | tail | redline | NEVER |
| scene_truth_proj | L0 | mid | redline | NEVER |
| request_constraint | L3 | tail | craft | T2 |

`DRAMA_CORE_NAMES`（密度分子）：narrative_contract, event_drive, drama_contract, drama_vacuum, outline, brief_must。

---

## C. L0 旁路段（`L0_NEVER_CUT` 中 **不在** `SEGMENT_REGISTRY` 的名字）

| 单元 | 层 | 裁剪档 | 备注 |
|------|----|--------|------|
| identity | L0 | NEVER | 组装身份前缀，非 registry |
| write_protocol | L0 | NEVER | 写协议 |
| revision | L0 | NEVER | 修订约束 |
| anti_slop | L0 | NEVER | 防套话 |
| continue_snapshot | L0 | NEVER | 续写快照 |
| secret_guard | L0 | NEVER | 保密护栏 |
| request_position | L0 | NEVER | 请求落位 |
| tool_scope | L0 | NEVER | 工具范围 |
| craft_skills_index | L0 | NEVER | 技法索引 |
| focalizer | L0 | NEVER | 限知焦点声明 |

（`L0_NEVER_CUT` 里与 B 重叠的名字不重复计为旁路：prefix, structure_diversity, narrative_contract, event_drive, drama_*, envelope, revelation_discipline, sincerity, final_reminder, deduction_final, scene_truth_proj。）

---

## 本轮 W1 覆盖（红线）

计划点名且现网存在：

1. narrative_contract  
2. event_drive  
3. drama_contract  
4. drama_vacuum  
5. outline  
6. deduction_final  
7. scene_truth_proj  
8. secret_guard  
9. focalizer  
10. final_reminder  

无「点名但不在库存」的名字。W2–W5 仅列于上表，本轮不写卷宗。

## 计数

| 来源 | 行数 |
|------|------|
| 信封块 A | 8 |
| 注入段 B | 34 |
| L0 旁路 C | 10 |
| **库存合计（不重名）** | **52** |
| W1 本轮卷宗 | 10 |
