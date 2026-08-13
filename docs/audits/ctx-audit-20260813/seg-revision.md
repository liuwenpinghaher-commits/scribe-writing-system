# 单元：revision

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_blocks.py:428
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

_write_revision_block 修订约束。并入 prefix。

## 2. 生成质量

第一性：改稿时保事实。

## 3. 爆炸半径

小。

## 4. 业务完善性

修订环。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 2 |

## 6. 最优改造

**主方案：** 非修订请求不注入。

**放弃：** 每次都长文修订手册。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_blocks.py:428`