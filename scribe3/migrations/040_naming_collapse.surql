-- scribe3 · 040_naming_collapse.surql · P3-e2: 命名漂移收口
-- 退场方列只在此删除;真源列继续存在。
-- 每行只在对应 readers 迁移完毕、测试绿灯后才加入。

-- 1. voice_evolution_flag.seq → trigger_chapter
--    读者:list_voice_flags 已改读 trigger_chapter;add_voice_flag 已停写 seq。
REMOVE FIELD IF EXISTS seq ON voice_evolution_flag;

-- 2. event.etype → event_type
--    读者:events_at / graph_recall 已改读 event_type;add_event 已停写 etype。
REMOVE FIELD IF EXISTS etype ON event;

-- 3. proposition.entity → entity_id
--    读者:_keyword_search / facts_at / fact() / semantic_recall / graph_recall 均已改读 entity_id;
--    add_fact 已停写 entity。
REMOVE FIELD IF EXISTS entity ON proposition;

-- 4. event.valid_from → story_chapter
--    读者:max_chapter / events_at 均已改读 story_chapter;add_event 已停写 valid_from。
--    注意:proposition.valid_from 是完全不同的字段(命题时间门),此处不动。
REMOVE FIELD IF EXISTS valid_from ON event;
