-- 070_material_memory.surql · 素材=主编的联想记忆:三模态(向量/全文/图)+ 溯源
-- 全文索引: SurrealDB 3.x 用 FULLTEXT ANALYZER。
-- material 表沿用 055/060;此处 OVERWRITE/IF NOT EXISTS 加记忆化字段与索引,现有数据零丢失。
DEFINE FIELD IF NOT EXISTS ref_tags         ON material TYPE array<string> DEFAULT [];  -- 参考维度(自由标签)
DEFINE FIELD IF NOT EXISTS embedding        ON material TYPE option<array<float>>;      -- 512维语义向量
DEFINE FIELD IF NOT EXISTS tokens           ON material TYPE option<string>;            -- jieba 切词(全文 BM25)
DEFINE FIELD IF NOT EXISTS about_entities   ON material TYPE array<string> DEFAULT [];  -- 提及实体 id(图召回)
DEFINE FIELD IF NOT EXISTS pinned           ON material TYPE bool DEFAULT false;        -- 核心记忆
DEFINE FIELD IF NOT EXISTS archived         ON material TYPE bool DEFAULT false;        -- 归档(不召回)
DEFINE FIELD IF NOT EXISTS recall_count     ON material TYPE int DEFAULT 0;             -- 参考次数(强度)
DEFINE FIELD IF NOT EXISTS last_recalled_at ON material TYPE option<datetime>;          -- 最近参考(衰减)

DEFINE INDEX IF NOT EXISTS material_embedding ON material FIELDS embedding HNSW DIMENSION 512 DIST COSINE;
DEFINE ANALYZER OVERWRITE material_zh TOKENIZERS blank FILTERS lowercase;
DEFINE INDEX IF NOT EXISTS material_fts ON material FIELDS tokens FULLTEXT ANALYZER material_zh BM25;

-- 双向溯源:素材↔章(到章,无段落锚)
DEFINE TABLE IF NOT EXISTS material_reference SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS material_id ON material_reference TYPE string;
DEFINE FIELD IF NOT EXISTS chapter     ON material_reference TYPE int;
DEFINE FIELD IF NOT EXISTS dimension   ON material_reference TYPE option<string>;
DEFINE FIELD IF NOT EXISTS reason      ON material_reference TYPE option<string>;
DEFINE FIELD IF NOT EXISTS via         ON material_reference TYPE string DEFAULT 'manual';
DEFINE FIELD IF NOT EXISTS created_at  ON material_reference TYPE datetime VALUE time::now() READONLY;
DEFINE INDEX IF NOT EXISTS matref_by_material ON material_reference FIELDS material_id;
DEFINE INDEX IF NOT EXISTS matref_by_chapter  ON material_reference FIELDS chapter;
