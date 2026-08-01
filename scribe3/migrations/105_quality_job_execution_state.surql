-- 质量作业的输入(快照/合同/指纹)不可变；执行状态独立可变，供断线恢复与安全重试。
DEFINE FIELD IF NOT EXISTS execution_status ON quality_job TYPE string
  ASSERT $value IN ['queued', 'running', 'completed', 'retryable_failed', 'failed'];
DEFINE FIELD IF NOT EXISTS execution_attempts ON quality_job TYPE int;
DEFINE FIELD IF NOT EXISTS execution_error_code ON quality_job TYPE option<string>;
DEFINE FIELD IF NOT EXISTS execution_error_message ON quality_job TYPE option<string>;
DEFINE FIELD IF NOT EXISTS execution_started_at ON quality_job TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS execution_finished_at ON quality_job TYPE option<datetime>;
