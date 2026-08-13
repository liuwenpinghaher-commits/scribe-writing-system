# 单元：story_recall

- 层：L2 | zone：head | 裁剪档：DEF
- 代码锚点：scribe3/story_constraint_prompt.py:127
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

format 可出【世界此刻】且有 4000 字燃料帽（测试）。assemble **未 push**，与 ember 同病。

## 2. 生成质量

第一性：限知后的世界此刻。未接线则质量为 0。探针：接线后须经限知投影。

## 3. 爆炸半径

接线后与 canonical/recent 抢窗；默认 priority 55。

## 4. 业务完善性

对应 CL-B6。

## 5. 评分

| P_flow | 1 |
| Q_craft | 2 |
| R_safety | 3 |
| B_product | 2 |
| Observability | 2 |

## 6. 最优改造

**主方案：** 与 ember/causal 同一 PR 接线；query 限知投影后注入；超窗按 DEF 可裁。

**放弃：** k 提到 12 当质量（预算文档已收回）。

**验收：** 针对本段名的 assemble 段列表或纯函数断言。

## 7. 证据

- `scribe3/story_constraint_prompt.py:127`
- `scribe3/story_constraint_prompt.py:171`