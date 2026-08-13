# 单元：avoid

- 层：L3 | zone：mid | 裁剪档：T2
- 代码锚点：scribe3/api/services/prompt_blocks.py:236
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

`should_omit_avoid_domain()` 默认真：不推独立段，记 `avoid_merged_into_antislop`。关旗时才 `_avoid_directive`；空则 `empty_avoid`。budget_report：`avoid_injected` / `avoid_skip_reason`。

## 2. 生成质量

第一性：不与 anti_slop 双份金句表。探针：默认 omit 为真；v1 走 skip 键。

## 3. 爆炸半径

词表不进 L0。误关旗才独立段。

## 4. 业务完善性

连载卫生。默认不把前章措辞表摊给作者看。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：默认 omit 独立段；skip 可查。

## 6. 最优改造

**主方案：** 默认 omit 独立段（已有旗）。**已落地。**

**放弃：** avoid 词表进 L0。

**验收：** `test_avoid_omit.py`

## 7. 证据

- `scribe3/injection_compact.py` `should_omit_avoid_domain`
- `scribe3/api/services/write_assemble_v1.py`
- `scribe3/tests/test_avoid_omit.py`