# 摘要收编 · 裁决闭环凭证

日期：2026-08-22  
状态：**已统一（裁决闭环）**  
监控：触发条件（消费方开始把「人/物/规则」当设定条目召回则重启评估）。2026-09-05 前无触发则记「无触发」。不是观察期。

摘要底座只走 `codex_digest`（一条不超过 200 字，名字/性别/秘密标记还在）。下面三处**不迁**进统一召回中枢：它们不是实体摘要，和「找这本书里对得上的设定」不是一件事。

| 处 | 理由 | 触发再评估 |
| --- | --- | --- |
| `scribe3/api/services/prompt_blocks.py` `_pulse_digest` | 章脉搏：给作者看这一章写得怎样，不是设定条目 | 若改成把角色/世界条目摘要喂进写章嘱咐 |
| `scribe3/api/routers/chat_threads.py` `maintenance_daily_digest` | 日摘要：对话维护用，不是书里的人/物设定 | 若改成按实体消费、进召回槽 |
| `scribe3/memory_gain.py` usage digest | 用量：模型花了多少，不是故事事实 | 若改成故事事实摘要并进嘱咐 |

已接：

| 处 | 状态 |
| --- | --- |
| `scribe3/codex_digest.py` `sync_entity_digests` | 底座 |
| `scribe3/api/routers/codex.py` 实体写入后同步 | 已接 |
| `scribe3/tools/codex_digest_backfill.py` | 已接 |

触发条件（任一成立则重启迁移评估，不算本凭证自动失效）：digest 的消费方开始把「人/物/规则」当设定条目召回。
