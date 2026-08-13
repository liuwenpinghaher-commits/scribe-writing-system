# 单元：identity

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_blocks.py:378
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

`_editor_identity_block` 纯身份，不灌设定。独立 `_push("identity")`，不并入 prefix。

## 2. 生成质量

第一性：你是本书主编/作者助手。

## 3. 爆炸半径

改身份影响所有书。

## 4. 业务完善性

系统人格。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

## 6. 最优改造

**主方案（已落地）：** 独立 `_push("identity")`，NEVER 按名裁。prefix 不再吞身份。

**放弃：** 身份块再拼圣经。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_blocks.py:378`
- `scribe3/api/services/write_assemble_v1.py:91`