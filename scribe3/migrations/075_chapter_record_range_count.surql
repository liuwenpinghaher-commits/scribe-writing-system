-- scribe3 · 075_chapter_record_range_count.surql · 章节计数快路
-- SurrealDB 2.1.x 不支持 `DEFINE INDEX ... COUNT`（Parse error）。
-- 章节计数改走 SELECT count() / 应用层 stats()；本迁移仅作幂等占位，避免 apply_schema 卡死。
-- （历史 3.x 目标语法保留在 git 历史；2.1 生产栈以本文件为准。）
DEFINE FIELD IF NOT EXISTS _schema_075_count_path ON chapter TYPE option<string>;
