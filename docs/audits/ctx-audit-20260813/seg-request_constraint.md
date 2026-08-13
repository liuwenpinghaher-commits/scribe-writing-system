# 单元：request_constraint

- 层：L3 | zone：tail | 裁剪档：T2
- 代码锚点：scribe3/api/services/write_assemble_v1.py:547-552
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

extra_instructions 才 push。作者本轮约束。

## 2. 生成质量

第一性：这一次你说的话。

## 3. 爆炸半径

小。

## 4. 业务完善性

写槽请求。

## 5. 评分

| P_flow | 4 |
| Q_craft | 4 |
| R_safety | 4 |
| B_product | 4 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 空 extra 不 push（已然）。

**放弃：** 把整段聊天塞进来。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:547-552`