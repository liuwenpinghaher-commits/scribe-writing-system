-- 旧设计字段删除（prose 不动）。须在 migrate_legacy_plays 之后应用。
REMOVE FIELD IF EXISTS chapter_spine ON chapter;
REMOVE FIELD IF EXISTS beats ON chapter;
REMOVE FIELD IF EXISTS beats_meta ON chapter;
REMOVE FIELD IF EXISTS deductions ON chapter;
REMOVE FIELD IF EXISTS scene_truth ON chapter;
REMOVE FIELD IF EXISTS draft ON chapter;
REMOVE TABLE IF EXISTS design_attempt;
