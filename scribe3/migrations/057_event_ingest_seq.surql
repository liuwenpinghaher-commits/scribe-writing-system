-- scribe3 · 057_event_ingest_seq.surql · event 加 ingest_seq 字段(批D P1-5 事件抽取)
-- 供 purge_ingest 幂等清理:重跑同一章 ingest 前先删该章 ingest 产出的 event + 图边
-- (involves/causes/causal),再重抽落库,重复 ingest 不残留悬挂事件/边。
-- 手动种 / MCP s3_add_event 的事件 ingest_seq=NONE,不受 purge 影响(向后兼容)。
DEFINE FIELD IF NOT EXISTS ingest_seq ON event TYPE option<int>;
DEFINE INDEX IF NOT EXISTS idx_event_ingest ON event FIELDS ingest_seq;
