-- scribe3 · 077_editorial_thread.surql · 主编历史:一 work 一连续线程 + 每轮焦点标签(Task 6)
-- 为什么:此前主编对话按"焦点(sel/phase/focalizer)"拆 chatKey——切角色即切对话,历史被打成碎片。
-- 改为一 work 一条 editorial_thread(连续线程),每条 chat_message 挂 thread_id 并带本轮的
-- context 绑定字段(revision/hash/focus),焦点成为"每轮标签"而非"分线程键"。
-- 隔离靠 per-work db(与 chat_message 一致):thread_id 全局唯一,别的 work 的 db 里读不到。
DEFINE TABLE IF NOT EXISTS editorial_thread SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS thread_id ON editorial_thread TYPE string;
DEFINE FIELD IF NOT EXISTS work ON editorial_thread TYPE string;
DEFINE FIELD IF NOT EXISTS actor_id ON editorial_thread TYPE string;
DEFINE FIELD IF NOT EXISTS parent_thread_id ON editorial_thread TYPE option<string>;
DEFINE FIELD IF NOT EXISTS title ON editorial_thread TYPE string DEFAULT '主编讨论';
DEFINE FIELD IF NOT EXISTS status ON editorial_thread TYPE string ASSERT $value IN ['active', 'archived'];
DEFINE FIELD IF NOT EXISTS hermes_conversation_id ON editorial_thread TYPE option<string>;
DEFINE FIELD IF NOT EXISTS previous_response_id ON editorial_thread TYPE option<string>;
DEFINE FIELD IF NOT EXISTS summary ON editorial_thread TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS created_at ON editorial_thread TYPE datetime VALUE time::now() READONLY;
DEFINE FIELD IF NOT EXISTS updated_at ON editorial_thread TYPE datetime;
DEFINE INDEX IF NOT EXISTS editorial_thread_id_idx ON editorial_thread FIELDS thread_id UNIQUE;
DEFINE INDEX IF NOT EXISTS editorial_thread_active_idx ON editorial_thread FIELDS work, actor_id, status;

-- chat_message 扩展:线程归属 + 本轮 context 绑定(全 option,向后兼容存量行/直写调用方)。
DEFINE FIELD IF NOT EXISTS thread_id ON chat_message TYPE option<string>;
DEFINE FIELD IF NOT EXISTS context_session_id ON chat_message TYPE option<string>;
DEFINE FIELD IF NOT EXISTS context_revision ON chat_message TYPE option<int>;
DEFINE FIELD IF NOT EXISTS context_hash ON chat_message TYPE option<string>;
DEFINE FIELD IF NOT EXISTS focus ON chat_message TYPE option<object>;
DEFINE FIELD IF NOT EXISTS focus.* ON chat_message TYPE any;
DEFINE FIELD IF NOT EXISTS response_id ON chat_message TYPE option<string>;
DEFINE INDEX IF NOT EXISTS chat_message_thread_ts_idx ON chat_message FIELDS thread_id, ts;
