-- chapter_reader_ack: dual-lamp human reader confirmation (prose_fp = sha256[:16])
DEFINE TABLE IF NOT EXISTS chapter_reader_ack SCHEMALESS;
DEFINE FIELD IF NOT EXISTS work ON chapter_reader_ack TYPE option<string>;
DEFINE FIELD IF NOT EXISTS seq ON chapter_reader_ack TYPE option<int>;
DEFINE FIELD IF NOT EXISTS prose_fp ON chapter_reader_ack TYPE option<string>;
DEFINE FIELD IF NOT EXISTS note ON chapter_reader_ack TYPE option<string>;
DEFINE FIELD IF NOT EXISTS user_id ON chapter_reader_ack TYPE option<string>;
DEFINE FIELD IF NOT EXISTS updated_at ON chapter_reader_ack TYPE option<datetime>;
DEFINE INDEX IF NOT EXISTS idx_chapter_reader_ack_work_seq ON chapter_reader_ack FIELDS work, seq;
