-- S-1: 混合搜索配置 — proposition 补 tokens + BM25，便于单程融合
-- 与 HNSW(003) 并存；写路径可回填 tokens（jieba 空格串）
DEFINE ANALYZER IF NOT EXISTS proposition_zh TOKENIZERS BLANK FILTERS LOWERCASE;
DEFINE FIELD IF NOT EXISTS tokens ON proposition TYPE option<string>;
DEFINE INDEX IF NOT EXISTS idx_prop_bm25 ON proposition FIELDS tokens FULLTEXT ANALYZER proposition_zh BM25;
