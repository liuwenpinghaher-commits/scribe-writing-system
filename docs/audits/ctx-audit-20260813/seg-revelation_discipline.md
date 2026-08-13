# 单元：revelation_discipline

- 层：L0 | zone：mid | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/prompt_blocks.py:424
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

无焦点者不注入（`revelation_skip_no_focalizer`）。有焦点者则相对 CORE 差集，只留一句；全覆盖记 `revelation_echo_core`。budget_report：`revelation_injected` / `revelation_skip_reason`。

## 2. 生成质量

第一性：配角勿批发真相（CORE 未写的那一句）。探针：CORE 原句行丢、只留 1 条子弹。

## 3. 爆炸半径

差集只删。全知章不灌限知纪律。

## 4. 业务完善性

标题仍是「限知揭示纪律」。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：与 CORE 只留一句差集。

## 6. 最优改造

**主方案：** 与 CORE 尾注差集，只保留尾注没有的一句。**已落地。**

**放弃：** 再写第三份揭示纪律。

**验收：** `test_revelation_core_delta.py`

## 7. 证据

- `scribe3/injection_compact.py` `clip_revelation_to_core_delta`
- `scribe3/api/services/write_assemble_v1.py`
- `scribe3/tests/test_revelation_core_delta.py`