-- scribe3 · 016_chapter_vector.surql · 章节级 RAG(E枢纽 §3.5)
-- chapter.prose 向量化,与 proposition 同维同距(512 / COSINE = bge-small-zh-v1.5)。

DEFINE FIELD IF NOT EXISTS embedding ON chapter TYPE option<array<float>>;
DEFINE INDEX IF NOT EXISTS idx_chapter_vec ON chapter
    FIELDS embedding HNSW DIMENSION 512 DIST COSINE;
