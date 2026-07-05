-- 断头修复批(审计 P1-6 / C-2):
-- ① chapter.ingest_status/ingest_error —— 后台 ingest 结果对前端可见(失败不再静默)
-- ② voice_evolution_flag.ingest_seq —— ingest 路径产的 flag 随 purge 幂等清理
DEFINE FIELD IF NOT EXISTS ingest_status ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS ingest_error ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS ingest_seq ON voice_evolution_flag TYPE option<int>;
