# 单元：uncertainty

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:1069
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

superseded 行先产出，allocate 再 `prioritize_superseded_items`。budget_report：`uncertainty_superseded_count` / `uncertainty_pending_count`。

## 2. 生成质量

第一性：别把旧推测当事实。探针：reason=superseded 排在待确认前。

## 3. 爆炸半径

不并进 canonical。只改 uncertainty 序。

## 4. 业务完善性

文案「旧推测已被正典取代(存疑,勿据此写)」。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：superseded 优先；观测两键。

## 6. 最优改造

**主方案：** 保留 superseded 行优先于低信心闲聊。**已落地。**

**放弃：** 并进 canonical（污染真值）。

**验收：** `test_uncertainty_superseded.py`

## 7. 证据

- `scribe3/api/services/write_assemble_context.py` `prioritize_superseded_items`
- `scribe3/context_assembler.py` `_allocate` / `_uncertainty_items`
- `scribe3/tests/test_uncertainty_superseded.py`