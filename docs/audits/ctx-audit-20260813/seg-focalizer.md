# 单元：focalizer

- 层：L0 head redline | 裁剪档：NEVER | 已独立 `_push`
- 代码锚点：`epistemic_guard.py` 横幅；`write_assemble_v1.py` `_push("focalizer","redline")`
- 预算：短横幅

## 1. 流程完善性

- **读**：assemble 参数 `focalizer`
- **编**：非空 → 限知横幅；空 → 全知横幅（点明 secret_guard 仍约束）
- **注**：独立 `_push`，prefix 不再内嵌
- 下游：同一 `focalizer` 仍传入 envelope / codex / outline / drama

## 2. 生成质量

- 声明本章认知分身。全知横幅不再暗示「可以泄密」。
- 残留：横幅短，模型仍可能 head-hop（不是本段能独自解决的）。
- 探针：`scribe3/tests/test_focalizer_segment.py`

## 3. 爆炸半径

- 独立红线段；NEVER 按名生效。未改 48k。

## 4. 业务完善性

- 限知/全知文案人话；检查器可见独立段。

## 5. 评分（P1 后诚实 5）

| 维 | 分 |
|----|----|
| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

## 6. 最优改造

**主方案：** 独立 `_push("focalizer")` + 全知横幅点明 secret_guard。**已落地。**

## 7. 证据

- `scribe3/epistemic_guard.py` `writing_*_banner`
- `scribe3/api/services/write_assemble_v1.py` `_push("focalizer")`
- `scribe3/tests/test_focalizer_segment.py`
