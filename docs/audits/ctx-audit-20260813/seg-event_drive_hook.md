# 单元：event_drive_hook

- 层：L2 | zone：head | 裁剪档：DEF
- 代码锚点：scribe3/api/services/write_assemble_v1.py:257-270
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

有场面合同时 `_event_drive_block` 改走 `format_event_drive_hook_only`，段名 hook、layer supplemental，不进 NEVER。

## 2. 生成质量

第一性：有合同后只留续势钩，避免「优先执行」与场面头双嘴。病：双次读 chapter 判合同（W1 已记）。

## 3. 爆炸半径

误标 redline 则钩焊死。回归：有合同无「优先执行」。

## 4. 业务完善性

对应场面合同 R6。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** contract 对象只判一次并传入 helper（与 W1 event_drive 同一改造）。

**放弃：** 无合同也出 hook。

**验收：** 针对本段名的 assemble 段列表或纯函数断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:257-270`
- `scribe3/api/services/write_assemble_context.py:276-279`