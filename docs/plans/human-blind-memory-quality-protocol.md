# 人盲质量封顶协议（OQ3 · rev.4）

## 目的
唯一允许对外宣称任一维 **≥9.5** 的路径。机器 A/B / M 绿 **不得** 单独封顶。

## 规格（拍板）
| 项 | 要求 |
|----|------|
| 评者 | **≥2** 名独立评者，双盲（不知 A/B 哪边开记忆） |
| 材料 | 同 synopsis 轨 2 成稿各 1 份（可加第 2 章稳健性） |
| 量表 | coherence / canon_echo / contradiction · 1–5 |
| 主观 | 「记忆是否在扛设定」Y/N |
| D6 | 认知问卷 **≥5 人次**，目标「否」≥80% |
| 通过 | 人评三项均 ≥4.5 且 lead≥1.5 → `human_pass_rule_met=true` |
| 禁止 | LLM-as-judge 单独定 9.5；M0–M6 绿；仅 heuristic |

## 流程
1. 工程产出 `a_prose.md` / `b_prose.md`（去头标签，随机化为 X/Y）  
2. 评者独立填 `human_blind_scores.template.json`  
3. 汇总 lead；写回 scores.json 的 `human_pass_rule_met`  
4. 缺人评维质量分封顶 ≤6.5–8.0 叙事（见 rescore 模板）

## 模板文件
- `docs/plans/human_blind_scores.template.json`
- 旅程侧 D6：`scripts/quality_wave_c_templates.py`
