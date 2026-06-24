-- scribe3 · 012_ingest_provenance.surql · ingest 章级幂等(C枢纽 P07)
-- 产出归属:proposition/knows 记录由第几章 ingest 产生(作者直编/种子为 NONE)。

-- ingest 归属字段(NONE=非 ingest 产出)
DEFINE FIELD IF NOT EXISTS ingest_seq ON proposition TYPE option<int>;
DEFINE FIELD IF NOT EXISTS ingest_seq ON knows TYPE option<int>;

-- 清理热路径索引:按 ingest_seq 反查
DEFINE INDEX IF NOT EXISTS idx_prop_ingest  ON proposition FIELDS ingest_seq;
DEFINE INDEX IF NOT EXISTS idx_knows_ingest ON knows FIELDS ingest_seq;

-- 待确认表:LLM 抽出的库外角色/名字(P18)
DEFINE TABLE IF NOT EXISTS ingest_unverified SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name   ON ingest_unverified TYPE string ASSERT string::len($value) > 0;
DEFINE FIELD IF NOT EXISTS seq    ON ingest_unverified TYPE int;
DEFINE FIELD IF NOT EXISTS role   ON ingest_unverified TYPE string;
DEFINE FIELD IF NOT EXISTS status ON ingest_unverified TYPE string DEFAULT 'pending';
