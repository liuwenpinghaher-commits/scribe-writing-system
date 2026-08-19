-- chapter_state：章末世界快照（跨章连续性）。照 146 模板。
-- 另：角色户口补 gender；作品意图补 imagery（全书意象域）。

DEFINE TABLE IF NOT EXISTS chapter_state SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON chapter_state TYPE int;
DEFINE FIELD IF NOT EXISTS version ON chapter_state TYPE int;
DEFINE FIELD IF NOT EXISTS status ON chapter_state TYPE string;
DEFINE FIELD IF NOT EXISTS sha ON chapter_state TYPE string;
DEFINE FIELD IF NOT EXISTS playbook_version ON chapter_state TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_sha ON chapter_state TYPE option<string>;
DEFINE FIELD IF NOT EXISTS schema_name ON chapter_state TYPE option<string>;
DEFINE FIELD IF NOT EXISTS body ON chapter_state TYPE string;
DEFINE INDEX IF NOT EXISTS chapter_state_seq_ver ON chapter_state FIELDS seq, version UNIQUE;

DEFINE FIELD IF NOT EXISTS gender ON character TYPE option<string> DEFAULT '';
DEFINE FIELD IF NOT EXISTS imagery ON intent TYPE option<string> DEFAULT '';
