-- scribe3 · 032_chapter_version.surql · 命名存档点(改造④)
-- 作者命名的章稿里程碑;不存每次 AI 生成(去噪)。一书一 DB,故不含 work 字段。
DEFINE TABLE IF NOT EXISTS chapter_version SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq        ON chapter_version TYPE int;
DEFINE FIELD IF NOT EXISTS prose      ON chapter_version TYPE string;
DEFINE FIELD IF NOT EXISTS label      ON chapter_version TYPE string DEFAULT "";
DEFINE FIELD IF NOT EXISTS kind       ON chapter_version TYPE string DEFAULT "checkpoint";  -- checkpoint | final
DEFINE FIELD IF NOT EXISTS qc         ON chapter_version TYPE object DEFAULT {};
DEFINE FIELD IF NOT EXISTS created_at ON chapter_version TYPE datetime DEFAULT time::now();
DEFINE INDEX IF NOT EXISTS cv_seq ON chapter_version COLUMNS seq;
