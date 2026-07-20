-- Creative Context 审计闭环：版本化 Policy 快照、来源选入状态与非空 revision。
-- 091/092 已发布，升级只能追加迁移；先回填旧行，再收紧 READONLY 合同。

DEFINE FIELD IF NOT EXISTS policy_key ON context_policy_snapshot TYPE option<string>;
DEFINE FIELD IF NOT EXISTS schema_hash ON context_policy_snapshot TYPE option<string>;
DEFINE FIELD IF NOT EXISTS payload ON context_policy_snapshot TYPE option<object> FLEXIBLE;
UPDATE context_policy_snapshot SET
    policy_key = 'generation',
    schema_hash = 'f6235d430969384a4124e238277c0e841a8d0975591a1eb002040acde98edd38',
    payload = {
        policy_key: 'generation',
        version: 'generation.v1',
        task_kinds: ['draft', 'final'],
        canonical_source_kinds: ['canonical'],
        forbidden_source_kinds: ['reference_work_text', 'raw_reference_text', 'model_inference'],
        protocol_versions: {
            context_policy: 'creative-context-policy.v2',
            secret_guard: 'scribe3-secret-guard.v1',
            system_instructions: 'scribe3-write-system.v1',
            write_protocol: 'scribe3-write-protocol.v1'
        }
    }
WHERE policy_key IS NONE OR schema_hash IS NONE OR payload IS NONE;
DEFINE FIELD OVERWRITE policy_key ON context_policy_snapshot TYPE string READONLY;
DEFINE FIELD OVERWRITE policy_version ON context_policy_snapshot TYPE string READONLY;
DEFINE FIELD OVERWRITE schema_hash ON context_policy_snapshot TYPE string READONLY;
DEFINE FIELD OVERWRITE payload ON context_policy_snapshot TYPE object FLEXIBLE READONLY;
DEFINE INDEX IF NOT EXISTS context_policy_snapshot_key_version_idx
    ON context_policy_snapshot FIELDS policy_key, policy_version UNIQUE;

DEFINE FIELD IF NOT EXISTS policy_key ON context_manifest TYPE option<string>;
DEFINE FIELD IF NOT EXISTS policy_schema_hash ON context_manifest TYPE option<string>;
UPDATE context_manifest SET
    policy_key = 'generation',
    policy_schema_hash = 'f6235d430969384a4124e238277c0e841a8d0975591a1eb002040acde98edd38'
WHERE policy_key IS NONE OR policy_schema_hash IS NONE;
DEFINE FIELD OVERWRITE policy_key ON context_manifest TYPE string READONLY;
DEFINE FIELD OVERWRITE policy_schema_hash ON context_manifest TYPE string READONLY;

DEFINE FIELD IF NOT EXISTS included ON context_manifest_source TYPE option<bool>;
UPDATE context_manifest_source SET included = true WHERE included IS NONE;
-- 092 已把旧 revision 定义为 READONLY option<string>；先临时解锁才能回填真旧行。
DEFINE FIELD OVERWRITE revision ON context_manifest_source TYPE option<string>;
UPDATE context_manifest_source SET revision = string::concat('content-sha256:', content_digest)
    WHERE revision IS NONE;
DEFINE FIELD OVERWRITE revision ON context_manifest_source TYPE string READONLY;
DEFINE FIELD OVERWRITE included ON context_manifest_source TYPE bool READONLY;

-- Outcome 明确区分 transport/gateway 与实际 reasoning provider；未观测到的字段保持 NONE。
DEFINE FIELD IF NOT EXISTS transport_provider ON context_outcome_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS transport_request_id ON context_outcome_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS reasoning_provider ON context_outcome_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS reasoning_model ON context_outcome_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS reasoning_request_id ON context_outcome_trace TYPE option<string>;
DEFINE FIELD OVERWRITE transport_provider ON context_outcome_trace TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE transport_request_id ON context_outcome_trace TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE reasoning_provider ON context_outcome_trace TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE reasoning_model ON context_outcome_trace TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE reasoning_request_id ON context_outcome_trace TYPE option<string> READONLY;
