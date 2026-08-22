# 召回中枢统一完成

日期：2026-08-22  
HEAD 实施时从 `0b001761` 起。

写章路：`SCRIBE3_RECALL_PLAYBOOK` 默认开。对话路：作者授意翻主（`0b001761` + ADR）。

残留旧路只作紧急回退，不是常规双轨：

- `_legacy_codex_recall`：关旗才走
- 对话 `legacy_named/legacy_cards`：关 `SCRIBE3_RECALL_DISCUSS` 或异常安全网
- except 兜底：降级安全网，非旧路

回退：关 `SCRIBE3_RECALL_PLAYBOOK`（写章）或 `SCRIBE3_RECALL_DISCUSS`（只退对话）。
