-- scribe3 · 046_narrative_position.surql · 时间线完整期:故事/叙事双轴
-- 给 event 加可空的 narrative_position(叙事位):事件在"故事讲述顺序"中的位置,
-- 独立于 story_chapter(故事编年/实际发生章)。
--   null  = 与 story_chapter 同序(线性叙事,向后兼容,现有读路径一行不改即继续工作)
--   非 null = 倒叙/闪回/插叙的独立叙事坐标(故事时间早、叙事位置晚)
-- 对应 Aeon Timeline 的 Narrative Order(spec §3.1)。
-- 不回填:留 null = 回退 story_chapter。幂等:IF NOT EXISTS 保证重跑安全。

DEFINE FIELD IF NOT EXISTS narrative_position ON event TYPE option<int>;
DEFINE INDEX IF NOT EXISTS idx_event_narrative_pos ON event FIELDS narrative_position;
