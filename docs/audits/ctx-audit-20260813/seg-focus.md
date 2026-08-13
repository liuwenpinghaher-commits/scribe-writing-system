# 单元：focus

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:612
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

assemble() 先 `_focus_items`：章/角色焦点 + 可选 query[:200]。章焦点不再展开 synopsis/beats，只指针「见 outline 域」。fail-soft 查不到细节不影响块存在。经 `_allocate` 受 BLOCK_BUDGETS_NOVEL focus=1000。

## 2. 生成质量

第一性：告诉模型「此刻在看哪一章/谁」。病：query 截 200；章焦点只剩指针，注意力全靠 outline。探针：有章 ⇒ 含「当前第 N 章」。

## 3. 爆炸半径

改 _focus_items 影响所有写路径信封。误再展开大纲会与 outline 双份。回归：focus 指针单测 / envelope hash。

## 4. 业务完善性

作者不直接编辑本块；对应 CL-B5 此刻焦点。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 保持指针不去重失败；budget_report 增加 focus_has_outline_pointer 布尔。

**放弃：** 重新把 synopsis[:220] 塞回 focus（已证明双份）。

**验收：** 改后用该段名的 assemble/trace 或纯函数断言覆盖本卷宗探针。

## 7. 证据

- `scribe3/context_assembler.py:612`
- `scribe3/context_assembler.py:642`
- `scribe3/context_assembler.py:436`