-- 兼容期结束：ingest_message 已全覆盖，删除旧列 ingest_error。
REMOVE FIELD IF EXISTS ingest_error ON chapter;
