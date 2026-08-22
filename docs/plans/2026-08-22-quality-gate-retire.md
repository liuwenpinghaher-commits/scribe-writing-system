# 旧判定四套退役表

QualityGate 现在是统一出口形状。旧四套先影子接入，再翻主，最后删码。

| 套 | 位置 | 影子接入 | 翻主判据 | 删码时点 |
| --- | --- | --- | --- | --- |
| ① 法官问卷 | `scribe3/playbook/judge.py` | **已翻主**（消费方读 `gate`，`verdict` 留一版） | 问卷文本若改必须升 playbook 版 | 下一轮删 `verdict` 消费 |
| ② post_check 检测器族 | `scribe3/api/routers/write.py` `post_check` | **已翻主**（聚合出口 `gate`） | 作者面板仍只认 issues 人话，不把 gate.ok 当创作放行 | 检测器可留 |
| ③ review evaluator | `scribe3/review/runner.py` | **已翻主**（`gate` 与 issues 并存） | 与 post_check 形状一致 | 下一轮只留 gate |
| ④ quality evaluator | `scribe3/quality/` | **已翻主**（响应带 `gate`，dimensions 留一版给作者面板） | 下一轮实施即删旧字段 | 版本兼容节奏，不是观察期 |
