# 摘要收编清单

摘要只走 `codex_digest`（一条不超过 200 字，名字/性别/秘密标记还在）。

| 处 | 状态 |
| --- | --- |
| `scribe3/codex_digest.py` `sync_entity_digests` | 底座 |
| `scribe3/api/routers/codex.py` 实体写入后同步 | 已接 |
| `scribe3/tools/codex_digest_backfill.py` | 已接 |
| `scribe3/api/services/prompt_blocks.py` `_pulse_digest` | 章脉搏，不是实体摘要，不迁 |
| `scribe3/api/routers/chat_threads.py` `maintenance_daily_digest` | 日摘要，不是实体摘要，不迁 |
| `scribe3/memory_gain.py` usage digest | 用量，不是实体摘要，不迁 |
