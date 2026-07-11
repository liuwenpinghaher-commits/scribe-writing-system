-- 079_memory_capture.surql · Task 9:幂等捕获管线 outbox + 正典待审 + 活化缺口回填
-- 只增不改(迁移铁律):三处新增,全 IF NOT EXISTS,幂等重放无害。
--   ① memory_item 追加 provenance/linked_ids —— 打通 Task 8 已就绪但静默失效的
--      正典压制(_suppress_by_canonical 靠 provenance 的 (entity,attribute))与 focus 加权
--      (final_score 靠 linked_ids)。回填后 RetrievalResult.unconflictable_count/unlinked_count 归零。
--   ② memory_event —— 幂等事件 outbox(event_id UNIQUE),同步 drain 的状态机载体。
--   ③ pending_authority_claim —— 正典揭示(真实身份等)待审队列;宪法红线:
--      canonical 事实【绝不】进 memory_item,一律经此待审再进领域表,fact 唯一真相源仍是领域表。

-- ① memory_item 活化字段(array<object> 沿用 074 ai_run_trace 的 .* / .*.* 惯例)
DEFINE FIELD IF NOT EXISTS provenance ON memory_item TYPE array DEFAULT [];
DEFINE FIELD IF NOT EXISTS provenance.* ON memory_item TYPE object;
DEFINE FIELD IF NOT EXISTS provenance.*.* ON memory_item TYPE any;
DEFINE FIELD IF NOT EXISTS linked_ids ON memory_item TYPE array<string> DEFAULT [];

-- ② 幂等事件 outbox(计划 Task 9 Step 3 SQL,逐字)
DEFINE TABLE IF NOT EXISTS memory_event SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS event_id ON memory_event TYPE string;
DEFINE FIELD IF NOT EXISTS work ON memory_event TYPE string;
DEFINE FIELD IF NOT EXISTS thread_id ON memory_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS event_type ON memory_event TYPE string ASSERT $value IN ['navigation', 'turn', 'write', 'approval', 'save', 'compress', 'session_end'];
DEFINE FIELD IF NOT EXISTS payload ON memory_event TYPE object DEFAULT {};
DEFINE FIELD IF NOT EXISTS payload.* ON memory_event TYPE any;
DEFINE FIELD IF NOT EXISTS status ON memory_event TYPE string ASSERT $value IN ['pending', 'processing', 'complete', 'failed'] DEFAULT 'pending';
DEFINE FIELD IF NOT EXISTS attempts ON memory_event TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS error ON memory_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON memory_event TYPE datetime VALUE time::now() READONLY;
DEFINE FIELD IF NOT EXISTS processed_at ON memory_event TYPE option<datetime>;
DEFINE INDEX IF NOT EXISTS memory_event_id_idx ON memory_event FIELDS event_id UNIQUE;
DEFINE INDEX IF NOT EXISTS memory_event_pending_idx ON memory_event FIELDS work, status, created_at;

-- ③ 正典揭示待审队列(限知红线:canonical 绝不进 memory_item)
DEFINE TABLE IF NOT EXISTS pending_authority_claim SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS work ON pending_authority_claim TYPE string;
DEFINE FIELD IF NOT EXISTS thread_id ON pending_authority_claim TYPE option<string>;
DEFINE FIELD IF NOT EXISTS text ON pending_authority_claim TYPE string;
DEFINE FIELD IF NOT EXISTS entity ON pending_authority_claim TYPE option<string>;
DEFINE FIELD IF NOT EXISTS attribute ON pending_authority_claim TYPE option<string>;
DEFINE FIELD IF NOT EXISTS value ON pending_authority_claim TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_type ON pending_authority_claim TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS source_id ON pending_authority_claim TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS status ON pending_authority_claim TYPE string ASSERT $value IN ['pending', 'approved', 'rejected'] DEFAULT 'pending';
DEFINE FIELD IF NOT EXISTS created_at ON pending_authority_claim TYPE datetime VALUE time::now() READONLY;
DEFINE INDEX IF NOT EXISTS pending_authority_status_idx ON pending_authority_claim FIELDS work, status, created_at;
