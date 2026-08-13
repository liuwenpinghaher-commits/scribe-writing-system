# 单元：discourse_soft

- 层：L3 | zone：mid | 裁剪档：T3
- 代码锚点：scribe3/discourse_inject.py:75
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

话语讲法/连载 meso+serial；finding 不进 finalize 硬阻塞。

## 2. 生成质量

第一性：怎么说话，不是剧情。

## 3. 爆炸半径

与 final_reminder 文体叠。

## 4. 业务完善性

话语层。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：与 `_final_reminder` 整行差集；剔空 `skip_reason=echo_core_or_empty`。

## 6. 最优改造

**主方案：** 与 CORE 尾注差集。

**放弃：** discourse finding 升硬门（设计禁止）。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/discourse_inject.py:75`
- `scribe3/api/services/write_assemble_v1.py:587`