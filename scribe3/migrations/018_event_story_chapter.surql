-- scribe3 · 018_event_story_chapter.surql · D命名重构 N2 第一阶段
-- 新增 story_chapter 字段(与 valid_from 并存,双写阶段)。

DEFINE FIELD IF NOT EXISTS story_chapter ON event TYPE int;
DEFINE INDEX IF NOT EXISTS idx_event_story_chapter ON event FIELDS story_chapter;
