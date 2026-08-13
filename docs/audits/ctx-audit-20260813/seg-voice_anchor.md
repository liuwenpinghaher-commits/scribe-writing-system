# 单元：voice_anchor

- 层：L2 | zone：mid | 裁剪档：PROT
- 代码锚点：scribe3/api/services/write_assemble_context.py:57
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

焦点者声口 profile；PROT。

## 2. 生成质量

第一性：这一章的声音。

## 3. 爆炸半径

误裁丢声口。

## 4. 业务完善性

CL-B5 声口。

## 5. 评分

| P_flow | 4 |
| Q_craft | 4 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 无 profile 时一行「未登记声口」而非空。

**放弃：** 把别人声口也注入。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_context.py:57`
- `scribe3/api/services/write_assemble_v1.py:482-486`