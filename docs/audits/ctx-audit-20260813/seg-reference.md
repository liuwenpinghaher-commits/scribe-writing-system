# 单元：reference

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:1041
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

恒先免责「借鉴非事实」。仅免责则整块空，omitted 记 `no_materials`。budget_report：`reference_no_materials`。

## 2. 生成质量

第一性：素材不当正典。探针：空库 ⇒ no_materials；有标题才占额。

## 3. 爆炸半径

免责门保留。不把素材正文当 canonical。

## 4. 业务完善性

免责文案「借鉴非事实」人话。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：空素材 omitted.no_materials。

## 6. 最优改造

**主方案：** 保持免责门；材料空时 omitted 记 no_materials。**已落地。**

**放弃：** 把素材正文当 canonical。

**验收：** `test_reference_no_materials.py`

## 7. 证据

- `scribe3/context_assembler.py` `_reference_items` / assemble omitted
- `scribe3/api/services/write_assemble_context.py` `reference_no_materials_from_envelope`
- `scribe3/tests/test_reference_no_materials.py`