-- GAP-16: 独立 storyline 实体表（可编辑）
DEFINE TABLE IF NOT EXISTS storyline SCHEMALESS;
DEFINE FIELD IF NOT EXISTS title ON storyline TYPE option<string>;
DEFINE FIELD IF NOT EXISTS arc_kind ON storyline TYPE option<string>;
DEFINE FIELD IF NOT EXISTS chapter_seqs ON storyline TYPE option<array>;
DEFINE FIELD IF NOT EXISTS notes ON storyline TYPE option<string>;
DEFINE FIELD IF NOT EXISTS updated_at ON storyline TYPE option<datetime>;
DEFINE INDEX IF NOT EXISTS storyline_title ON storyline FIELDS title;
