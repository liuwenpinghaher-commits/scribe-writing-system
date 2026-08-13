-- 140_pipeline_trace.surql · 写路径步骤全量账（系统分析）
-- 不含提示词正文 / secret value / leak_markers / 工具参数原文。

DEFINE TABLE IF NOT EXISTS pipeline_chain SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS trace_id ON pipeline_chain TYPE string;
DEFINE FIELD IF NOT EXISTS work ON pipeline_chain TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON pipeline_chain TYPE int;
DEFINE FIELD IF NOT EXISTS kind ON pipeline_chain TYPE string
  ASSERT $value IN ['write', 'save', 'claim'];
DEFINE FIELD IF NOT EXISTS phase ON pipeline_chain TYPE option<string>;
DEFINE FIELD IF NOT EXISTS status ON pipeline_chain TYPE string
  ASSERT $value IN ['in_progress', 'ok', 'failed', 'abandoned'];
DEFINE FIELD IF NOT EXISTS cursor_step_key ON pipeline_chain TYPE option<string>;
DEFINE FIELD IF NOT EXISTS headline ON pipeline_chain TYPE option<string>;
DEFINE FIELD IF NOT EXISTS started_at ON pipeline_chain TYPE datetime;
DEFINE FIELD IF NOT EXISTS ended_at ON pipeline_chain TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS duration_ms ON pipeline_chain TYPE option<float>;
DEFINE FIELD IF NOT EXISTS span_count ON pipeline_chain TYPE int;
DEFINE FIELD IF NOT EXISTS red_count ON pipeline_chain TYPE int;
DEFINE FIELD IF NOT EXISTS manifest_id ON pipeline_chain TYPE option<string>;
DEFINE FIELD IF NOT EXISTS actual_input_hash ON pipeline_chain TYPE option<string>;
DEFINE FIELD IF NOT EXISTS outcome_id ON pipeline_chain TYPE option<string>;
DEFINE FIELD IF NOT EXISTS outcome_status ON pipeline_chain TYPE option<string>;
DEFINE FIELD IF NOT EXISTS outcome_usage ON pipeline_chain TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS contrast_run_id ON pipeline_chain TYPE option<string>;
DEFINE FIELD IF NOT EXISTS contrast_summary ON pipeline_chain TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS notes ON pipeline_chain TYPE option<array>;
DEFINE FIELD IF NOT EXISTS notes.* ON pipeline_chain TYPE string;
DEFINE FIELD IF NOT EXISTS schema_ver ON pipeline_chain TYPE string;
DEFINE FIELD IF NOT EXISTS created_at ON pipeline_chain TYPE datetime VALUE time::now() READONLY;

DEFINE INDEX IF NOT EXISTS pipeline_chain_id_idx ON pipeline_chain FIELDS trace_id UNIQUE;
DEFINE INDEX IF NOT EXISTS pipeline_chain_work_ch_idx ON pipeline_chain FIELDS work, chapter, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_chain_kind_idx ON pipeline_chain FIELDS kind, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_chain_status_idx ON pipeline_chain FIELDS status, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_chain_outcome_idx ON pipeline_chain FIELDS outcome_id;
DEFINE INDEX IF NOT EXISTS pipeline_chain_contrast_idx ON pipeline_chain FIELDS contrast_run_id;
DEFINE INDEX IF NOT EXISTS pipeline_chain_created_idx ON pipeline_chain FIELDS created_at;

DEFINE TABLE IF NOT EXISTS pipeline_span SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS span_id ON pipeline_span TYPE string;
DEFINE FIELD IF NOT EXISTS parent_span_id ON pipeline_span TYPE option<string>;
DEFINE FIELD IF NOT EXISTS trace_id ON pipeline_span TYPE string;
DEFINE FIELD IF NOT EXISTS work ON pipeline_span TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON pipeline_span TYPE int;
DEFINE FIELD IF NOT EXISTS kind ON pipeline_span TYPE string;
DEFINE FIELD IF NOT EXISTS step_key ON pipeline_span TYPE string;
DEFINE FIELD IF NOT EXISTS step_title ON pipeline_span TYPE string;
DEFINE FIELD IF NOT EXISTS layer ON pipeline_span TYPE string;
DEFINE FIELD IF NOT EXISTS tier ON pipeline_span TYPE option<string>;
DEFINE FIELD IF NOT EXISTS zone ON pipeline_span TYPE option<string>;
DEFINE FIELD IF NOT EXISTS status ON pipeline_span TYPE string;
DEFINE FIELD IF NOT EXISTS expected ON pipeline_span TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS expected_reason ON pipeline_span TYPE option<string>;
DEFINE FIELD IF NOT EXISTS actual ON pipeline_span TYPE option<string>;
DEFINE FIELD IF NOT EXISTS actual_reason ON pipeline_span TYPE option<string>;
DEFINE FIELD IF NOT EXISTS verdict ON pipeline_span TYPE option<string>;
DEFINE FIELD IF NOT EXISTS input ON pipeline_span TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS compute ON pipeline_span TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS output ON pipeline_span TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS timing ON pipeline_span TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS events ON pipeline_span TYPE option<array>;
DEFINE FIELD IF NOT EXISTS events.* ON pipeline_span TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS quality ON pipeline_span TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS error ON pipeline_span TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS links ON pipeline_span TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS schema_ver ON pipeline_span TYPE string;
DEFINE FIELD IF NOT EXISTS created_at ON pipeline_span TYPE datetime VALUE time::now() READONLY;

DEFINE INDEX IF NOT EXISTS pipeline_span_id_idx ON pipeline_span FIELDS span_id UNIQUE;
DEFINE INDEX IF NOT EXISTS pipeline_span_trace_idx ON pipeline_span FIELDS trace_id, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_span_step_idx ON pipeline_span FIELDS work, step_key, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_span_status_idx ON pipeline_span FIELDS status, created_at;
DEFINE INDEX IF NOT EXISTS pipeline_span_created_idx ON pipeline_span FIELDS created_at;
