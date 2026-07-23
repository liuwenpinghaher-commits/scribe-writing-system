-- 095 · 素材共享字段 + 导入任务持久化
-- summary: 手法摘要(召回注入优先)
-- origin: 创建来源(manual/import/session_clip/chief),仅创建时写入
-- material_import_job: 导入流水线跨重启/worker 的 job 态(bound to work DB)

DEFINE FIELD IF NOT EXISTS summary ON material TYPE option<string>;
DEFINE FIELD IF NOT EXISTS origin  ON material TYPE option<string> DEFAULT 'manual'
    ASSERT $value = NONE OR $value IN ['manual', 'import', 'session_clip', 'chief'];

DEFINE TABLE IF NOT EXISTS material_import_job SCHEMALESS;
DEFINE FIELD IF NOT EXISTS job_id     ON material_import_job TYPE string;
DEFINE FIELD IF NOT EXISTS work       ON material_import_job TYPE string;
DEFINE FIELD IF NOT EXISTS stage      ON material_import_job TYPE option<string>;
DEFINE FIELD IF NOT EXISTS done       ON material_import_job TYPE bool DEFAULT false;
DEFINE FIELD IF NOT EXISTS total      ON material_import_job TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS items      ON material_import_job TYPE option<array>;
DEFINE FIELD IF NOT EXISTS error      ON material_import_job TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source     ON material_import_job TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON material_import_job TYPE datetime VALUE time::now() READONLY;
DEFINE FIELD IF NOT EXISTS updated_at ON material_import_job TYPE datetime VALUE time::now();
DEFINE INDEX IF NOT EXISTS matimp_by_job ON material_import_job FIELDS job_id UNIQUE;
