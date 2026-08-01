-- 离线/测试评价器可以验证质量判断逻辑，但没有真实供应商回执。
-- 供应商身份为空必须可持久化，避免把配置意图伪造为 TokenPlan 调用证据。
DEFINE FIELD OVERWRITE provider ON quality_judgment TYPE option<string> READONLY;
DEFINE FIELD OVERWRITE model ON quality_judgment TYPE option<string> READONLY;
