-- PR-1 fix: independent ingest_lease table for cross-process CAS (CREATE ONLY / UPDATE WHERE)
DEFINE TABLE IF NOT EXISTS ingest_lease SCHEMALESS;
DEFINE FIELD IF NOT EXISTS work ON ingest_lease TYPE option<string>;
DEFINE FIELD IF NOT EXISTS seq ON ingest_lease TYPE option<int>;
DEFINE FIELD IF NOT EXISTS owner ON ingest_lease TYPE option<string>;
DEFINE FIELD IF NOT EXISTS until ON ingest_lease TYPE option<float>;
DEFINE FIELD IF NOT EXISTS state ON ingest_lease TYPE option<string>;
DEFINE FIELD IF NOT EXISTS heartbeat_at ON ingest_lease TYPE option<float>;
-- id is deterministic: work + "_" + seq (see lease_record_id)
