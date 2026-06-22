-- scribe3 · reader 帧(读者已知,戏剧反讽的一极)。
-- reader 不是角色,不走 character->knows 边(保其类型安全);单独一张表,knower 隐含=reader。
-- 读者已知随章单调累积(since_chapter:第几章被叙述揭示)。
DEFINE TABLE IF NOT EXISTS reader_knows SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS proposition   ON reader_knows TYPE string;   -- proposition oid
DEFINE FIELD IF NOT EXISTS since_chapter ON reader_knows TYPE int;
