# 单元：codex

- 层：L2 | zone：mid | 裁剪档：T1
- 代码锚点：scribe3/api/services/write_assemble_blocks.py:77
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

V2 在 envelope 后 push；`cap_codex_text` 默认 4500。限知 reveal=not focalizer；for_generation=True fail-closed。V1 兼容塞进 prefix。

## 2. 生成质量

第一性：设定圣经勿串书。病：与 canonical 复读；4500 仍可能洪水。

## 3. 爆炸半径

漏 for_generation 泄密。回归：限知角色 backstory 不进。

## 4. 业务完善性

对应 CL-B1。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 与 canonical 差集后再 cap；观测 codex_chars。

**放弃：** 把 codex 焊进 prefix 回 V1。

**验收：** 针对本段名的 assemble 段列表或纯函数断言。

## 7. 证据

- `scribe3/api/services/write_assemble_blocks.py:77`
- `scribe3/api/services/write_assemble_v1.py:180-192`
- `scribe3/context_budget.py:124`