# 单元：craft

- 层：L3 | zone：mid | 裁剪档：T2
- 代码锚点：scribe3/craft.py:1
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

build_craft_block(list_craft_rules)。与 procedural 重叠。

## 2. 生成质量

第一性：书级技法规则。

## 3. 爆炸半径

与信封工艺双份。

## 4. 业务完善性

技法栏 4 条纪律。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：与 envelope procedural 整行去重；剔空记 `empty_craft`。

## 6. 最优改造

**主方案：** 与 procedural compact 去重。

**放弃：** 升 L0。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/craft.py:1`
- `scribe3/api/services/write_assemble_v1.py:337-342`