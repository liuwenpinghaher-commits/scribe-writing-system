# 单元：voice_anchor

- 层：L2 | zone：mid | 裁剪档：PROT
- 代码锚点：scribe3/api/services/write_assemble_context.py:57
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

有 profile 注入声口；无则一行「未登记声口」。budget_report：`voice_anchor_registered`。

## 2. 生成质量

第一性：这一章的声音。探针：无 profile ⇒ 未登记声口；有 style_summary ⇒ 不出现该句。

## 3. 爆炸半径

不把别人声口当焦点者。

## 4. 业务完善性

「未登记声口」人话，不像空段丢了。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：无 profile 写「未登记声口」。

## 6. 最优改造

**主方案：** 无 profile 时一行「未登记声口」而非空。**已落地。**

**放弃：** 把别人声口也注入。

**验收：** `test_voice_anchor_unregistered.py`

## 7. 证据

- `scribe3/api/services/write_assemble_context.py` `_voice_anchor_block`
- `scribe3/tests/test_voice_anchor_unregistered.py`