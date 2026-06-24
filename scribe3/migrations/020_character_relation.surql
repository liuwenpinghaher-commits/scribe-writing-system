-- scribe3 · 020_character_relation.surql · B枢纽 角色关系图(文档04 §3.2)
DEFINE TABLE IF NOT EXISTS character_relation TYPE RELATION
    FROM character TO character SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS relation      ON character_relation TYPE string
    ASSERT $value IN ['ally','enemy','kin','master_disciple','lover'];
DEFINE FIELD IF NOT EXISTS since_chapter ON character_relation TYPE int
    ASSERT $value >= 1;
DEFINE FIELD IF NOT EXISTS note          ON character_relation TYPE option<string>;
DEFINE INDEX IF NOT EXISTS idx_charrel_since ON character_relation FIELDS since_chapter;
