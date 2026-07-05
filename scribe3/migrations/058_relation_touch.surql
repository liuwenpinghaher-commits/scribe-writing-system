-- scribe3 · 058_relation_touch.surql · 关系触碰追踪(本章哪两个角色之间发生了对关系本身产生实质影响的互动)
-- 新表 SCHEMAFULL,ingest 抽取落库;purge_ingest 幂等清除。方案B任务12:连续性 heat/last_touch 状态机。
DEFINE TABLE IF NOT EXISTS relation_touch SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS a ON relation_touch TYPE string;
DEFINE FIELD IF NOT EXISTS b ON relation_touch TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON relation_touch TYPE int;
DEFINE FIELD IF NOT EXISTS kind ON relation_touch TYPE string;
DEFINE FIELD IF NOT EXISTS note ON relation_touch TYPE option<string>;
