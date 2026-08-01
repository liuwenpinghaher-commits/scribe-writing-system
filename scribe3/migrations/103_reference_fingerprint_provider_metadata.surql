-- 参考技法指纹的模型来源仅能来自实际 TokenPlan/Qwen 响应；NULL 明确表示旧记录或离线测试。
DEFINE FIELD IF NOT EXISTS provider ON reference_fingerprint TYPE option<string> READONLY;
DEFINE FIELD IF NOT EXISTS model ON reference_fingerprint TYPE option<string> READONLY;
DEFINE FIELD IF NOT EXISTS provider_request_id ON reference_fingerprint TYPE option<string> READONLY;
DEFINE FIELD IF NOT EXISTS usage ON reference_fingerprint TYPE option<object> FLEXIBLE READONLY;
