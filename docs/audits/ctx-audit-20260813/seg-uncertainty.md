# 单元：uncertainty

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:1028
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

低信心候选 + 被正典取代的 episodic 提示。额度 800。

## 2. 生成质量

第一性：告诉模型别把旧推测当事实。病：800 易挤掉；文案弱。探针：有 superseded ⇒ 含「已被正典取代」。

## 3. 爆炸半径

半径小。回归：superseded 进 uncertainty。

## 4. 业务完善性

对应待确认/正典冲突。

## 5. 评分

| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 保留 superseded 行优先于低信心闲聊（allocate 时先留 reason=superseded）。

**放弃：** 并进 canonical（污染真值）。

**验收：** 改后用该段名的 assemble/trace 或纯函数断言覆盖本卷宗探针。

## 7. 证据

- `scribe3/context_assembler.py:1028`
- `scribe3/context_assembler.py:437`