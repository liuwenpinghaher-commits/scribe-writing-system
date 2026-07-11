-- 082_memory_trace.surql · Task 14:记忆溯源 trace(上下文检查器数据源)
-- 号段纠正:计划原写 079_memory_trace,但 079 已被 Task 9(079_memory_capture)占用,
--   当前号段已到 081(081_ai_run_context),故本迁移落 082。schema 照计划 Task 14 Step 2。
-- 只增不改(迁移铁律):全 IF NOT EXISTS,幂等重放无害。
-- 一次检索的"主编看到了什么、为什么选这条、为什么弃那条":selected/rejected 各带 reason;
--   channels/block_tokens/latency_ms 是可观测度量;snapshot/envelope_hash 绑到具体上下文快照。
-- 限知红线:私密事实的 value 绝不进此表——落库前经 store.mask_memory_trace 权威屏蔽
--   (secret 证据只留 masked=true 标记,text 抹空,不靠前端不显)。
DEFINE TABLE IF NOT EXISTS memory_trace SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS trace_id ON memory_trace TYPE string;
DEFINE FIELD IF NOT EXISTS work ON memory_trace TYPE string;
DEFINE FIELD IF NOT EXISTS thread_id ON memory_trace TYPE string;
DEFINE FIELD IF NOT EXISTS context_session_id ON memory_trace TYPE string;
DEFINE FIELD IF NOT EXISTS snapshot_revision ON memory_trace TYPE int;
DEFINE FIELD IF NOT EXISTS snapshot_hash ON memory_trace TYPE string;
DEFINE FIELD IF NOT EXISTS envelope_hash ON memory_trace TYPE string;
DEFINE FIELD IF NOT EXISTS query ON memory_trace TYPE string;
-- channels/block_tokens/latency_ms:可观测度量对象(沿用 074/079 的 .* / .*.* any 惯例)
DEFINE FIELD IF NOT EXISTS channels ON memory_trace TYPE object;
DEFINE FIELD IF NOT EXISTS channels.* ON memory_trace TYPE any;
DEFINE FIELD IF NOT EXISTS selected ON memory_trace TYPE array;
DEFINE FIELD IF NOT EXISTS selected.* ON memory_trace TYPE object;
DEFINE FIELD IF NOT EXISTS selected.*.* ON memory_trace TYPE any;
DEFINE FIELD IF NOT EXISTS rejected ON memory_trace TYPE array;
DEFINE FIELD IF NOT EXISTS rejected.* ON memory_trace TYPE object;
DEFINE FIELD IF NOT EXISTS rejected.*.* ON memory_trace TYPE any;
DEFINE FIELD IF NOT EXISTS block_tokens ON memory_trace TYPE object;
DEFINE FIELD IF NOT EXISTS block_tokens.* ON memory_trace TYPE any;
DEFINE FIELD IF NOT EXISTS latency_ms ON memory_trace TYPE object;
DEFINE FIELD IF NOT EXISTS latency_ms.* ON memory_trace TYPE any;
DEFINE FIELD IF NOT EXISTS response_id ON memory_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS run_id ON memory_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON memory_trace TYPE datetime VALUE time::now() READONLY;
DEFINE INDEX IF NOT EXISTS memory_trace_id_idx ON memory_trace FIELDS trace_id UNIQUE;
DEFINE INDEX IF NOT EXISTS memory_trace_thread_idx ON memory_trace FIELDS work, thread_id, created_at;
DEFINE INDEX IF NOT EXISTS memory_trace_snapshot_idx ON memory_trace FIELDS context_session_id, snapshot_revision;
