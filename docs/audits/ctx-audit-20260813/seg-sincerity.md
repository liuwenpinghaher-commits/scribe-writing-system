# 单元：sincerity

- 层：L0 | zone：mid | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_v1.py:379-380
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

_focalizer_sincerity_block 固定红线。偏口号。

## 2. 生成质量

第一性：诚意/反油滑。质量弱。

## 3. 爆炸半径

焊死每章。

## 4. 业务完善性

弱产品面。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

已并入 anti_slop 短核，不再独立 `_push`。空/跳过可查：assemble 源无 sincerity 段。

## 6. 最优改造

**主方案：** 并入 anti_slop 或删独立段，只留一条。

**放弃：** 加长真诚散文。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:379-380`