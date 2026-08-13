# 单元：structure_diversity

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_v1.py:94-110
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

flag 开则独立 `_push("structure_diversity")`；fail-soft。不并 38 篇文件名（产品纪律）。

## 2. 生成质量

第一性：别复读上一章结构模子。病：短纪律易被忽略。

## 3. 爆炸半径

误把方法论全文并进本段违 38 融合设计。

## 4. 业务完善性

对应结构多样性 SHOULD。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

## 6. 最优改造

**主方案（已落地）：** 短纪律独立 `_push`，不再吞进 prefix。

**放弃：** 把 oh-story 38 篇原文塞进来。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:94-110`
- `scribe3/structure_style.py:12`