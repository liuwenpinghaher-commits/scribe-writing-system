-- 招式库卡身 / 旧用（计划存在 chapter.beats_meta.story_move_plan）
DEFINE TABLE IF NOT EXISTS story_move SCHEMALESS;
DEFINE TABLE IF NOT EXISTS story_move_use SCHEMALESS;
DEFINE FIELD IF NOT EXISTS slug ON story_move TYPE option<string>;
DEFINE FIELD IF NOT EXISTS status ON story_move TYPE option<string>;
DEFINE FIELD IF NOT EXISTS origin ON story_move TYPE option<string>;
DEFINE FIELD IF NOT EXISTS formula_family ON story_move TYPE option<string>;
DEFINE FIELD IF NOT EXISTS name ON story_move TYPE option<string>;
DEFINE INDEX IF NOT EXISTS uniq_story_move_slug ON story_move FIELDS slug UNIQUE;
