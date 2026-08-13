# 单元：volume_intro

- 层：L3 | zone：mid | 裁剪档：T2
- 代码锚点：scribe3/api/services/write_assemble_context.py:230
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

`compact_volume_intro` 相对 synopsis/outline。空 intro/无卷/compact 空 → 不 push，记 `empty_volume_intro`。budget_report：`volume_intro_injected` / `volume_intro_skip_reason`。

## 2. 生成质量

第一性：卷氛围不得盖章大纲。探针：标题已在大纲里 → 卷钩≤120。

## 3. 爆炸半径

不把卷纲当本章大纲。

## 4. 业务完善性

「本卷卷纲摘要(作者备忘…)」人话。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：compact + 空不 push。

## 6. 最优改造

**主方案：** 保持 compact；空不 push。**已落地。**

**放弃：** 卷纲当本章大纲。

**验收：** `test_volume_intro_skip.py`

## 7. 证据

- `scribe3/injection_compact.py` `compact_volume_intro`
- `scribe3/api/services/write_assemble_v1.py`
- `scribe3/tests/test_volume_intro_skip.py`