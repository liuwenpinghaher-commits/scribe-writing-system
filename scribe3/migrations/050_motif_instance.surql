-- scribe3 · 050_motif_instance.surql · 母题章实例(本章触及哪些母题 + 证据引文)
-- 新表 SCHEMAFULL,ingest 抽取落库;purge_ingest 幂等清除。
DEFINE TABLE IF NOT EXISTS motif_instance SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS motif_id ON motif_instance TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON motif_instance TYPE int;
DEFINE FIELD IF NOT EXISTS evidence ON motif_instance TYPE option<string>;
DEFINE FIELD IF NOT EXISTS ingest_seq ON motif_instance TYPE option<int>;
