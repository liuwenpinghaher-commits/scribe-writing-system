-- 150_pipeline_chain_fail_reasons.surql
-- 关链时把没过的原因写成数组。缺列时 SCHEMAFULL 会整次拒写，链停在进行中。

DEFINE FIELD IF NOT EXISTS fail_reasons ON pipeline_chain TYPE option<array> DEFAULT [];
DEFINE FIELD IF NOT EXISTS fail_reasons.* ON pipeline_chain TYPE string;
