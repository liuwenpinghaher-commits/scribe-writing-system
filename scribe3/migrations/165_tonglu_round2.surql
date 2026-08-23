-- 铜炉下一轮：收件箱已处理 / 候选去重哈希 / advisory 待确认补字段
DEFINE TABLE IF NOT EXISTS inbox_dismissed SCHEMALESS;
DEFINE FIELD IF NOT EXISTS item_id ON inbox_dismissed TYPE option<string>;
DEFINE FIELD IF NOT EXISTS dismissed ON inbox_dismissed TYPE option<bool>;
DEFINE INDEX IF NOT EXISTS uniq_inbox_dismissed_id ON inbox_dismissed FIELDS item_id UNIQUE;

DEFINE FIELD IF NOT EXISTS entity_hash ON canon_candidate TYPE option<string>;
DEFINE INDEX IF NOT EXISTS idx_canon_candidate_entity_hash ON canon_candidate FIELDS entity_hash;

DEFINE FIELD IF NOT EXISTS advisory_id ON advisory_pending TYPE option<string>;
DEFINE FIELD IF NOT EXISTS prose ON advisory_pending TYPE option<string>;
DEFINE FIELD IF NOT EXISTS items ON advisory_pending TYPE option<string>;
DEFINE FIELD IF NOT EXISTS marked_at ON advisory_pending TYPE option<float>;
DEFINE FIELD IF NOT EXISTS expires_at ON advisory_pending TYPE option<float>;

DEFINE FIELD IF NOT EXISTS needs_human ON motif TYPE option<bool>;
