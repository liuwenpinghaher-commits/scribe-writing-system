# 单元：procedural

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:998
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

已采纳工艺/教训；有候选走检索，否则 `list_craft_rules[:8]`（真实键 kind/pattern/note）。作者偏好经 `_author_preference_constraint` 升格。`list_craft_rules` 失败 fail-loud。assemble 后 `_dedup_procedural_against_craft`：相对 `build_craft_block` compact 去重，命中记 `omitted.reason=deduped_by_craft`。budget_report 有 `procedural_item_count` / `procedural_dedup_dropped`。

## 2. 生成质量

第一性：怎么写（非剧情事实），且只留 craft 段没有的已采纳教训。探针：与 craft 同行 compact 命中则丢、独有教训保留。

## 3. 爆炸半径

去重只删不增。cover 组装失败 fail-soft 保原文。回归：`list_craft_rules` 失败仍 fail-loud。

## 4. 业务完善性

对应 CL-B5 技法卫生。信封标题仍是「工艺方法(已采纳的写作方法/教训)」。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：assemble 对 craft 做 compact 去重；空/失败可分；观测两键。

## 6. 最优改造

**主方案：** assemble 对 craft 段与 procedural 做 compact 去重（已有 phase_role 去重可仿）。**已落地。**

**放弃：** 再加第四处工艺注入。

**验收：** `test_procedural_craft_dedup.py` 覆盖 compact 探针 + v1/assembler 接线。

## 7. 证据

- `scribe3/injection_compact.py` `line_echoes_cover` / `filter_procedural_lines`
- `scribe3/context_assembler.py` `_dedup_procedural_against_craft`
- `scribe3/api/services/write_assemble_context.py` `procedural_stats_from_envelope`
- `scribe3/tests/test_procedural_craft_dedup.py`