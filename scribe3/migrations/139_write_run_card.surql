-- 139_write_run_card.surql · 写/存/宣称 Run 卡（期望×实际×质量）
-- 不含提示词正文 / secret value / leak_markers 明文。
DEFINE TABLE IF NOT EXISTS write_run_card SCHEMAFULL;

DEFINE FIELD IF NOT EXISTS run_id ON write_run_card TYPE string;
DEFINE FIELD IF NOT EXISTS work ON write_run_card TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON write_run_card TYPE int;
DEFINE FIELD IF NOT EXISTS kind ON write_run_card TYPE string
  ASSERT $value IN ['write', 'save', 'claim'];
DEFINE FIELD IF NOT EXISTS phase ON write_run_card TYPE option<string>;
DEFINE FIELD IF NOT EXISTS request_id ON write_run_card TYPE option<string>;
DEFINE FIELD IF NOT EXISTS manifest_id ON write_run_card TYPE option<string>;
DEFINE FIELD IF NOT EXISTS actual_input_hash ON write_run_card TYPE option<string>;
DEFINE FIELD IF NOT EXISTS outcome_id ON write_run_card TYPE option<string>;
DEFINE FIELD IF NOT EXISTS outcome_status ON write_run_card TYPE option<string>;
DEFINE FIELD IF NOT EXISTS outcome_usage ON write_run_card TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS assemble_ok ON write_run_card TYPE bool;
DEFINE FIELD IF NOT EXISTS verdict ON write_run_card TYPE string
  ASSERT $value IN ['green', 'red'];
DEFINE FIELD IF NOT EXISTS summary ON write_run_card TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS rows ON write_run_card TYPE array;
DEFINE FIELD IF NOT EXISTS rows.* ON write_run_card TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS quality ON write_run_card TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS facts ON write_run_card TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS caps ON write_run_card TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS l2 ON write_run_card TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS density ON write_run_card TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS quality_flags ON write_run_card TYPE array;
DEFINE FIELD IF NOT EXISTS quality_flags.* ON write_run_card TYPE string;
DEFINE FIELD IF NOT EXISTS schema_ver ON write_run_card TYPE string;
DEFINE FIELD IF NOT EXISTS created_at ON write_run_card TYPE datetime VALUE time::now() READONLY;

DEFINE INDEX IF NOT EXISTS write_run_card_id_idx ON write_run_card FIELDS run_id UNIQUE;
DEFINE INDEX IF NOT EXISTS write_run_card_request_idx ON write_run_card FIELDS request_id;
DEFINE INDEX IF NOT EXISTS write_run_card_work_ch_idx ON write_run_card FIELDS work, chapter, created_at;
DEFINE INDEX IF NOT EXISTS write_run_card_kind_idx ON write_run_card FIELDS kind, created_at;
DEFINE INDEX IF NOT EXISTS write_run_card_created_idx ON write_run_card FIELDS created_at;
