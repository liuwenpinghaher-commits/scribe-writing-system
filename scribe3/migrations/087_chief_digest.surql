-- scribe3 · 087_chief_digest.surql · P2:每日创作摘报(cron 产出,决策收件箱消费)
-- 一天一行(day 唯一,重跑覆盖);error 非空=当日汇总有失败源(收件箱如实红字,不静默)。
DEFINE TABLE IF NOT EXISTS chief_digest SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS work ON chief_digest TYPE string;
DEFINE FIELD IF NOT EXISTS day ON chief_digest TYPE string;
DEFINE FIELD IF NOT EXISTS body ON chief_digest TYPE string;
DEFINE FIELD IF NOT EXISTS error ON chief_digest TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON chief_digest TYPE datetime DEFAULT time::now();
DEFINE INDEX IF NOT EXISTS chief_digest_day ON chief_digest FIELDS day UNIQUE;
