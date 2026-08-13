# 单元：pressure_drive

- 层：L2 | zone：mid | 裁剪档：T1
- 代码锚点：scribe3/pressure_drive.py:646
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

load_pdc + render；与 drama 结构化差集，完全重复则空段。fail-soft。

## 2. 生成质量

第一性：力学合同（进度/分叉）不是「作品意图」。病：与 drama GCD 抢嘴；差集失败则整段保留双份。

## 3. 爆炸半径

半径中。回归：pressure_diff_keys。

## 4. 业务完善性

产品已锁「力学合同」文案。

## 5. 评分

| P_flow | 3 |
| Q_craft | 3 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 差集失败记 soft_fail 并仍尝试差集空键；禁止再渲染与 drama 相同的 goal 句。

**放弃：** 升格 L0。

**验收：** 针对本段名的 assemble 段列表或纯函数断言。

## 7. 证据

- `scribe3/pressure_drive.py:646`
- `scribe3/api/services/write_assemble_v1.py:446-476`