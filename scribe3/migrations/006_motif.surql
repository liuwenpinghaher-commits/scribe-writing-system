-- scribe3 · 母题(motif):反复出现的意象 + 绑定主题 + 物质回声 + 隐喻展开。
-- 戏剧层的贯穿线之一;参照不透支(点到为止)。
DEFINE TABLE IF NOT EXISTS motif SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name      ON motif TYPE string;
DEFINE FIELD IF NOT EXISTS theme     ON motif TYPE string DEFAULT '';   -- 绑定主题
DEFINE FIELD IF NOT EXISTS echoes    ON motif TYPE string DEFAULT '';   -- 物质回声
DEFINE FIELD IF NOT EXISTS unfolding ON motif TYPE string DEFAULT '';   -- 隐喻展开
