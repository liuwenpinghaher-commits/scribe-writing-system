# 单元：anti_slop

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_blocks.py:445
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

防套话地板。并入 prefix。与 sincerity/reminder 叠。

## 2. 生成质量

第一性：别油。质量靠禁令弱。

## 3. 爆炸半径

焊死。

## 4. 业务完善性

卫生。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：与 sincerity 收成 prefix 内一处短核；不再独立 `_push("sincerity")`。

## 6. 最优改造

**主方案：** 三处 slop 收成一处短核。

**放弃：** 再加形容词黑名单硬拦。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_blocks.py:445`