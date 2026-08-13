# ctx-audit W1 红线评分总表 · 2026-08-13

现网 `NOVEL_PROMPT_HARD=48000`（非对话中的 96k）。分 1–5。

| 单元 | P_flow | Q_craft | R_safety | B_product | Observability | 最优改造（一句） |
|------|--------|---------|----------|-----------|---------------|------------------|
| narrative_contract | 2 | 4 | 4 | 2 | 3 | store 按 narrative_drive 同构打通读写 |
| event_drive | 3 | 3 | 4 | 3 | 3 | assemble 单点判定 + empty_event_drive 可观测 |
| drama_contract | 4 | 2 | 3 | 3 | 4 | 400 字先砍 MRU 套话、保代价/冲突 |
| drama_vacuum | 3 | 3 | 4 | 3 | 3 | 触发改「无 goal∧conflict」+ 可操作短句 |
| outline | 4 | 3 | 4 | 3 | 4 | 半裁改为保拍砍纲 |
| deduction_final | 4 | 3 | 2 | 4 | 2 | 焦点优先压缩 + 整包硬帽 + 单段 push |
| scene_truth_proj | 4 | 4 | 4 | 3 | 3 | budget_report 标明真相源路径 |
| secret_guard | 4 | 3 | 5 | 3 | 2 | 独立 `_push("secret_guard")` + 揭示字段覆盖 |
| focalizer | 4 | 3 | 4 | 3 | 2 | 独立 `_push("focalizer")` |
| final_reminder | 5 | 2 | 4 | 2 | 4 | 默认 CORE 短核，文体按书覆盖 |
