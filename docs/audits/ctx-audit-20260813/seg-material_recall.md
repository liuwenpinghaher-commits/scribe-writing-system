# 单元：material_recall

- 层：L3 | zone：mid | 裁剪档：T3
- 代码锚点：scribe3/api/services/write_assemble_context.py:531
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

仅 draft/final；素材召回。T3 最先丢。

## 2. 生成质量

第一性：可借用素材。与 envelope reference 重叠。

## 3. 爆炸半径

小。

## 4. 业务完善性

素材库。

## 5. 评分

| P_flow | 3 |
| Q_craft | 3 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 与 reference 块去重标题。

**放弃：** 当事实写入。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_context.py:531`
- `scribe3/api/services/write_assemble_v1.py:524-530`