-- S-7: 审计 EVENT + 审计表（pilot / memory 状态联动）
DEFINE TABLE IF NOT EXISTS audit_event SCHEMALESS;
DEFINE FIELD IF NOT EXISTS kind ON audit_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_table ON audit_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_id ON audit_event TYPE option<string>;
DEFINE FIELD IF NOT EXISTS detail ON audit_event TYPE option<object>;
DEFINE FIELD IF NOT EXISTS at ON audit_event TYPE option<datetime> VALUE time::now() READONLY;

-- pilot_state 若存在则钩变更（表可能 SCHEMALESS）
DEFINE EVENT IF NOT EXISTS audit_pilot_state ON TABLE pilot_state WHEN $event = "CREATE" OR $event = "UPDATE" THEN {
    CREATE audit_event SET
        kind = 'pilot_state',
        source_table = 'pilot_state',
        source_id = string::concat('', $after.id),
        detail = { after: $after, before: $before };
};

DEFINE EVENT IF NOT EXISTS audit_memory_status ON TABLE memory_item WHEN $event = "UPDATE" AND $before.status != $after.status THEN {
    CREATE audit_event SET
        kind = 'memory_status',
        source_table = 'memory_item',
        source_id = string::concat('', $after.id),
        detail = { before_status: $before.status, after_status: $after.status };
};
