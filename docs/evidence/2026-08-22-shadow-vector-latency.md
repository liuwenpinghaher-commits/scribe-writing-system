# 向量对照延迟（N06）

日期：2026-08-22  
环境：Grok 运行机（约 1.6Gi、无生产负载）。**未测**带 embedding 的写章首字增量——会把这台机器拖死。数字不当创作放行判据。

裁决：**A 异步**。`SCRIBE3_RECALL_SHADOW_VECTOR` 默认仍开，对照另开线程，写章路径不等待。需要同步结果时设 `SCRIBE3_RECALL_SHADOW_VECTOR_SYNC=1`（单测）。

对照：`docs/adr/2026-08-22-shadow-vector-async.md`。
