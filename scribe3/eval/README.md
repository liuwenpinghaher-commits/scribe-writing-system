# craft-eval 尺子数据

本目录是 [`docs/plans/2026-08-26-craft-ruler-loop.md`](../../docs/plans/2026-08-26-craft-ruler-loop.md) 的评测真源。

- `holdout.json`：**冻结**。种子 `20260826`，43 章留出。禁止改章号。每轮开工校验 `holdout.sha256`。
- `chapters.json`：214 节在现存母本上的行界。`r1_skip_reason` 非空的节不进 R1。
- `citation_spotcheck.json`：20 条拆文书证能否在母本搜到（行号已整体偏移，只认句子）。
- `extract_card.py`：给一节原文出 21 段卡。禁止读留出章 gold。few-shot 只从 dev 抽。
- `card_schema.py`：21 个段题。

母本因版权不入库（见根 `.gitignore`）。本机没有全文时，先把 txt 拷到该路径再跑脚本。
