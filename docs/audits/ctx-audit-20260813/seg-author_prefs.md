# 单元：author_prefs

- 层：L3 | zone：mid | 裁剪档：T3
- 代码锚点：scribe3/api/app_impl.py:1152
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

`_author_prefs_block_safe` fail-safe。T3 先裁。相对 envelope 整行差集；空则 `empty_author_prefs`。

## 2. 生成质量

第一性：作者偏好。

## 3. 爆炸半径

小。

## 4. 业务完善性

作者设置。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

## 6. 最优改造

**主方案（已落地）：** 相对 envelope 整行差集 + `empty_author_prefs`，不焊 L0。

**放弃：** 焊 L0。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/app_impl.py:1152`
- `scribe3/api/services/write_assemble_v1.py:477-481`