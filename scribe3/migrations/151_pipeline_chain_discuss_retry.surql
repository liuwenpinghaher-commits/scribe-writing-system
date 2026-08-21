-- 151: 闲聊链路允许 kind=discuss；重发链记下 retry_of（上一链 id）。

DEFINE FIELD OVERWRITE kind ON pipeline_chain TYPE string
  ASSERT $value IN ['write', 'save', 'claim', 'discuss'];

DEFINE FIELD IF NOT EXISTS retry_of ON pipeline_chain TYPE option<string>;
DEFINE INDEX IF NOT EXISTS pipeline_chain_retry_idx ON pipeline_chain FIELDS retry_of;
