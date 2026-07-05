-- scribe3 · 026_record_links.surql · B枢纽 P38 RecordLink 升级
-- proposition.entity 裸 string → record<character|place>
-- 分阶段:先加新字段 entity_link(与 entity 并存),数据迁移后切换
--
-- ⚠ 疑似死(P2-15,2026-07-04):此处"数据迁移后切换"从未落地——全仓无任何写入 entity_link 的
--   代码,proposition.entity_id 仍是裸 string 真相源。store.graph_recall 读 entity_link.name 恒
--   null(回退 entity_id)。字段+索引均为半迁移遗留;保留待确认(移除需专门 down-migration)。

DEFINE FIELD IF NOT EXISTS entity_link ON proposition TYPE option<record<character | place>>;
DEFINE INDEX IF NOT EXISTS idx_prop_entity_link ON proposition FIELDS entity_link;
