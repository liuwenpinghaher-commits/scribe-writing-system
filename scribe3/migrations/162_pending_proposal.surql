DEFINE TABLE IF NOT EXISTS pending_proposal SCHEMALESS;
DEFINE FIELD IF NOT EXISTS pid ON pending_proposal TYPE string;
DEFINE FIELD IF NOT EXISTS status ON pending_proposal TYPE option<string>;
DEFINE FIELD IF NOT EXISTS payload ON pending_proposal TYPE option<string>;
DEFINE INDEX IF NOT EXISTS uniq_pending_proposal_pid ON pending_proposal FIELDS pid UNIQUE;
