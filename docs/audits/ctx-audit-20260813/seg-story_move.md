# 单元：story_move

- 层：L3 | zone：mid | 裁剪档：T3
- 代码锚点：scribe3/story_move.py:1
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

仅旗开且章有已批计划才注入 ≤1 卡+≤2 旧用；否则零字节。段名不含 38 原文文件名。默认旗 0。

## 2. 生成质量

第一性：已批招式绕法。纪律已严。

## 3. 爆炸半径

误把 38 篇并入会炸注意力。

## 4. 业务完善性

招式栏 5 卡。

## 5. 评分

| P_flow | 4 |
| Q_craft | 4 |
| R_safety | 4 |
| B_product | 4 |
| Observability | 4 |

## 6. 最优改造

**主方案：** 保持零字节默认；观测 plan_missing 原因。

**放弃：** 无计划也灌卡。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/story_move.py:1`
- `scribe3/api/services/write_assemble_v1.py:620`
- `scribe3/feature_flags.py:106`