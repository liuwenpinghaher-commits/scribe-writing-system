# 单元：story_causal

- 层：L2 | zone：head | 裁剪档：DEF
- 代码锚点：scribe3/story_constraint_prompt.py:130
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

格式化【前因后果】存在；物理序断言 ember < event_drive；assemble 未 push。因果查询失败应 soft_fail 而非装无链。

## 2. 生成质量

第一性：本章前因。未接线。

## 3. 爆炸半径

图查询失败假「无链」会误导。

## 4. 业务完善性

对应因果/CL-B3。

## 5. 评分

| P_flow | 1 |
| Q_craft | 2 |
| R_safety | 3 |
| B_product | 2 |
| Observability | 2 |

## 6. 最优改造

**主方案：** 接线 + 查询失败 `_record_write_soft_fail("empty_story_causal")`。

**放弃：** depth 盲目加大。

**验收：** 针对本段名的 assemble 段列表或纯函数断言。

## 7. 证据

- `scribe3/story_constraint_prompt.py:130`
- `scribe3/tests/test_r8_story_constraint_assemble.py:26`