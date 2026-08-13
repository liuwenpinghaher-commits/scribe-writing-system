# 单元：recent

- 层：L1-env | zone：mid | 裁剪档：ENV
- 代码锚点：scribe3/context_assembler.py:943
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000` / 信封 22000

## 1. 流程完善性

working+episodic 候选映射为 recent；无 retriever 时直查近期事件/决策。额度 6000。fabric 关则 query 空、经验通道弱。

## 2. 生成质量

第一性：近几章日子与决策。病：fabric 关时块瘦；与 story_ember 设计重叠但 ember 现网未 push。探针：有 episodic 命中 ⇒ recent 非空。

## 3. 爆炸半径

改映射影响记忆是否进模。回归：source_kind working/episodic → recent。

## 4. 业务完善性

对应 CL-B6 记忆；50k M9。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：fabric 开且 query 空时兜底「第 N 章续写」并记 `recent_query_fallback`；`budget_report.recent_item_count` 可查。

## 6. 最优改造

**主方案：** fabric 开时保证 _build_write_retrieval_query 非空（v1 已有）；观测 recent_item_count。

**放弃：** 把 recent 焊 L0（抢红线窗）。

**验收：** 改后用该段名的 assemble/trace 或纯函数断言覆盖本卷宗探针。

## 7. 证据

- `scribe3/context_assembler.py:943`
- `scribe3/context_assembler.py:440`