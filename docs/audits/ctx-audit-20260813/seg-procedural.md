# 单元：procedural

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:980
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

已采纳工艺/教训；有候选走检索，否则 list_craft_rules[:8] 各 80 字。作者偏好经 _author_preference_constraint 升格。fail-loud。额度 1400。

## 2. 生成质量

第一性：怎么写（非剧情事实）。病：与独立 craft 段、author_prefs 三处工艺。探针：有 craft_rules ⇒ 含「工艺:」。

## 3. 爆炸半径

与 craft 段双份。回归：list_craft_rules fail-loud。

## 4. 业务完善性

对应 CL-B5 技法卫生。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** assemble 对 craft 段与 procedural 做 compact 去重（已有 phase_role 去重可仿）。

**放弃：** 再加第四处工艺注入。

**验收：** 改后用该段名的 assemble/trace 或纯函数断言覆盖本卷宗探针。

## 7. 证据

- `scribe3/context_assembler.py:980`
- `scribe3/context_assembler.py:75`