# 单元：avoid

- 层：L3 | zone：mid | 裁剪档：T2
- 代码锚点：scribe3/api/services/prompt_blocks.py:236
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

前章措辞避免复读；should_omit_avoid_domain 可并入 anti_slop 则不独立段。

## 2. 生成质量

第一性：跨章不复读金句。

## 3. 爆炸半径

误关 omit 双份。

## 4. 业务完善性

连载卫生。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 默认 omit 独立段（已有旗）。

**放弃：** avoid 词表进 L0。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/prompt_blocks.py:236`
- `scribe3/api/services/write_assemble_v1.py:361-373`