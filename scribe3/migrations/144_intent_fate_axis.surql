-- scribe3 · 144_intent_fate_axis.surql · 命运轴四字段（fate-dearer rev.7）
-- 谁付钱 / 轴用语 / 书钟起止。TYPE string DEFAULT ''。
DEFINE FIELD IF NOT EXISTS who_pays ON intent TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS axis_terms ON intent TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS clock_start ON intent TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS clock_end ON intent TYPE string DEFAULT '';
