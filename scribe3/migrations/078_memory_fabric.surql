-- 078_memory_fabric.surql · 统一记忆底座(Task 8):经验性记忆 + 联想边 + 工作摘要
-- ⚠ 只存【经验性】记忆(working/episodic/procedural/reference/uncertainty);
--   正典事实不复制进 memory_item——canonical 候选一律来自现有领域表(proposition/promise 等)。
-- 三时态:valid_from/to = 故事内时间(章),known_from/to = 读者/发现时间(章)。
-- SurrealDB 3.x: 全文用 FULLTEXT ANALYZER；HNSW DIMENSION 512 DIST COSINE。
DEFINE TABLE IF NOT EXISTS memory_item SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS work ON memory_item TYPE string;
DEFINE FIELD IF NOT EXISTS scope_type ON memory_item TYPE string ASSERT $value IN ['work', 'thread', 'chapter', 'user_global'];
DEFINE FIELD IF NOT EXISTS scope_id ON memory_item TYPE string;
DEFINE FIELD IF NOT EXISTS kind ON memory_item TYPE string ASSERT $value IN ['working', 'episodic', 'procedural', 'reference', 'uncertainty'];
DEFINE FIELD IF NOT EXISTS text ON memory_item TYPE string;
DEFINE FIELD IF NOT EXISTS summary ON memory_item TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS condition ON memory_item TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_type ON memory_item TYPE string;
DEFINE FIELD IF NOT EXISTS source_id ON memory_item TYPE string;
DEFINE FIELD IF NOT EXISTS source_revision ON memory_item TYPE option<string>;
DEFINE FIELD IF NOT EXISTS status ON memory_item TYPE string ASSERT $value IN ['active', 'superseded', 'invalid'];
DEFINE FIELD IF NOT EXISTS confidence ON memory_item TYPE float ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD IF NOT EXISTS importance ON memory_item TYPE int ASSERT $value >= 0 AND $value <= 5;
DEFINE FIELD IF NOT EXISTS pinned ON memory_item TYPE bool DEFAULT false;
DEFINE FIELD IF NOT EXISTS supersedes ON memory_item TYPE option<record<memory_item>>;
DEFINE FIELD IF NOT EXISTS observed_at ON memory_item TYPE datetime;
DEFINE FIELD IF NOT EXISTS valid_from ON memory_item TYPE option<int>;
DEFINE FIELD IF NOT EXISTS valid_to ON memory_item TYPE option<int>;
DEFINE FIELD IF NOT EXISTS known_from ON memory_item TYPE option<int>;
DEFINE FIELD IF NOT EXISTS known_to ON memory_item TYPE option<int>;
DEFINE FIELD IF NOT EXISTS tokens ON memory_item TYPE string;
DEFINE FIELD IF NOT EXISTS embedding ON memory_item TYPE option<array<float>>;
DEFINE FIELD IF NOT EXISTS recall_count ON memory_item TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS last_recalled_at ON memory_item TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS created_at ON memory_item TYPE datetime VALUE time::now() READONLY;
DEFINE FIELD IF NOT EXISTS updated_at ON memory_item TYPE datetime;
DEFINE INDEX IF NOT EXISTS memory_scope_kind_idx ON memory_item FIELDS work, scope_type, scope_id, kind, status;
DEFINE INDEX IF NOT EXISTS memory_source_idx ON memory_item FIELDS work, source_type, source_id;
DEFINE INDEX IF NOT EXISTS memory_embedding_idx ON memory_item FIELDS embedding HNSW DIMENSION 512 DIST COSINE;
DEFINE ANALYZER OVERWRITE memory_zh TOKENIZERS blank FILTERS lowercase;
DEFINE INDEX IF NOT EXISTS memory_fts_idx ON memory_item FIELDS tokens FULLTEXT ANALYZER memory_zh BM25;

DEFINE TABLE IF NOT EXISTS memory_relation TYPE RELATION IN memory_item OUT memory_item SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS relation ON memory_relation TYPE string ASSERT $value IN ['supports', 'contradicts', 'derived_from', 'same_topic', 'caused_by', 'corrects'];
DEFINE FIELD IF NOT EXISTS weight ON memory_relation TYPE float DEFAULT 1.0;
DEFINE FIELD IF NOT EXISTS provenance ON memory_relation TYPE object DEFAULT {};
DEFINE FIELD IF NOT EXISTS provenance.* ON memory_relation TYPE any;
DEFINE INDEX IF NOT EXISTS memory_relation_kind_idx ON memory_relation FIELDS relation;

DEFINE TABLE IF NOT EXISTS working_summary SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS work ON working_summary TYPE string;
DEFINE FIELD IF NOT EXISTS thread_id ON working_summary TYPE string;
DEFINE FIELD IF NOT EXISTS through_turn ON working_summary TYPE int;
DEFINE FIELD IF NOT EXISTS goals ON working_summary TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS open_tasks ON working_summary TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS decisions ON working_summary TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS assumptions ON working_summary TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS summary ON working_summary TYPE string;
DEFINE FIELD IF NOT EXISTS updated_at ON working_summary TYPE datetime;
DEFINE INDEX IF NOT EXISTS working_summary_thread_idx ON working_summary FIELDS work, thread_id UNIQUE;
