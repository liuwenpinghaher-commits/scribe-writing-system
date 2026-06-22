-- scribe3 · 伏笔/promise(被开启、须闭合的张力;戏剧层)。
-- setup_chapter 埋下 → payoff_chapter 回收;open 着超过 N 章未收=超期(体检告警,护城河)。
DEFINE TABLE IF NOT EXISTS promise SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS text           ON promise TYPE string;
DEFINE FIELD IF NOT EXISTS setup_chapter  ON promise TYPE int;
DEFINE FIELD IF NOT EXISTS payoff_chapter ON promise TYPE option<int>;     -- null=未回收
DEFINE FIELD IF NOT EXISTS status         ON promise TYPE string DEFAULT 'open';   -- open/closed
DEFINE FIELD IF NOT EXISTS kind           ON promise TYPE string DEFAULT 'promise'; -- promise/red_herring
