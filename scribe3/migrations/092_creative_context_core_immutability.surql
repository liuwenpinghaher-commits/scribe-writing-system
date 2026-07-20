-- 已应用 091 的升级路径：审计核心在 CREATE 后不可变。CREATE 仍可完整赋值；
-- 仅 created_at 保留为时间字段，其他身份与载荷字段拒绝 UPDATE。
DEFINE FIELD OVERWRITE policy_snapshot_id ON context_policy_snapshot TYPE string READONLY;
DEFINE FIELD OVERWRITE policy_version ON context_policy_snapshot TYPE string READONLY;

DEFINE FIELD OVERWRITE manifest_id ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE manifest_version ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE request_id ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE task_kind ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE policy_version ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE navigation_snapshot_id ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE snapshot_hash ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE envelope_hash ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE actual_input_hash ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE actual_input_bytes ON context_manifest TYPE int READONLY;
DEFINE FIELD OVERWRITE manifest_hash ON context_manifest TYPE string READONLY;

DEFINE FIELD OVERWRITE manifest_id ON context_manifest_source TYPE string READONLY;
DEFINE FIELD OVERWRITE source_ref ON context_manifest_source TYPE string READONLY;
DEFINE FIELD OVERWRITE block ON context_manifest_source TYPE string READONLY;
DEFINE FIELD OVERWRITE source_id ON context_manifest_source TYPE string READONLY;
DEFINE FIELD OVERWRITE source_kind ON context_manifest_source TYPE string READONLY;
DEFINE FIELD OVERWRITE work ON context_manifest_source TYPE string READONLY;
DEFINE FIELD OVERWRITE revision ON context_manifest_source TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE masked ON context_manifest_source TYPE bool READONLY;
DEFINE FIELD OVERWRITE reason_code ON context_manifest_source TYPE string READONLY;
DEFINE FIELD OVERWRITE content_digest ON context_manifest_source TYPE string READONLY;

DEFINE FIELD OVERWRITE outcome_id ON context_outcome_trace TYPE string READONLY;
DEFINE FIELD OVERWRITE request_id ON context_outcome_trace TYPE string READONLY;
DEFINE FIELD OVERWRITE manifest_id ON context_outcome_trace TYPE string READONLY;
DEFINE FIELD OVERWRITE actual_input_hash ON context_outcome_trace TYPE string READONLY;
DEFINE FIELD OVERWRITE status ON context_outcome_trace TYPE string ASSERT $value IN ['succeeded', 'failed', 'incomplete_stream', 'cancelled'] READONLY;
DEFINE FIELD OVERWRITE provider ON context_outcome_trace TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE model ON context_outcome_trace TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE provider_request_id ON context_outcome_trace TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE usage ON context_outcome_trace TYPE option<object> READONLY;
DEFINE FIELD OVERWRITE usage.* ON context_outcome_trace TYPE number READONLY;
DEFINE FIELD OVERWRITE output_hash ON context_outcome_trace TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE error ON context_outcome_trace TYPE option<string> READONLY;
