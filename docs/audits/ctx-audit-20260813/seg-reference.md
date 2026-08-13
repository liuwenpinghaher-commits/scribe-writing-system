# 单元：reference

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:1000
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

恒先免责「借鉴非事实」；候选或 list_materials 标题。仅免责则整块视为空。额度 1800。

## 2. 生成质量

第一性：素材不当正典。病：只标题信息量低。探针：有素材 ⇒ 免责行+标题；无素材 ⇒ 块不占额。

## 3. 爆炸半径

误删免责会把素材当事实。回归：borrow_not_fact reason。

## 4. 业务完善性

对应素材消费；非 50k MUST。

## 5. 评分

| P_flow | 4 |
| Q_craft | 4 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 保持免责门；材料空时 omitted 记 no_materials 以便检查器。

**放弃：** 把素材正文当 canonical。

**验收：** 改后用该段名的 assemble/trace 或纯函数断言覆盖本卷宗探针。

## 7. 证据

- `scribe3/context_assembler.py:1000`
- `scribe3/context_assembler.py:1005`