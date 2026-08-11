-- S-3: 跨进程 inflight 幂等锁（work+seq+op 唯一）
DEFINE TABLE IF NOT EXISTS inflight SCHEMALESS;
DEFINE FIELD IF NOT EXISTS work ON inflight TYPE option<string>;
DEFINE FIELD IF NOT EXISTS seq ON inflight TYPE option<int>;
DEFINE FIELD IF NOT EXISTS op ON inflight TYPE option<string>;
DEFINE FIELD IF NOT EXISTS started_at ON inflight TYPE option<datetime> VALUE time::now() READONLY;
DEFINE FIELD IF NOT EXISTS ttl_seconds ON inflight TYPE option<int> VALUE 300;
DEFINE INDEX IF NOT EXISTS idx_inflight_unique ON inflight FIELDS work, seq, op UNIQUE;
