# 单元：provenance

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:1045
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

派生清单不复制正文。BLOCK 额度为 0，默认不进模型；density 盯 provenance_in_prompt 必须 0。forbidden_source_kinds 可再滤。

## 2. 生成质量

第一性：审计用非生成用。病：若误注入会泄 source 结构且浪费窗。探针：joined 不含「## 溯源清单」除非实验打开额。

## 3. 爆炸半径

误把额度>0 进模：泄密/占窗。回归：G1 provenance_in_prompt false。

## 4. 业务完善性

作者不可见；检查器可见。

## 5. 评分

| P_flow | 5 |
| Q_craft | 2 |
| R_safety | 5 |
| B_product | 2 |
| Observability | 5 |

## 6. 最优改造

**主方案：** 维持 0 额度；检查器读 envelope.omitted / trace 而非 prompt。

**放弃：** 为了「可解释」把 provenance 灌进 48k。

**验收：** 改后用该段名的 assemble/trace 或纯函数断言覆盖本卷宗探针。

## 7. 证据

- `scribe3/context_assembler.py:1045`
- `scribe3/context_budget.py:50`
- `scribe3/injection_registry.py:113`