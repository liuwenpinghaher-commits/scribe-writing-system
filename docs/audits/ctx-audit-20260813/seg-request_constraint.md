# 单元：request_constraint

- 层：L3 | zone：tail | 裁剪档：T2
- 代码锚点：scribe3/api/services/write_assemble_v1.py
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

仅非空 `extra_instructions` 才 push。空记 `empty_request_constraint`。budget_report：`request_constraint_injected` / `request_constraint_skip_reason`。

## 2. 生成质量

第一性：这一次作者说的话。空不占槽。

## 3. 爆炸半径

不把整段聊天塞进 prefix。

## 4. 业务完善性

写槽本轮约束。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：空 extra 不 push；skip 可查。

## 6. 最优改造

**主方案：** 空 extra 不 push。**已落地。**

**放弃：** 把整段聊天塞进来。

**验收：** `test_request_constraint_skip.py`

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py`
- `scribe3/tests/test_request_constraint_skip.py`
