-- 111_context_turn_bind.surql · B∪C 上下文检查器 Turn 绑定
-- 按 (context_session_id, snapshot_revision) 存最新一轮编译投影，供检查器按导航 rev 读取。
-- 不含提示词正文 / secret value；selected/rejected 已在写入前 mask。

DEFINE TABLE IF NOT EXISTS context_turn_bind SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS bind_id ON context_turn_bind TYPE string;
DEFINE FIELD IF NOT EXISTS work ON context_turn_bind TYPE string;
DEFINE FIELD IF NOT EXISTS context_session_id ON context_turn_bind TYPE string;
DEFINE FIELD IF NOT EXISTS snapshot_revision ON context_turn_bind TYPE int;
DEFINE FIELD IF NOT EXISTS task_kind ON context_turn_bind TYPE string;
DEFINE FIELD IF NOT EXISTS path ON context_turn_bind TYPE string;
DEFINE FIELD IF NOT EXISTS availability ON context_turn_bind TYPE string;
DEFINE FIELD IF NOT EXISTS manifest_id ON context_turn_bind TYPE option<string>;
DEFINE FIELD IF NOT EXISTS request_id ON context_turn_bind TYPE option<string>;
DEFINE FIELD IF NOT EXISTS actual_input_hash ON context_turn_bind TYPE option<string>;
DEFINE FIELD IF NOT EXISTS policy_version ON context_turn_bind TYPE option<string>;
DEFINE FIELD IF NOT EXISTS envelope_hash ON context_turn_bind TYPE string;
DEFINE FIELD IF NOT EXISTS query ON context_turn_bind TYPE string;
DEFINE FIELD IF NOT EXISTS synthetic_snapshot ON context_turn_bind TYPE bool;
DEFINE FIELD IF NOT EXISTS block_tokens ON context_turn_bind TYPE object;
DEFINE FIELD IF NOT EXISTS block_tokens.* ON context_turn_bind TYPE any;
DEFINE FIELD IF NOT EXISTS blocks ON context_turn_bind TYPE array;
DEFINE FIELD IF NOT EXISTS blocks.* ON context_turn_bind TYPE object;
DEFINE FIELD IF NOT EXISTS blocks.*.* ON context_turn_bind TYPE any;
DEFINE FIELD IF NOT EXISTS selected ON context_turn_bind TYPE array;
DEFINE FIELD IF NOT EXISTS selected.* ON context_turn_bind TYPE object;
DEFINE FIELD IF NOT EXISTS selected.*.* ON context_turn_bind TYPE any;
DEFINE FIELD IF NOT EXISTS rejected ON context_turn_bind TYPE array;
DEFINE FIELD IF NOT EXISTS rejected.* ON context_turn_bind TYPE object;
DEFINE FIELD IF NOT EXISTS rejected.*.* ON context_turn_bind TYPE any;
DEFINE FIELD IF NOT EXISTS usage_digest ON context_turn_bind TYPE object;
DEFINE FIELD IF NOT EXISTS usage_digest.* ON context_turn_bind TYPE any;
DEFINE FIELD IF NOT EXISTS created_at ON context_turn_bind TYPE datetime VALUE time::now() READONLY;
DEFINE INDEX IF NOT EXISTS context_turn_bind_id_idx ON context_turn_bind FIELDS bind_id UNIQUE;
DEFINE INDEX IF NOT EXISTS context_turn_bind_session_rev_idx ON context_turn_bind FIELDS context_session_id, snapshot_revision;
