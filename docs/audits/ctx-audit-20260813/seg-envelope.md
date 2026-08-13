# 单元：envelope

- 层：L1 | zone：mid | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_v1.py:295-297
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

指针段：`render_envelope_text(envelope)` 一次 push layer=envelope，整包 NEVER。八块细节见独立 W2 卷宗，本段只负责「如何拼进物理序（outline 后、codex 前）」。

## 2. 生成质量

第一性：记忆核整包进模。病：envelope 与八块审计边界需检查器同时展示块长。

## 3. 爆炸半径

改 render 影响全书写路径。

## 4. 业务完善性

作者不可拆段；检查器应显示八块长度。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：budget_report 八键 `envelope_block_lengths`。

## 6. 最优改造

**主方案：** budget_report 必带 envelope_block_lengths 八键。**已落地。**

**放弃：** 在 envelope 卷宗里重写八块评分。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:295-297`
- `scribe3/context_assembler.py:507`