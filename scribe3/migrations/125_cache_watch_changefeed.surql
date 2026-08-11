-- S-2 完成：旁路 cache_watch 表（新建 SCHEMALESS + CHANGEFEED）
-- 不改 proposition 等 SCHEMAFULL 表定义，避免 apply_schema 失败。
-- emit_invalidation 双写本表；ChangefeedCacheWorker 轮询 SHOW CHANGES。
DEFINE TABLE IF NOT EXISTS cache_watch SCHEMALESS CHANGEFEED 1h;
DEFINE FIELD IF NOT EXISTS table_name ON cache_watch TYPE option<string>;
DEFINE FIELD IF NOT EXISTS work ON cache_watch TYPE option<string>;
DEFINE FIELD IF NOT EXISTS at ON cache_watch TYPE option<datetime> VALUE time::now() READONLY;
