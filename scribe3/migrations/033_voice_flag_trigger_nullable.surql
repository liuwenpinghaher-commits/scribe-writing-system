-- scribe3 · 033_voice_flag_trigger_nullable.surql
-- 修 schema 漂移:旧库(如 main)的 voice_evolution_flag.trigger_chapter 被定义为必填 int,
-- 而 021 的本意是 option<int>(因 IF NOT EXISTS + 按文件名记录迁移,旧定义未被更新)。
-- ingest 触发声音标记时,add_voice_flag 未必带 trigger_chapter → NONE 强转 int 报错。
-- 这里 OVERWRITE 成 option<int>,统一为可空,根治漂移。配合 store.add_voice_flag 现已显式写入。
DEFINE FIELD OVERWRITE trigger_chapter ON voice_evolution_flag TYPE option<int>;
