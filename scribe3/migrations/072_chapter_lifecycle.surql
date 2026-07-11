-- scribe3 · 072_chapter_lifecycle.surql · 章节生命周期
-- chapter 是 SCHEMAFULL,归档/删除闭环所需字段必须显式定义。

DEFINE FIELD IF NOT EXISTS archived ON chapter TYPE bool DEFAULT false;
DEFINE FIELD IF NOT EXISTS archived_at ON chapter TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS archive_reason ON chapter TYPE option<string>;
