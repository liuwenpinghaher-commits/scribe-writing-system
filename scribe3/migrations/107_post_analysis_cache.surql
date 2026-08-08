-- 章后统一分析缓存：跨进程/重启复用 knowledge+settings（按 prose 指纹校验）
DEFINE FIELD IF NOT EXISTS post_analysis_cache ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS post_analysis_fp ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS post_analysis_at ON chapter TYPE option<datetime>;
