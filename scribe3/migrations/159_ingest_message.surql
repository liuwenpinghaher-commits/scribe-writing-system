-- 成功/失败共用中性字段；ingest_error 留一版兼容读。
DEFINE FIELD IF NOT EXISTS ingest_message ON chapter TYPE option<string>;
UPDATE chapter SET ingest_message = ingest_error WHERE ingest_message IS NONE AND ingest_error IS NOT NONE;
