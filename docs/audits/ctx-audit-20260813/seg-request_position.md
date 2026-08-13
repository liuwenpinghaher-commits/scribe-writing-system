# 单元：request_position

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_v1.py:135-138
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

固定「当前第 N 章」。并入 prefix。

## 2. 生成质量

第一性：章号。信息量极低但必要。

## 3. 爆炸半径

无。

## 4. 业务完善性

定位。

## 5. 评分

| P_flow | 5 |
| Q_craft | 2 |
| R_safety | 5 |
| B_product | 3 |
| Observability | 2 |

## 6. 最优改造

**主方案：** 可留在 prefix 一行；不必独立段。本卷宗改造=维持一行。

**放弃：** 扩成章摘要。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:135-138`