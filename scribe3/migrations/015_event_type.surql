-- scribe3 · 015_event_type.surql · D命名重构 N1
-- 新增 event_type 字段(与 etype 并存,双写阶段)。

DEFINE FIELD IF NOT EXISTS event_type ON event TYPE string;
