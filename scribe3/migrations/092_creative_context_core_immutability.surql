-- 已应用 091 的升级路径：先消除旧自由 error/status，再收紧不可变审计合同。
-- SurQL 不能安全复刻 Python 的领域秘密 redactor：任何非 NONE 旧 error 一律丢弃为
-- 固定无敏感占位，绝不试图保留或部分脱敏未知历史文本；NONE 保持 NONE。
UPDATE context_outcome_trace SET error='[redacted_legacy_error]' WHERE error IS NOT NONE;
-- 091 曾允许任意状态。先规范化才加 ASSERT，避免历史 completed/未知值使迁移失败。
UPDATE context_outcome_trace SET status = IF status = 'completed' {
    'succeeded'
} ELSE IF status IN ['succeeded', 'failed', 'incomplete_stream', 'cancelled'] {
    status
} ELSE {
    'failed'
};

-- 清洗完成后，审计核心在 CREATE 后不可变。
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
DEFINE FIELD OVERWRITE created_at ON context_outcome_trace TYPE datetime READONLY;
