-- chapter_review: deep-review snapshot side table (M4a / KD-19)
-- prose_fp = sha256(utf-8)[:16] matching chapter_analysis._prose_fp
DEFINE TABLE IF NOT EXISTS chapter_review SCHEMALESS;
DEFINE FIELD IF NOT EXISTS work ON chapter_review TYPE option<string>;
DEFINE FIELD IF NOT EXISTS seq ON chapter_review TYPE option<int>;
DEFINE FIELD IF NOT EXISTS prose_fp ON chapter_review TYPE option<string>;
DEFINE FIELD IF NOT EXISTS mode ON chapter_review TYPE option<string>;
DEFINE FIELD IF NOT EXISTS issues_json ON chapter_review TYPE option<array>;
DEFINE FIELD IF NOT EXISTS coverage ON chapter_review TYPE option<object>;
DEFINE FIELD IF NOT EXISTS degraded ON chapter_review TYPE option<array>;
DEFINE FIELD IF NOT EXISTS model_id ON chapter_review TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON chapter_review TYPE option<datetime>;
DEFINE INDEX IF NOT EXISTS idx_chapter_review_work_seq ON chapter_review FIELDS work, seq;
