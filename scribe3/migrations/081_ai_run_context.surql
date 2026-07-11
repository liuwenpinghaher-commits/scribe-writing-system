-- scribe3 · 081_ai_run_context.surql · Task 13:Runs 链回作品级主编线程 + 发起时上下文快照
-- 迁移只增不改铁律(store.apply_schema 按 f.stem 去重):074 已 apply,改 074 无效,
-- 故本任务的八字段以 DEFINE FIELD IF NOT EXISTS 追加到既有 ai_run_trace(SCHEMAFULL)。
-- 用途:审批前重校验"发起时的上下文快照",拦截"旧 run 拿着过期焦点写入当前章"。
DEFINE FIELD IF NOT EXISTS parent_thread_id ON ai_run_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS context_session_id ON ai_run_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS origin_context_revision ON ai_run_trace TYPE option<int>;
DEFINE FIELD IF NOT EXISTS origin_context_hash ON ai_run_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS envelope_hash ON ai_run_trace TYPE option<string>;
DEFINE FIELD IF NOT EXISTS focus ON ai_run_trace TYPE option<object>;
DEFINE FIELD IF NOT EXISTS focus.* ON ai_run_trace TYPE any;
DEFINE FIELD IF NOT EXISTS completion_context_revision ON ai_run_trace TYPE option<int>;
DEFINE FIELD IF NOT EXISTS write_effects ON ai_run_trace TYPE array DEFAULT [];
DEFINE FIELD IF NOT EXISTS write_effects.* ON ai_run_trace TYPE object;
DEFINE FIELD IF NOT EXISTS write_effects.*.* ON ai_run_trace TYPE any;
