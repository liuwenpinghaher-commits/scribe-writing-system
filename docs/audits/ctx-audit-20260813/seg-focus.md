# 单元：focus

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:629
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

assemble() 先 `_focus_items`：章/角色焦点 + 可选 query[:200]。章焦点不再展开 synopsis/beats，只指针「见 outline 域」。fail-soft 查不到细节不影响块存在。budget_report 有 `focus_has_outline_pointer`。

## 2. 生成质量

第一性：告诉模型「此刻在看哪一章/谁」，大纲正文只在 outline。探针：有指针 ⇒ report 真；无指针 ⇒ 假。

## 3. 爆炸半径

不回填 synopsis。限知者不因本段变差。

## 4. 业务完善性

「见 outline 域」人话。作者不直接编辑本块。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：指针保留；`focus_has_outline_pointer` 可查。

## 6. 最优改造

**主方案：** 保持指针不去重失败；budget_report 增加 focus_has_outline_pointer 布尔。**已落地。**

**放弃：** 重新把 synopsis[:220] 塞回 focus（已证明双份）。

**验收：** `test_focus_outline_pointer.py`

## 7. 证据

- `scribe3/context_assembler.py` `_focus_detail`
- `scribe3/api/services/write_assemble_context.py` `focus_has_outline_pointer_from_envelope`
- `scribe3/tests/test_focus_outline_pointer.py`