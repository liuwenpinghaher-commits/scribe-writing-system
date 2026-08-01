-- 作者是质量裁决的高权重来源，但每次 accept/revise/reject 都必须追加、可回读、不可覆盖。
DEFINE TABLE IF NOT EXISTS quality_author_verdict SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS verdict_id ON quality_author_verdict TYPE string READONLY;
DEFINE FIELD IF NOT EXISTS job ON quality_author_verdict TYPE record<quality_job> READONLY;
DEFINE FIELD IF NOT EXISTS job_id ON quality_author_verdict TYPE string READONLY;
DEFINE FIELD IF NOT EXISTS unit ON quality_author_verdict TYPE record<chapter_version> READONLY;
DEFINE FIELD IF NOT EXISTS unit_id ON quality_author_verdict TYPE string READONLY;
DEFINE FIELD IF NOT EXISTS dimension ON quality_author_verdict TYPE string READONLY;
DEFINE FIELD IF NOT EXISTS revision ON quality_author_verdict TYPE int READONLY;
DEFINE FIELD IF NOT EXISTS decision ON quality_author_verdict TYPE string ASSERT $value IN ['accept', 'revise', 'reject'] READONLY;
DEFINE FIELD IF NOT EXISTS reason ON quality_author_verdict TYPE string READONLY;
DEFINE FIELD IF NOT EXISTS payload ON quality_author_verdict TYPE object FLEXIBLE READONLY;
DEFINE FIELD IF NOT EXISTS created_at ON quality_author_verdict TYPE datetime VALUE time::now() READONLY;
DEFINE INDEX IF NOT EXISTS quality_author_verdict_id_idx ON quality_author_verdict FIELDS verdict_id UNIQUE;
DEFINE INDEX IF NOT EXISTS quality_author_verdict_revision_idx ON quality_author_verdict FIELDS job, unit, dimension, revision UNIQUE;
