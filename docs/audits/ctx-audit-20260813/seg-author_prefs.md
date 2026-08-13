# 单元：author_prefs

- 层：L3 | zone：mid | 裁剪档：T3
- 代码锚点：scribe3/api/app_impl.py:1152
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

_author_prefs_block_safe fail-safe。T3 先裁。与 procedural 升格重叠。

## 2. 生成质量

第一性：作者偏好。

## 3. 爆炸半径

小。

## 4. 业务完善性

作者设置。

## 5. 评分

| P_flow | 3 |
| Q_craft | 3 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 与 procedural 偏好去重。

**放弃：** 焊 L0。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/app_impl.py:1152`
- `scribe3/api/services/write_assemble_v1.py:477-481`