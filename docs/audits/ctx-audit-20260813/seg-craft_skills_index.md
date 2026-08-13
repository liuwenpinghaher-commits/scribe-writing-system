# 单元：craft_skills_index

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/craft_skills.py:43
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

技法索引渐进披露。with_tools。并入 prefix。

## 2. 生成质量

第一性：有哪些纪律可点开。不应是 38 全文。

## 3. 爆炸半径

误灌全文炸窗。

## 4. 业务完善性

技法 4 条。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 2 |

## 6. 最优改造

**主方案：** 保持索引；独立 push。

**放弃：** 把 4 篇全文塞进 L0。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/craft_skills.py:43`
- `scribe3/api/services/write_assemble_v1.py:144-148`