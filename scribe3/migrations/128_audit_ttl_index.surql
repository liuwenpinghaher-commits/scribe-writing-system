-- GAP-3: audit_event 索引 + 查询辅助（TTL 由 agent_crons / purge API 执行）
DEFINE INDEX IF NOT EXISTS audit_event_at ON audit_event FIELDS at;
DEFINE INDEX IF NOT EXISTS audit_event_kind ON audit_event FIELDS kind;
DEFINE INDEX IF NOT EXISTS audit_event_source ON audit_event FIELDS source_table;
