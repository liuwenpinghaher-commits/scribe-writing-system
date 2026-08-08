-- 终选/ingest L2 回写正文指纹：同指纹跳过二次 purge+apply
DEFINE FIELD IF NOT EXISTS ingest_prose_fp ON chapter TYPE option<string>;
