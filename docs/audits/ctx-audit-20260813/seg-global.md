# 单元：global

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:690
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

fail-loud 读 get_intent。strip 红线时正文写「红线已按实验剥离」。budget_report：`global_iron_stripped`。

## 2. 生成质量

第一性：全书稳定层。标签「作品意图」。探针：标题/行首用作品意图；strip 行可观测。

## 3. 爆炸半径

不改取数 fail-loud。purpose 已认「作品意图」。

## 4. 业务完善性

对齐产品文案「作品意图」，不再信封写北极星。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：作品意图 + strip 明示行。

## 6. 最优改造

**主方案：** 渲染标签改为「作品意图」；strip 红线留明示行。**已落地。**

**放弃：** 取数失败再改回静默空（U-011 禁止）。

**验收：** `test_global_intent_label.py`

## 7. 证据

- `scribe3/context_assembler.py` `_HEADERS["global"]` / `_global_items`
- `scribe3/api/services/write_assemble_context.py` `global_iron_stripped_from_envelope`
- `scribe3/tests/test_global_intent_label.py`