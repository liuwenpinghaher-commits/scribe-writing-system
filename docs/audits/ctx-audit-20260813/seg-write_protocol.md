# 单元：write_protocol

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_blocks.py:391
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

独立 `_push("write_protocol")`（L0_NEVER_CUT，序在 identity 后、prefix 前）。相对 `_final_reminder()` 整行差集；空则 `write_protocol_echo_core_or_empty`。budget_report：`write_protocol_injected` / `write_protocol_skip_reason`。

## 2. 生成质量

第一性：讨论 vs 动稿 + 围栏 HOWTO。CORE 已有的整行不复读。探针：HOW TO 保留；CORE 原句行丢弃。

## 3. 爆炸半径

差集只删不增。限知/秘密门不在本段。

## 4. 业务完善性

写路径合同。作者能读「讨论 vs 动稿」。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：独立段 + 与 CORE 尾注差集。

## 6. 最优改造

**主方案：** 与 CORE 尾注差集。**已落地。**

**放弃：** 加长协议小说。

**验收：** `test_write_protocol_core_diff.py`

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py` `_push("write_protocol")`
- `scribe3/context_budget.py` `generation_physical_order_names`
- `scribe3/tests/test_write_protocol_core_diff.py`