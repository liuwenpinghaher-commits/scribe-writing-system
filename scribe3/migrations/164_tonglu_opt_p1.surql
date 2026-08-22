-- 铜炉最优化 2026-08-23：伏笔绑人 / 素材溯源类型 / 关系权重 / ingest 自愈点 / advisory 待确认
DEFINE FIELD IF NOT EXISTS involved_characters ON promise TYPE option<array<string>>;

DEFINE FIELD IF NOT EXISTS ref_kind ON material_reference TYPE option<string>;

DEFINE FIELD IF NOT EXISTS weight ON character_relation TYPE option<float>;

DEFINE TABLE IF NOT EXISTS ingest_checkpoint SCHEMALESS;
DEFINE FIELD IF NOT EXISTS seq ON ingest_checkpoint TYPE int;
DEFINE FIELD IF NOT EXISTS ok ON ingest_checkpoint TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS needs_replay ON ingest_checkpoint TYPE option<bool>;
DEFINE INDEX IF NOT EXISTS uniq_ingest_checkpoint_seq ON ingest_checkpoint FIELDS seq UNIQUE;

DEFINE TABLE IF NOT EXISTS advisory_pending SCHEMALESS;
DEFINE FIELD IF NOT EXISTS seq ON advisory_pending TYPE int;
DEFINE FIELD IF NOT EXISTS status ON advisory_pending TYPE option<string>;
