# 单元：continue_snapshot

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_v1.py:111-130
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

有 reread ack 才并入 prefix；否则 soft_fail skip。

## 2. 生成质量

第一性：续写接着昨天的日子。

## 3. 爆炸半径

中。

## 4. 业务完善性

续写仪式。

## 5. 评分

| P_flow | 3 |
| Q_craft | 3 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 独立 push；skip 原因进 report。

**放弃：** 无 ack 也灌快照。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:111-130`