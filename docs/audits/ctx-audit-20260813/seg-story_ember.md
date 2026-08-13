# 单元：story_ember

- 层：L2 | zone：head | 裁剪档：DEF
- 代码锚点：scribe3/story_constraint_prompt.py:114
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

registry + 物理序在 narrative_contract 后、event_drive 前；`format_story_fuel_parts` 可生成【上章余烬】。`load_chapter_story_inputs` 取上章 `end_hook` → `collect_story_fuel_segments` → assemble `_push("story_ember","supplemental")`。空则 `empty_story_ember`。不进 `L0_NEVER_CUT`。

## 2. 生成质量

第一性：上章日子余热。病：作者写了余烬字段也不进 48k。探针：现网 draft assemble 段名不应出现 story_ember（直至接线）。

## 3. 爆炸半径

接线后与 recent 重叠；误焊 L0 抢窗。回归：test_r8 序断言 vs 实 push。

## 4. 业务完善性

对应 CL-B5 续写；设计预算-optimal 的 T1_fuel 现网 L2_DROP 已无 T1_fuel 档。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

仅引擎燃料，作者主表面不展示段名。探针：`test_story_fuel_wire.py`。

## 6. 最优改造

**主方案：** 从 load_chapter_story_inputs 取 prior_consequences，`format_story_fuel_parts` 后 `_push("story_ember","supplemental")`。禁止加入 L0_NEVER_CUT。

**放弃：** 把余烬拼回 narrative_contract（已否决）。

**验收：** 针对本段名的 assemble 段列表或纯函数断言。

## 7. 证据

- `scribe3/story_constraint_prompt.py:114`
- `scribe3/context_budget.py:789`
- `scribe3/api/services/write_assemble_v1.py:229`