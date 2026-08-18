# playbook.1

共用版本号：`PLAYBOOK_VERSION = "playbook.1"`。

改任何 prompt / rubric / schema 必须升到 playbook.2，并另写本文对应副本。已有产物按其落库时的版本验收，不追溯重考。

## 身份

- 生成器：见 `scribe3/playbook/prompts.py` `IDENTITY_NOVELIST`
- 责任卡：`IDENTITY_DUTY`
- 抽取：`IDENTITY_SCRIBE`
- 法官：`IDENTITY_JUDGE`

## 调用参数

- 法官 / Contract 抽取：temperature `0`
- 生成器：temperature `0.8`

## 五层

duty → design（写戏 + 抽契约）→ deduce → draft → final

每层：生成 → 一个 LLM 法官 → 结构闸。单层质量重试 ≤5 → `needs_human`。

## 纯函数允许清单

见 `scribe3/playbook/structural.py` 与 `quote.py`。禁止 ngram / 词表 / 相似度。
