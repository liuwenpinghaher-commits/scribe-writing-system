-- 实体摘要命题：一实体可多条 digest，用 source + field_group 回指。
-- option 字段无 DEFAULT，老行天然 NONE。

DEFINE FIELD IF NOT EXISTS field_group ON proposition TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_entity ON proposition TYPE option<string>;

DEFINE INDEX IF NOT EXISTS proposition_digest_entity ON proposition FIELDS entity_id, attribute, source;
