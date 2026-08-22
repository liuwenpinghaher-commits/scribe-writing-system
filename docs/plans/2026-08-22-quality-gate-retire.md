# 旧判定四套退役表

QualityGate 现在是统一出口形状。旧四套先影子接入，再翻主，最后删码。

| 套 | 位置 | 影子接入 | 翻主判据 | 删码时点 |
| --- | --- | --- | --- | --- |
| ① 法官问卷 | `scribe3/playbook/judge.py` | **已退役**（消费方只读 gate；关旗走旧 verdict） | 问卷文本若改必须升 playbook 版 | 关旗回退仍可用 |
| ② post_check 检测器族 | `scribe3/api/routers/write.py` `post_check` | **已退役**（聚合出口 gate；作者面板仍只认 issues 人话） | 不把 gate.ok 当创作放行 | 检测器可留 |
| ③ review evaluator | `scribe3/review/runner.py` | **已退役**（消费方优先 gate.hits；issues 人话兼容一版） | 与 post_check 形状一致 | 下一轮可只留 gate |
| ④ quality evaluator | `scribe3/quality/` | **已退役**（gate 为主；dimensions 兼容一版） | 下一轮删旧字段 | 兼容期，不是观察期 |
