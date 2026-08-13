# 单元：volume_intro

- 层：L3 | zone：mid | 裁剪档：T2
- 代码锚点：scribe3/api/services/write_assemble_context.py:215
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

卷 intro clip；compact 相对 synopsis。无卷/空 intro 空串。

## 2. 生成质量

第一性：卷氛围备忘不得盖章大纲。

## 3. 爆炸半径

小。

## 4. 业务完善性

卷 IA。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 保持 compact；空不 push。

**放弃：** 卷纲当本章大纲。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_context.py:215`
- `scribe3/api/services/write_assemble_v1.py:406-439`