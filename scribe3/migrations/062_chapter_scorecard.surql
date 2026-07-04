-- scribe3 · 062_chapter_scorecard.surql · 章级北极星 scorecard 缓存(北极星方案任务3,蓝图 §3-③)
-- 独立缓存表而非章表字段(台账 D-008):/live SSE 推送轻(不裹 prose/embedding 大字段),
-- 三分栏 JSON 随任务6(fulfillment)演进不再动章表。存稿即算(save_chapter fail-soft 挂接)。
-- 三栏均为 JSON 串(scene_meta/qc_breakdown 先例):constraints 硬约束/advisory 软参考/
-- fulfillment 正向达成(任务6 前占位)。不合成总分(宪法条款)。
DEFINE TABLE IF NOT EXISTS chapter_scorecard SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON chapter_scorecard TYPE int;
DEFINE FIELD IF NOT EXISTS constraints ON chapter_scorecard TYPE string;
DEFINE FIELD IF NOT EXISTS advisory ON chapter_scorecard TYPE string;
DEFINE FIELD IF NOT EXISTS fulfillment ON chapter_scorecard TYPE string;
DEFINE FIELD IF NOT EXISTS degraded ON chapter_scorecard TYPE string;
DEFINE FIELD IF NOT EXISTS computed_at ON chapter_scorecard TYPE datetime;
