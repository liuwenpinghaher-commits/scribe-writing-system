-- 141_pipeline_log.surql · 逐步运行分析账本（主对象）
-- 不含提示词正文 / secret value / 工具参数值。

DEFINE TABLE IF NOT EXISTS pipeline_log SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS log_id ON pipeline_log TYPE string;
DEFINE FIELD IF NOT EXISTS trace_id ON pipeline_log TYPE string;
DEFINE FIELD IF NOT EXISTS span_id ON pipeline_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS seq ON pipeline_log TYPE int;
DEFINE FIELD IF NOT EXISTS ts ON pipeline_log TYPE datetime;
DEFINE FIELD IF NOT EXISTS level ON pipeline_log TYPE string
  ASSERT $value IN ['debug', 'info', 'warn', 'error'];
DEFINE FIELD IF NOT EXISTS step_key ON pipeline_log TYPE string;
DEFINE FIELD IF NOT EXISTS step_title ON pipeline_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS layer ON pipeline_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS code ON pipeline_log TYPE string;
DEFINE FIELD IF NOT EXISTS message ON pipeline_log TYPE string;
DEFINE FIELD IF NOT EXISTS attrs ON pipeline_log TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS work ON pipeline_log TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON pipeline_log TYPE int;
DEFINE FIELD IF NOT EXISTS kind ON pipeline_log TYPE string;
DEFINE FIELD IF NOT EXISTS schema_ver ON pipeline_log TYPE string;
DEFINE FIELD IF NOT EXISTS created_at ON pipeline_log TYPE datetime VALUE time::now() READONLY;

DEFINE INDEX IF NOT EXISTS pipeline_log_id_idx ON pipeline_log FIELDS log_id UNIQUE;
DEFINE INDEX IF NOT EXISTS pipeline_log_trace_idx ON pipeline_log FIELDS trace_id, seq;
DEFINE INDEX IF NOT EXISTS pipeline_log_step_idx ON pipeline_log FIELDS work, step_key, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_log_code_idx ON pipeline_log FIELDS work, code, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_log_created_idx ON pipeline_log FIELDS created_at;
