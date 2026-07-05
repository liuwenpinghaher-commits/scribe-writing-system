-- scribe3 · 065_lesson.surql · 复盘蒸馏 lesson 表(北极星方案任务8,蓝图 §4-② 沉淀环第2-3级)
-- 工作方法归复盘(lesson),世界状态归本体(ingest)——严格分家(蓝图两条铁律)。
-- 独立表+专属 HNSW 索引(台账/底座对表 Q4:分表分索引,无 pre-filtered HNSW,
-- 与情绪模式向量物理隔离,零 KNN×WHERE 组合坑);512 维 bge-small-zh(003 先例)。
-- importance:ExpeL 计数器(初始2/重复+1/否定-1,归零退役);invalid_at:失效标记不物理删(Zep)。
DEFINE TABLE IF NOT EXISTS lesson SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS chapter ON lesson TYPE int;
DEFINE FIELD IF NOT EXISTS kind ON lesson TYPE string ASSERT $value IN ['decision', 'correction', 'pitfall'];
DEFINE FIELD IF NOT EXISTS text ON lesson TYPE string;
DEFINE FIELD IF NOT EXISTS condition ON lesson TYPE option<string>;
DEFINE FIELD IF NOT EXISTS evidence_turns ON lesson TYPE option<string>;
DEFINE FIELD IF NOT EXISTS importance ON lesson TYPE int DEFAULT 2;
DEFINE FIELD IF NOT EXISTS uses ON lesson TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS invalid_at ON lesson TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS created_at ON lesson TYPE datetime;
DEFINE FIELD IF NOT EXISTS embedding ON lesson TYPE option<array<float>>;
DEFINE INDEX IF NOT EXISTS idx_lesson_vec ON lesson FIELDS embedding HNSW DIMENSION 512 DIST COSINE;
