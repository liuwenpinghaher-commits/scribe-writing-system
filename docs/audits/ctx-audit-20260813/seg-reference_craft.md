# 单元：reference_craft

- 层：L3 | zone：mid | 裁剪档：T3
- 代码锚点：scribe3/api/services/write_assemble_v1.py:489-496
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

仅 draft/final：craft_briefs_for_write 多段同名 push。

## 2. 生成质量

第一性：参考技法指纹。

## 3. 爆炸半径

T3 易丢。

## 4. 业务完善性

参考样本。

## 5. 评分

| P_flow | 3 |
| Q_craft | 3 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 合并一次 push + 条数帽 2。

**放弃：** 当正典。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:489-496`