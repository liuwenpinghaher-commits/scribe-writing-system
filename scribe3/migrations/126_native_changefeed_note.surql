-- S-2 最优路径说明（本迁移无副作用）
-- 关键表（proposition/chapter/material/memory_item/character/event）在 001/004/055/078
-- 已改为「建表即 CHANGEFEED」。仅对新 apply_schema 的空库生效。
--
-- 已有库 / feed 冻住时：demo 数据可丢则跑
--   python -m scribe3.tools.rebuild_db_native_changefeed --all --yes
-- 旁路 cache_watch（125）保留作双写补充，非唯一真相源。
SELECT * FROM _migration WHERE false;
