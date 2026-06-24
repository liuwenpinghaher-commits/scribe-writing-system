-- scribe3 · 026_record_links.surql · B枢纽 P38 RecordLink 升级
-- proposition.entity 裸 string → record<character|place>
-- 分阶段:先加新字段 entity_link(与 entity 并存),数据迁移后切换

DEFINE FIELD IF NOT EXISTS entity_link ON proposition TYPE option<record<character | place>>;
DEFINE INDEX IF NOT EXISTS idx_prop_entity_link ON proposition FIELDS entity_link;
