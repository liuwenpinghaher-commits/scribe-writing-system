-- 质量判断可能来自不暴露供应商回执的隔离 fake/离线评价器。
-- 这类记录绝不补造请求 ID 或零 token；空值明确表示不能作为真人 TokenPlan 验收证据。
DEFINE FIELD OVERWRITE provider_request_id ON quality_judgment TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE usage ON quality_judgment TYPE option<object> FLEXIBLE READONLY;
