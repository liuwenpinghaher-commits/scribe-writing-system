-- 同一章可以有多个独立场景的因果根；理由为空时仍按断链处理。
DEFINE FIELD IF NOT EXISTS causal_root_reason ON event TYPE option<string>;
