# book_79c0d45e 第 6–10 章运行日志盘点

数据源：demo `tonglu.example.com` 只读（2026-08-14）。  
对照：1–5 章盘点 `docs/evidence/v634-true-chat-20260814/14-log-inventory.md`（本轮主集不是 1–5）。

**诚实：141 `pipeline_log` 已通，但仍回放不了装段读值 / 谓词 / 裁剪正文。不是飞行记录仪。**

| # | 类别 | 本轮 6–10 | 能答 | 不能答 |
|---|------|-----------|------|--------|
| 1 | 书 | `book_79c0d45e` 10 章壳；6–10 有正文 | 本轮新写规模 | 哪一次 write 的哪一段被拼进定稿 |
| 2 | 章 GET | 五章 prose 非空、GATE-B 齐、无 `fallback` | 读者看见什么 | 续写拼接缝 |
| 3 | write 链 | 每章 ≥1 条 `status=ok` | 戏剧/大纲已注入、llm 耗时 | 读了哪些字段值 |
| 4 | save 链 | 每章先 409 定稿门 blocked，再 skip 绿 | headline「定稿门跳过」 | skip 仍可能对照假绿（`actual=present`，修前） |
| 5 | `pipeline_log` | `GET /debug/pipeline-logs` **200** | 步名、start/end、`emit.shape` | `read.source` / `pred.eval` / 丢段正文 / 血缘 |
| 6 | 链 `log_count` | **null** | — | 列表无法标旧账 |
| 7 | 142 工件 | **无** | — | 余烬原文、L2 丢段、编译段 |

## 每章代表链

| 章 | write `trace_id` | save 失败 | save skip |
|----|------------------|-----------|-----------|
| 6 | `e619b319419a41bba445414808d63fb9` | `541810ed0b374afe92cf272b7bb6fed1` | `5870b5066ccd42288c0a9fae170209d9` |
| 7 | `b03a7ee047454ecabb9c9b1b5547b35a` | `4ffbfbb1d0c34ec484104c28bd906855` | `790769f8d308449d95c78776e170ed59` |
| 8 | `0ad80f631642462d805c6e687fa81e11` | `08cdd1d58e6e4dd38a8e1b84e136222d` | `698879310a424e47b7874a85ae219e6b` |
| 9 | `be363f7d83204abdb46211711a2b0267` | `48f209467a3c41ca8c88ebaf8c2c7539` | `696e1cd262bf4ac2b7fd2b81f2db92af` |
| 10 | `d11121016aa748ca868f1853738470ac` | `2a44276a7d9940f7b37d4f183b572dbc` | `2a497169a3f84e8c8de083fc8e8581cd` |

写链 headline 一律「工艺（injected）·本章目的（injected）·必须发生（injected）·模型 succeeded」——R5/R6 已不再空合同。  
对照仍红：`craft` / `purpose` / `brief_must` / `deduction_final` / `storyline_polish` / `discourse_soft`（期望 `no_*` 却 injected）。

写链 logs 样例（ch6 write，50 条上限截断）：几乎全是 `step.start` / `step.end` / `emit.shape`。无 `read.source`。

save skip 的 `save.finalize_gate`：`actual_reason=skipped_by_flag`，修前 `actual=present` `verdict=green`。

## 观测缺口（不得假装已有 142）

1. 逐步日志不能回放「读了 end_hook 原文 / 丢掉哪段 / 编译段进模型」。  
2. 链上 `log_count` 未打穿列表。  
3. 对照期望与注入器不是同一套事实。  
4. 存稿跳过 QC 在 headline 已诚实，对照行仍可假绿（本轮修）。
