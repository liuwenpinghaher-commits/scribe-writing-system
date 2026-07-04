-- scribe3 · 066_style_profile.surql · 章级文体档案(北极星方案任务9,QD 防同质化)
-- 纯确定性六元组(句长CV/对话占比/MTLD/虚词指纹/标点节奏/POV 信号)存稿即算;
-- profile JSON 串(scene_meta 先例);书级面板聚合出分布单调告警;选择环复用特征轴。
DEFINE TABLE IF NOT EXISTS style_profile SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON style_profile TYPE int;
DEFINE FIELD IF NOT EXISTS profile ON style_profile TYPE string;
DEFINE FIELD IF NOT EXISTS computed_at ON style_profile TYPE datetime;
