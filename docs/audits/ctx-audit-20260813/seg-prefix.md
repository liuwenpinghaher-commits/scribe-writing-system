# 单元：prefix

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_v1.py:91-92
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

`prefix` 现网只留 anti_slop 短核 + 当前第 N 章。`identity` / `write_protocol` / revision / structure_diversity / continue_snapshot / tool_scope / craft_skills_index 已独立 `_push`。

## 2. 生成质量

第一性：身份与硬协议。病：检查器看不到旁路子段。

## 3. 爆炸半径

改 prefix 影响所有红线头。

## 4. 业务完善性

作者不可拆。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

已拆出 identity / write_protocol / revision / structure_diversity / continue_snapshot / tool_scope / craft_skills_index。`prefix` = anti_slop 短核 + 当前第 N 章。

## 6. 最优改造

**主方案（已落地）：** 旁路独立 `_push`；`prefix` 只留 anti_slop + 章号。

**放弃：** 继续往 prefix 塞设定（v1 已禁止）。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:91-92`
- `scribe3/api/services/write_assemble_v1.py:229`