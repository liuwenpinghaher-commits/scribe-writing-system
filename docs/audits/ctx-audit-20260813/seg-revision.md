# 单元：revision

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_blocks.py:428
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

独立 `_push("revision")`。`is_revision_request(phase/request_text/extra)` 为假则不注入，记 `revision_skip_not_requested`。budget_report：`revision_injected` / `revision_skip_reason`。

## 2. 生成质量

第一性：改稿时 span 级定向，首稿不灌修订手册。探针：draft/续写为假；revise/重写/改这段为真。

## 3. 爆炸半径

只少注、不改秘密门。首稿不再被「其余一字不动」绑住。

## 4. 业务完善性

修订环。作者看见「修订纪律」仅当在改稿。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

P1：非修订请求不注入。

## 6. 最优改造

**主方案：** 非修订请求不注入。**已落地。**

**放弃：** 每次都长文修订手册。

**验收：** `test_revision_gate.py`

## 7. 证据

- `scribe3/api/services/write_assemble_blocks.py` `is_revision_request`
- `scribe3/api/services/write_assemble_v1.py` 条件 `_push("revision")`
- `scribe3/tests/test_revision_gate.py`