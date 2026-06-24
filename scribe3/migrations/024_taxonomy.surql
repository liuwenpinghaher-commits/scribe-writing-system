-- scribe3 · 024_taxonomy.surql · D枢纽 taxonomy(事件大类枚举 + 自由子类型)
DEFINE FIELD IF NOT EXISTS event_category ON event TYPE option<string>
    ASSERT $value IN ['conflict', 'turning_point', 'daily', 'revelation', 'loss'] OR $value IS NONE;
DEFINE FIELD IF NOT EXISTS event_subtype ON event TYPE option<string>;
DEFINE INDEX IF NOT EXISTS idx_event_category ON event FIELDS event_category;
