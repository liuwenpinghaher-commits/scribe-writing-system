# 单元：brief_must

- 层：L2 | zone：mid | 裁剪档：PROT
- 代码锚点：scribe3/api/services/write_assemble_context.py:473
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

章简报 must 节；写路径 pop 掉 drama_contract 防双份。PROT 半保护。

## 2. 生成质量

第一性：必须写进场面的要点。病：与 outline/contract 复述。

## 3. 爆炸半径

误丢 PROT 先砍 must。

## 4. 业务完善性

对应 CL-B5 要点。

## 5. 评分

| P_flow | 3 |
| Q_craft | 3 |
| R_safety | 3 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** must 节只保留 outline/contract 没有的键。

**放弃：** 再把 drama 塞回 brief。

**验收：** 针对本段名的 assemble 段列表或纯函数断言。

## 7. 证据

- `scribe3/api/services/write_assemble_context.py:473`
- `scribe3/api/services/write_assemble_v1.py:440-444`