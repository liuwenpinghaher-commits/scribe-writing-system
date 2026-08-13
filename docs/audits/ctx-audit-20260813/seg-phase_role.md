# 单元：phase_role

- 层：L3 | zone：mid | 裁剪档：T2
- 代码锚点：scribe3/api/services/misc_helpers.py:242
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

按 phase 角色句；dedup_phase_role 相对 craft/anti_slop。

## 2. 生成质量

第一性：本阶段（大纲/草稿）职责。

## 3. 爆炸半径

半径小。

## 4. 业务完善性

阶段 Tab。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 保持去重；空 phase 不 push。

**放弃：** 每阶段长文。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/misc_helpers.py:242`
- `scribe3/api/services/write_assemble_v1.py:343-360`