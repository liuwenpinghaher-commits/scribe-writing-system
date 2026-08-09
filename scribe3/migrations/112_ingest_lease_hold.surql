-- PR-1/2: ingest lease + hold fields on chapter (fail-soft IF NOT EXISTS)
DEFINE FIELD IF NOT EXISTS ingest_lease_owner ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS ingest_lease_until ON chapter TYPE option<float>;
DEFINE FIELD IF NOT EXISTS ingest_hold_reason ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS ingest_confirm_token ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS ingest_hold_prose_fp ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS ingest_hold_until ON chapter TYPE option<float>;
