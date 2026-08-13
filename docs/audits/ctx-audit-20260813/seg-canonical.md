# 单元：canonical

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:725
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

权威事实：facts/events/promises/知识帧。限知投影 + C1 无条件剔除势力镜像机密字段。正典优先：同 entity/attr 的 episodic 进 omitted。额度 9200 最大块。ablation 可关 fact 注入。

## 2. 生成质量

第一性：书内真值（限知后）。病：与 prefix 旧 _editor_system 重复已由 v1 拆开；仍可能和 codex 段复读设定。探针：focalizer 非空时 secret value 不得明文。

## 3. 爆炸半径

误关投影 = 泄密（最高半径）。回归：project_frame / partition_facts / superseded_by_canonical。

## 4. 业务完善性

对应 CL-B1/B4；50k M3/M8。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：canonical 相对 codex 结构化差集；`canonical_codex_echoes_dropped`。

## 6. 最优改造

**主方案：** codex 与 canonical 做结构化差集（已在 codex 的角色/规则勿再以 fact 行复读）。**已落地。**

**放弃：** 加大 9200 挤死其他块；或无焦点就灌全部 secret。

**验收：** 改后用该段名的 assemble/trace 或纯函数断言覆盖本卷宗探针。

## 7. 证据

- `scribe3/context_assembler.py:725`
- `scribe3/context_assembler.py:239`
- `scribe3/context_assembler.py:19`