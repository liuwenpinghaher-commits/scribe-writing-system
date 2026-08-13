# 单元：continue_snapshot

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_v1.py:111-130
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

独立 `_push("continue_snapshot")`。无块 / 需重读未 ack / 异常 → `continue_snapshot_skip` + `budget_report.continue_snapshot_skip_reason`。

## 2. 生成质量

第一性：续写接着昨天的日子。

## 3. 爆炸半径

中。

## 4. 业务完善性

续写仪式。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

## 6. 最优改造

**主方案（已落地）：** 独立 `_push`；skip 走 soft_fail；`continue_snapshot_skip_reason` ∈ {empty_snapshot, reread_ack_required, continue_snapshot_error}。

**放弃：** 无 ack 也灌快照。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:111-130`