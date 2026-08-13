# 单元：phase_role

- 层：L3 | zone：mid | 裁剪档：T2
- 代码锚点：scribe3/api/services/misc_helpers.py:242
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

按 phase 角色句；`dedup_phase_role` 相对 craft/anti_slop。空 phase / 去重后空 → 不 push，记 `phase_role_skip_empty`。budget_report：`phase_role_injected` / `phase_role_skip_reason`。

## 2. 生成质量

第一性：本阶段职责且不复读 craft。探针：与 craft 全覆盖 → 空；独有句保留。

## 3. 爆炸半径

去重只删。空不占段。

## 4. 业务完善性

阶段 Tab。「阶段角色」人话。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：保持去重；空不 push。

## 6. 最优改造

**主方案：** 保持去重；空 phase 不 push。**已落地。**

**放弃：** 每阶段长文。

**验收：** `test_phase_role_skip.py`

## 7. 证据

- `scribe3/injection_compact.py` `dedup_phase_role`
- `scribe3/api/services/write_assemble_v1.py`
- `scribe3/tests/test_phase_role_skip.py`