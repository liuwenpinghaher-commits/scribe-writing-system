-- scribe3 · 042_char_state_ingest_seq.surql · char_state 加 ingest_seq 字段(G4 自动弧光抽取)
-- 供 purge_ingest 幂等清理:重跑同一章 ingest 前先 DELETE char_state WHERE ingest_seq=$seq。
-- 手动种的 char_state ingest_seq=NONE,不受 purge 影响(向后兼容)。
-- 同时补充 before_state / after_state 可选字段(若 028 SCHEMALESS 已允许写入则此行为 no-op)。
DEFINE FIELD IF NOT EXISTS ingest_seq ON char_state TYPE option<int>;
DEFINE FIELD IF NOT EXISTS before_state ON char_state TYPE option<object>;
DEFINE FIELD IF NOT EXISTS after_state ON char_state TYPE option<object>;
