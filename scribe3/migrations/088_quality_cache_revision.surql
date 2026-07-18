-- 质量派生缓存版本:正文保存、事件回写或检测器规则变更后，面板可以识别旧缓存。
-- 不自动全书重算，避免启动时拉取百万字正文；作者在质量仪表盘可显式刷新。
DEFINE FIELD IF NOT EXISTS qc_cache_revision ON chapter TYPE option<int>;
