-- scribe3 · 语义 RAG:proposition 向量 + HNSW 索引(语义召回设定/命题)。
-- 512 维 = bge-small-zh-v1.5;COSINE 距离。单库多模:向量召回可同句 JOIN 图谱。
DEFINE FIELD IF NOT EXISTS embedding ON proposition TYPE option<array<float>>;
DEFINE INDEX IF NOT EXISTS idx_prop_vec ON proposition FIELDS embedding HNSW DIMENSION 512 DIST COSINE;
