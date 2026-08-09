# pressure_progress_ab_v1 · 人盲进度感问卷

> 仅人读；**禁止**用 machine 分宣称文学达标或不拖沓。  
> MVP 工程交付：n=1 作者自读 + 三问书面记录即可；下列 1–5 为问卷默认，**不作 CI gate**。

## 样本
- 书 / 章：
- 臂 / 版本 id：
- 是否含 progress 合同：是 / 否

## 评分（1–5）

| 维 | 题干 | 分 |
|----|------|----|
| plot_moved | 读完是否觉得「事情往前挪了」？ | |
| grind_felt | 是否长时间停在同一处磨？（5=磨很久） | |
| retreat_cost_felt | 若有退缩，是否付了可见代价？ | |
| idle_vs_main | 闲笔是否压过主事？（5=闲笔压主） | |
| overall_pressure | 是否被压力推着走？ | |
| irreversible_visible | 是否见到收不回的痕迹？ | |

## 建议阈值（非 CI）
- plot_moved ≥ 4 且 grind_felt ≤ 2 → 进度感倾向通过（可标定）
- 未达标：先查合同 stairs / 注入 / imper_by_kind 接线，**禁止**叠 prompt

## 机检对照（可选粘贴）
- stairs hit/need：
- grind tier：
- retreat_no_cost：
