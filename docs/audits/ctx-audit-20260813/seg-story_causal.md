# 单元：story_causal

- 层：L2 | zone：head | 裁剪档：DEF
- 代码锚点：scribe3/story_constraint_prompt.py:130
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

`_causal_chain_for_write` 回溯本章/上章事件；失败记 `empty_story_causal`（与无链空串区分）。assemble `_push("story_causal","supplemental")`。

## 2. 生成质量

第一性：本章前因。未接线。

## 3. 爆炸半径

图查询失败假「无链」会误导。

## 4. 业务完善性

对应因果/CL-B3。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

仅引擎。探针：`test_causal_fail_records_soft_fail`。

## 6. 最优改造

**主方案：** 接线 + 查询失败 `_record_write_soft_fail("empty_story_causal")`。

**放弃：** depth 盲目加大。

**验收：** 针对本段名的 assemble 段列表或纯函数断言。

## 7. 证据

- `scribe3/story_constraint_prompt.py:130`
- `scribe3/tests/test_r8_story_constraint_assemble.py:26`