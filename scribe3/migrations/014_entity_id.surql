-- scribe3 · 014_entity_id.surql · D命名重构 N3 第一阶段
-- 新增 entity_id 字段(与 entity 并存,双写阶段)。

DEFINE FIELD IF NOT EXISTS entity_id ON proposition TYPE string;
DEFINE INDEX IF NOT EXISTS idx_prop_entity_id ON proposition FIELDS entity_id;
