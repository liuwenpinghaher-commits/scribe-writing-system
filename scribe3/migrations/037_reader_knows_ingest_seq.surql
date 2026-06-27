-- scribe3 · reader_knows 增加 ingest_seq 字段(P2-E1)。
-- 供 purge_ingest 幂等清理:重跑同一章 ingest 前先 DELETE reader_knows WHERE ingest_seq=$seq。
-- 手动种的 reader_knows 边 ingest_seq=NONE,不受 purge 影响(向后兼容)。
DEFINE FIELD IF NOT EXISTS ingest_seq ON reader_knows TYPE option<int>;
