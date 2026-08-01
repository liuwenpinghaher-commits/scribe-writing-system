-- 原文仅供指纹分析；生成只读取已批准的安全技法摘要与审计账本。
DEFINE FIELD IF NOT EXISTS source_text ON reference_work TYPE option<string>;

DEFINE TABLE IF NOT EXISTS reference_craft_use SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS use_id ON reference_craft_use TYPE string READONLY;
DEFINE FIELD IF NOT EXISTS work ON reference_craft_use TYPE string READONLY;
DEFINE FIELD IF NOT EXISTS chapter ON reference_craft_use TYPE int READONLY;
DEFINE FIELD IF NOT EXISTS request_id ON reference_craft_use TYPE string READONLY;
DEFINE FIELD IF NOT EXISTS manifest_id ON reference_craft_use TYPE string READONLY;
DEFINE FIELD IF NOT EXISTS reference_fingerprint_ids ON reference_craft_use TYPE array<string> READONLY;
DEFINE FIELD IF NOT EXISTS mechanism_ids ON reference_craft_use TYPE array<string> READONLY;
DEFINE FIELD IF NOT EXISTS created_at ON reference_craft_use TYPE datetime VALUE time::now() READONLY;
DEFINE INDEX IF NOT EXISTS reference_craft_use_id_idx ON reference_craft_use FIELDS use_id UNIQUE;
DEFINE INDEX IF NOT EXISTS reference_craft_use_manifest_idx ON reference_craft_use FIELDS manifest_id UNIQUE;
