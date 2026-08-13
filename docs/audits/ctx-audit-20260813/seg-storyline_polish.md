# 单元：storyline_polish

- 层：L3 | zone：mid | 裁剪档：T3
- 代码锚点：scribe3/storyline_inject_polish.py:1
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

prepare_write_storyline_inject fail-soft 永不抛。

## 2. 生成质量

第一性：故事线润色。旗/数据空则无段。

## 3. 爆炸半径

中（storyline 子系统）。

## 4. 业务完善性

StorylineHub。

## 5. 评分

| P_flow | 3 |
| Q_craft | 3 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 空 meta 不 push；观测 skip 原因。

**放弃：** 焊进 L0。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/storyline_inject_polish.py:1`
- `scribe3/api/services/write_assemble_v1.py:554-567`