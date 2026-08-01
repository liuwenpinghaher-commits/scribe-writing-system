-- scribe3 · 082_ai_run_stage_policy.surql · 阶段受限 Hermes Run 的可审计权限合同
-- ai_run_trace 是 SCHEMAFULL；阶段 profile、许可工具和违规结果都必须落正典审计表。
DEFINE FIELD IF NOT EXISTS stage_policy ON ai_run_trace TYPE option<object>;
DEFINE FIELD IF NOT EXISTS stage_policy.* ON ai_run_trace TYPE any;
DEFINE FIELD IF NOT EXISTS policy_violations ON ai_run_trace TYPE array DEFAULT [];
DEFINE FIELD IF NOT EXISTS policy_violations.* ON ai_run_trace TYPE object;
DEFINE FIELD IF NOT EXISTS policy_violations.*.* ON ai_run_trace TYPE any;
-- 书级 Run 的作者点名工具合同：不替代阶段 profile，只防“文字冒充工具调用”假完成。
DEFINE FIELD IF NOT EXISTS tool_contract ON ai_run_trace TYPE option<object>;
DEFINE FIELD IF NOT EXISTS tool_contract.* ON ai_run_trace TYPE any;
