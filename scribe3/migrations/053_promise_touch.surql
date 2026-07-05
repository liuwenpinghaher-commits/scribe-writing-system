-- scribe3 · 053_promise_touch.surql · 伏笔章触及(本章推进/呼应了哪条伏笔 + 引文)
-- 新表 SCHEMAFULL,ingest 抽取落库;purge_ingest 幂等清除。
DEFINE TABLE IF NOT EXISTS promise_touch SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS promise_id ON promise_touch TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON promise_touch TYPE int;
DEFINE FIELD IF NOT EXISTS evidence ON promise_touch TYPE option<string>;
DEFINE FIELD IF NOT EXISTS ingest_seq ON promise_touch TYPE option<int>;
