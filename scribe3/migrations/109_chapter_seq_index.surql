-- 109: chapter.seq 索引（列表 ORDER BY seq / LIMIT 热路径）
-- 80 章实测 p50≈5ms 仍可接受；千章级前先落索引，空库/新作品零成本。
DEFINE INDEX IF NOT EXISTS idx_chapter_seq ON chapter FIELDS seq;
