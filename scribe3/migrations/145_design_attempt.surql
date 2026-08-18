-- 145_design_attempt.surql · 章设计整份中间稿（每次全生成留一档）
DEFINE TABLE IF NOT EXISTS design_attempt SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON design_attempt TYPE int;
DEFINE FIELD IF NOT EXISTS attempt ON design_attempt TYPE int;
DEFINE FIELD IF NOT EXISTS ok ON design_attempt TYPE bool;
DEFINE FIELD IF NOT EXISTS errors ON design_attempt TYPE string;
DEFINE FIELD IF NOT EXISTS body ON design_attempt TYPE string;
DEFINE FIELD IF NOT EXISTS created_at ON design_attempt TYPE datetime DEFAULT time::now();
DEFINE INDEX IF NOT EXISTS design_attempt_seq ON design_attempt FIELDS seq, created_at;
