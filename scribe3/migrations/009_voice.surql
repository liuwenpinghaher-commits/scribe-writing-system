-- 声音库:每角色 4 类独白(自由/压力/关系/叙述),可版本化(同 character+kind 追加新 since_chapter)。
DEFINE TABLE IF NOT EXISTS voice_sample SCHEMALESS;
DEFINE FIELD IF NOT EXISTS character ON voice_sample TYPE string;
DEFINE FIELD IF NOT EXISTS kind ON voice_sample TYPE string;          -- free|pressure|relation|narration
DEFINE FIELD IF NOT EXISTS text ON voice_sample TYPE string;
DEFINE FIELD IF NOT EXISTS since_chapter ON voice_sample TYPE int;

-- 声音进化标记:ingest 检测重大事件 → 标记(只提示,不自动生成独白)。
DEFINE TABLE IF NOT EXISTS voice_evolution_flag SCHEMALESS;
DEFINE FIELD IF NOT EXISTS character ON voice_evolution_flag TYPE string;
DEFINE FIELD IF NOT EXISTS seq ON voice_evolution_flag TYPE int;
DEFINE FIELD IF NOT EXISTS reason ON voice_evolution_flag TYPE string;
DEFINE FIELD IF NOT EXISTS status ON voice_evolution_flag TYPE string;  -- open|done
