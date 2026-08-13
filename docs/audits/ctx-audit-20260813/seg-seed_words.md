# 单元：seed_words

- 层：L3 | zone：mid | 裁剪档：T3
- 代码锚点：scribe3/api/app_impl.py:1247
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

`_soak_block` 空串则不 push，记 `empty_seed_words`。有词才独立段。budget_report：`seed_words_injected` / `seed_words_skip_reason`。

## 2. 生成质量

第一性：本轮浸泡词。空不占槽。探针：空 skip；非空才 `_push("seed_words")`。

## 3. 爆炸半径

不把种子当正典。

## 4. 业务完善性

「情绪种子词」人话。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：空 soak 不 push。

## 6. 最优改造

**主方案：** 空 soak 不 push。**已落地。**

**放弃：** 把种子当正典。

**验收：** `test_seed_words_skip.py`

## 7. 证据

- `scribe3/api/app_impl.py` `_soak_block`
- `scribe3/api/services/write_assemble_v1.py`
- `scribe3/tests/test_seed_words_skip.py`