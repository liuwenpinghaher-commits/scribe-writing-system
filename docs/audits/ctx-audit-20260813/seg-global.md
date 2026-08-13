# 单元：global

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:668
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

fail-loud 读 get_intent + 开放伏笔 + 主要角色（U-011 删静默空）。红线可被 should_strip_iron_laws 整段不注入。额度 1800。

## 2. 生成质量

第一性：全书稳定层（读者感受/弧/红线/未收伏笔）。病：文案仍写「北极星」产品已改「作品意图」可能串词。探针：有 intent ⇒ 含读者感受字段。

## 3. 爆炸半径

改 global 影响每章写路径与限知无关的红线展示。回归：get_intent fail-loud 测。

## 4. 业务完善性

对应 CL-B0；50k M2。作者改 intent 后应出现在本块。

## 5. 评分

| P_flow | 4 |
| Q_craft | 4 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 渲染标签改为「作品意图」对齐产品文案；strip 红线时留「红线已按实验剥离」一行以免像没配置。

**放弃：** 取数失败再改回静默空（U-011 禁止）。

**验收：** 改后用该段名的 assemble/trace 或纯函数断言覆盖本卷宗探针。

## 7. 证据

- `scribe3/context_assembler.py:668`
- `scribe3/context_assembler.py:676`