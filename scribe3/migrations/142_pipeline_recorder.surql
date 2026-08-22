-- 142_pipeline_recorder.surql
-- 飞行记录仪：完整事件 + 真实工件。不含 API key / Cookie / secret 值 / leak_markers 明文。

DEFINE FIELD IF NOT EXISTS event_count ON pipeline_chain TYPE option<int>;
DEFINE FIELD IF NOT EXISTS artifact_count ON pipeline_chain TYPE option<int>;
DEFINE FIELD IF NOT EXISTS log_count ON pipeline_chain TYPE option<int>;

DEFINE TABLE IF NOT EXISTS pipeline_artifact SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS artifact_id ON pipeline_artifact TYPE string;
DEFINE FIELD IF NOT EXISTS trace_id ON pipeline_artifact TYPE string;
DEFINE FIELD IF NOT EXISTS span_id ON pipeline_artifact TYPE option<string>;
DEFINE FIELD IF NOT EXISTS kind ON pipeline_artifact TYPE string;
DEFINE FIELD IF NOT EXISTS name ON pipeline_artifact TYPE option<string>;
DEFINE FIELD IF NOT EXISTS media ON pipeline_artifact TYPE string
  ASSERT $value IN ['text', 'json'];
DEFINE FIELD IF NOT EXISTS body ON pipeline_artifact TYPE string;
DEFINE FIELD IF NOT EXISTS digest ON pipeline_artifact TYPE option<string>;
DEFINE FIELD IF NOT EXISTS chars ON pipeline_artifact TYPE int;
DEFINE FIELD IF NOT EXISTS chars_full ON pipeline_artifact TYPE option<int>;
DEFINE FIELD IF NOT EXISTS tokens_est ON pipeline_artifact TYPE option<int>;
DEFINE FIELD IF NOT EXISTS truncated ON pipeline_artifact TYPE bool;
DEFINE FIELD IF NOT EXISTS redacted ON pipeline_artifact TYPE bool;
DEFINE FIELD IF NOT EXISTS work ON pipeline_artifact TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON pipeline_artifact TYPE int;
DEFINE FIELD IF NOT EXISTS schema_ver ON pipeline_artifact TYPE string;
DEFINE FIELD IF NOT EXISTS created_at ON pipeline_artifact TYPE datetime VALUE time::now() READONLY;

DEFINE INDEX IF NOT EXISTS pipeline_artifact_id_idx ON pipeline_artifact FIELDS artifact_id UNIQUE;
DEFINE INDEX IF NOT EXISTS pipeline_artifact_trace_idx ON pipeline_artifact FIELDS trace_id, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_artifact_kind_idx ON pipeline_artifact FIELDS work, kind, name, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_artifact_created_idx ON pipeline_artifact FIELDS created_at;

DEFINE TABLE IF NOT EXISTS pipeline_event SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS event_id ON pipeline_event TYPE string;
DEFINE FIELD IF NOT EXISTS trace_id ON pipeline_event TYPE string;
DEFINE FIELD IF NOT EXISTS span_id ON pipeline_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS seq ON pipeline_event TYPE int;
DEFINE FIELD IF NOT EXISTS ts ON pipeline_event TYPE datetime;
DEFINE FIELD IF NOT EXISTS level ON pipeline_event TYPE string
  ASSERT $value IN ['debug', 'info', 'warn', 'error'];
DEFINE FIELD IF NOT EXISTS step_key ON pipeline_event TYPE string;
DEFINE FIELD IF NOT EXISTS step_title ON pipeline_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS layer ON pipeline_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS kind ON pipeline_event TYPE string;
DEFINE FIELD IF NOT EXISTS summary ON pipeline_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS empty ON pipeline_event TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS pred ON pipeline_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS pred_value ON pipeline_event TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS artifact_ids ON pipeline_event TYPE option<array>;
DEFINE FIELD IF NOT EXISTS artifact_ids.* ON pipeline_event TYPE string;
DEFINE FIELD IF NOT EXISTS from_span_id ON pipeline_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS from_step_key ON pipeline_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS from_artifact_id ON pipeline_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS payload ON pipeline_event TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS work ON pipeline_event TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON pipeline_event TYPE int;
DEFINE FIELD IF NOT EXISTS chain_kind ON pipeline_event TYPE string;
DEFINE FIELD IF NOT EXISTS schema_ver ON pipeline_event TYPE string;
DEFINE FIELD IF NOT EXISTS created_at ON pipeline_event TYPE datetime VALUE time::now() READONLY;

DEFINE INDEX IF NOT EXISTS pipeline_event_id_idx ON pipeline_event FIELDS event_id UNIQUE;
DEFINE INDEX IF NOT EXISTS pipeline_event_trace_idx ON pipeline_event FIELDS trace_id, seq;
DEFINE INDEX IF NOT EXISTS pipeline_event_step_idx ON pipeline_event FIELDS work, step_key, kind, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_event_kind_idx ON pipeline_event FIELDS work, kind, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_event_empty_idx ON pipeline_event FIELDS work, step_key, empty, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_event_art_idx ON pipeline_event FIELDS from_artifact_id;
DEFINE INDEX IF NOT EXISTS pipeline_event_created_idx ON pipeline_event FIELDS created_at;
