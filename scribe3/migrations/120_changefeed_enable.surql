-- S-2: Changefeed 启用说明（不自动 DEFINE TABLE，避免「table already exists」打断 apply_schema）
-- 现网 Surreal 3.2.x 对已有 SCHEMAFULL 表执行 `DEFINE TABLE proposition CHANGEFEED 1h`
-- 会报 already exists 并导致整库迁移失败（health db=down）。
--
-- 运维可选（手工、非本迁移）：在目标 DB 用与建表一致的 OVERWRITE 全量字段声明 + CHANGEFEED，
-- 或升级后使用官方 ALTER/CHANGEFEED 语法。
-- 代码侧：changefeed_consumer 在 SHOW CHANGES 可用时消费；flag 默认关。
-- 占位：无副作用语句，仅标记迁移已应用。
SELECT * FROM _migration WHERE false;
