# 单元：seed_words

- 层：L3 | zone：mid | 裁剪档：T3
- 代码锚点：scribe3/api/app_impl.py:1247
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

_soak_block(seed_words) 必 push（可空）。T3 先裁。

## 2. 生成质量

第一性：本轮浸泡词。空则浪费段槽。

## 3. 爆炸半径

半径小。

## 4. 业务完善性

写作槽种子。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 空 soak 不 push。

**放弃：** 把种子当正典。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/app_impl.py:1247`
- `scribe3/api/services/write_assemble_v1.py:304-308`