-- scribe3 · 011_indexes.surql · 性能索引(枢纽 E §3.1)
-- 全部 IF NOT EXISTS:与现有迁移一致,启动可重复 apply 幂等。
-- 仅补常规字段索引;HNSW 向量索引已在 003_vector.surql,不重复。

-- (1) 命题时间门:facts_at 的 valid_from<=ch AND (valid_to=NONE OR valid_to>ch)
-- Note: composite index on valid_from,valid_to skips rows with valid_to=NONE in SurrealDB 3.x.
-- Use single-column index on valid_from only; valid_to filter happens in memory.
DEFINE INDEX IF NOT EXISTS idx_prop_valid   ON proposition FIELDS valid_from;

-- (2) 命题主体反查:proposition.entity 等值(graph/限知按主体聚合)
DEFINE INDEX IF NOT EXISTS idx_prop_entity  ON proposition FIELDS entity;

-- (3) 知识边时间门:knowledge / project_frame 按 since_chapter 过滤
DEFINE INDEX IF NOT EXISTS idx_knows_since   ON knows FIELDS since_chapter;

-- (4) reader 帧时间门:reader_knows.since_chapter
DEFINE INDEX IF NOT EXISTS idx_rknows_since  ON reader_knows FIELDS since_chapter;

-- (5) 事件时间门:events_at 的 valid_from = $ch + max_chapter ORDER BY
DEFINE INDEX IF NOT EXISTS idx_event_chapter ON event FIELDS valid_from;

-- (6) 声音库:latest_voice_samples 的 character 等值 + since_chapter 排序
DEFINE INDEX IF NOT EXISTS idx_voice_char    ON voice_sample FIELDS character, since_chapter;

-- (7) 声音进化标记:list_voice_flags 按 status 过滤
DEFINE INDEX IF NOT EXISTS idx_vflag_status  ON voice_evolution_flag FIELDS status;

-- (8) 伏笔状态:open_promises WHERE status='open'
DEFINE INDEX IF NOT EXISTS idx_promise_status ON promise FIELDS status;

-- (9) 章节唯一:防重复章(UPSERT 用 record id=seq,但 seq 字段本身可重复写)
-- DEFINE INDEX IF NOT EXISTS idx_chapter_seq   ON chapter FIELDS seq UNIQUE;

-- (10) 母题去重:重复 ingest 防重
-- DEFINE INDEX IF NOT EXISTS idx_motif_name    ON motif FIELDS name UNIQUE;
