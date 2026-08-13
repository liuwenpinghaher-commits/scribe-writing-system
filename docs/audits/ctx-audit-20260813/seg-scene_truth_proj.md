# 单元：scene_truth_proj

- 层：L0 | zone：mid | 裁剪档：NEVER
- 代码锚点：`write_assemble_v1.py:533-546`（**仅 `normalized_phase == "deduce"`**）
- 预算：无帽；空真相仍注入占位「尚未填写…」

## 1. 流程完善性

- **读**：`get_chapter.scene_truth`
- **编**：标题「场景真相」+ 原文或占位 + **演绎终检合同**（逐字可追溯、禁止补环境/心理）
- **与 deduction_final**：deduce 阶段走本段；draft/final 走 deduction_final 里的全知真相——**双路径**
- **缺口**：非 deduce 写路径没有本段；占位句可能诱导模型「说明未能确认」交差

## 2. 生成质量

- **第一性**：演绎投影的唯一事实源，防脑补。
- **病**：终检过严会导致空洞投影；与 draft 注入口径不一致（draft 无「终检合同」）。
- **探针**：phase=deduce ⇒ 必有 `scene_truth_proj`；phase=draft ⇒ 本段名不出现。

## 3. 爆炸半径

- 只影响演绎生成；改终检文案改变所有 deduce 输出形状
- 误在 draft 也 push 本段：与 deduction_final 双份真相
- 回归：phase 分流单测

## 4. 业务完善性

- 演绎 Tab 作者可见场景真相编辑器
- 对应 CL-B4；GATE 演绎投影 completeness
- 终检「不得补环境」对「好小说」过窄（投影需要感知细节）但那是 **演绎阶段** 有意收口

## 5. 评分

| 维 | 分 |
|----|----|
| P_flow | 4 |
| Q_craft | 4 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |

## 6. 最优改造

**主方案：** 保持 deduce 终检；在 budget_report 标 `scene_truth_source=proj|deduction_final|none`，避免双路径审计迷路。不把终检合同抄进 draft。

**放弃：** 合并唯一段服务所有 phase（会污染正文写）；去掉占位导致空真相无段（更难发现没填）。

**验收：** deduce 有段；draft 无 `scene_truth_proj` 名。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:533-546`
