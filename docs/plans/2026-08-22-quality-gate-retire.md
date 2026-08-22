# 旧判定四套退役表

QualityGate 现在是统一出口形状。旧四套先影子接入，再翻主，最后删码。

| 套 | 位置 | 影子接入 | 翻主判据 | 删码时点 |
| --- | --- | --- | --- | --- |
| ① 法官问卷 | `scribe3/playbook/judge.py` | **已接**（`judge()` 写 `ok/code/message/hits`，仍保留 `verdict`） | 连续对照形状稳定、问卷文本若改必须升 playbook 版 | 翻主后一版、无任何调用 `verdict` 以外的旧字段 |
| ② post_check 检测器族 | `scribe3/api/routers/write.py` `post_check` | **已接**（响应带 `gate`） | 作者面板仍只认 issues 人话，不把 gate.ok 当创作放行 | 检测器仍可留；聚合出口只留 QualityGate |
| ③ review evaluator | `scribe3/review/runner.py` | **已接**（`run_chapter_review` 写 `gate`，旧 `issues` 仍在） | 与 post_check 对照一致后再翻 | 翻主下一轮 |
| ④ quality evaluator | `scribe3/quality/` | **已接**（`_shape_evaluation` 加 `gate`，旧 dimensions 不变） | 与作者面板对照后再翻 | 翻主下一轮 |
