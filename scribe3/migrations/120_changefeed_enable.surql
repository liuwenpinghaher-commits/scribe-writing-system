-- S-2 历史说明（本文件仍 no-op，保留迁移序号）
-- 旧路径：对已有 SCHEMAFULL 裸 `DEFINE TABLE x CHANGEFEED` → table exists → apply_schema 挂。
-- 最优路径（demo 数据可丢）：001/004/055/078 建表即 CHANGEFEED；旧库用
--   python -m scribe3.tools.rebuild_db_native_changefeed --all --commit --yes
-- 旁路 cache_watch 仍可用（125）；consumer 同时 watch 真表 + cache_watch。
SELECT * FROM _migration WHERE false;
