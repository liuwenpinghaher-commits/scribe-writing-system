-- scribe3 · 076_context_session.surql · 统一上下文:会话游标 + 不可变快照历史(Task 3)
-- context_session 持 revision 游标做 CAS 乐观并发;context_snapshot 是只增不改的历史,
-- UNIQUE(session_id, revision) 保证每个版本号只被占用一次,
-- UNIQUE(session_id, navigation_id) 兜底并发幂等重放(快照隔离下预查可能同时通过)。
DEFINE TABLE IF NOT EXISTS context_session SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS work ON context_session TYPE string;
DEFINE FIELD IF NOT EXISTS actor_id ON context_session TYPE string;
DEFINE FIELD IF NOT EXISTS device_id ON context_session TYPE string;
DEFINE FIELD IF NOT EXISTS thread_id ON context_session TYPE string;
DEFINE FIELD IF NOT EXISTS status ON context_session TYPE string ASSERT $value IN ['active', 'ended'];
DEFINE FIELD IF NOT EXISTS revision ON context_session TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS current_snapshot_id ON context_session TYPE option<string>;
DEFINE FIELD IF NOT EXISTS started_at ON context_session TYPE datetime VALUE time::now() READONLY;
DEFINE FIELD IF NOT EXISTS updated_at ON context_session TYPE datetime;
DEFINE INDEX IF NOT EXISTS context_session_work_idx ON context_session FIELDS work;
DEFINE INDEX IF NOT EXISTS context_session_thread_idx ON context_session FIELDS thread_id;

DEFINE TABLE IF NOT EXISTS context_snapshot SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS session_id ON context_snapshot TYPE string;
DEFINE FIELD IF NOT EXISTS work ON context_snapshot TYPE string;
DEFINE FIELD IF NOT EXISTS revision ON context_snapshot TYPE int;
DEFINE FIELD IF NOT EXISTS previous_revision ON context_snapshot TYPE option<int>;
DEFINE FIELD IF NOT EXISTS navigation_id ON context_snapshot TYPE string;
DEFINE FIELD IF NOT EXISTS thread_id ON context_snapshot TYPE string;
DEFINE FIELD IF NOT EXISTS entry ON context_snapshot TYPE string;
DEFINE FIELD IF NOT EXISTS directory_path ON context_snapshot TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS focus ON context_snapshot TYPE object;
DEFINE FIELD IF NOT EXISTS focus.* ON context_snapshot TYPE any;
DEFINE FIELD IF NOT EXISTS detail_route ON context_snapshot TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON context_snapshot TYPE option<int>;
DEFINE FIELD IF NOT EXISTS phase ON context_snapshot TYPE option<string>;
DEFINE FIELD IF NOT EXISTS focalizer ON context_snapshot TYPE option<string>;
DEFINE FIELD IF NOT EXISTS reason ON context_snapshot TYPE string;
DEFINE FIELD IF NOT EXISTS context_hash ON context_snapshot TYPE string;
DEFINE FIELD IF NOT EXISTS captured_at ON context_snapshot TYPE datetime VALUE time::now() READONLY;
DEFINE INDEX IF NOT EXISTS context_snapshot_session_revision ON context_snapshot FIELDS session_id, revision UNIQUE;
DEFINE INDEX IF NOT EXISTS context_snapshot_navigation ON context_snapshot FIELDS session_id, navigation_id UNIQUE;
DEFINE INDEX IF NOT EXISTS context_snapshot_work_focus ON context_snapshot FIELDS work, focus.id;
