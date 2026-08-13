# 单元：purpose

- 层：L2 | zone：mid | 裁剪档：T1
- 代码锚点：scribe3/api/app_impl.py:1284
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

目的/工作流块；with_tools 时更长。

## 2. 生成质量

第一性：本章目的。易与 intent/global 混。

## 3. 爆炸半径

中。

## 4. 业务完善性

作品意图已在 global。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：envelope global 已有北极星时，purpose 只留本章 delta / 滚入；空章改为一句「北极星已在全局段」。

## 6. 最优改造

**主方案：** 若 global 已有意图则 purpose 只留「本章目的」差集。

**放弃：** 复制北极星全文。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/app_impl.py:1284`
- `scribe3/api/services/write_assemble_v1.py:381-385`