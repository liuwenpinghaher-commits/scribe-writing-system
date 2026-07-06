-- Chapter Pilot(主编主动化 T6):章生命周期状态落库(崩溃可恢复)+ steer 想法字段(T8)。
DEFINE FIELD IF NOT EXISTS pilot_state ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS pilot_state_at ON chapter TYPE option<int>;
DEFINE FIELD IF NOT EXISTS pilot_parked ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS pilot_steer ON chapter TYPE option<string>;
-- 想法收件箱(T8)
DEFINE TABLE IF NOT EXISTS idea SCHEMALESS;
DEFINE FIELD IF NOT EXISTS pilot_card ON chapter TYPE option<string>;
