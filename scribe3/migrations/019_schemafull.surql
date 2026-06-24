-- scribe3 · 019_schemafull.surql · P32 收紧 007/008/009 SCHEMALESS → SCHEMAFULL

DEFINE TABLE OVERWRITE intent SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS reader_feeling ON intent TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS emotional_arc  ON intent TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS red_lines      ON intent TYPE string DEFAULT '';

DEFINE TABLE OVERWRITE craft_rule SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS kind    ON craft_rule TYPE string
  ASSERT $value IN ['purple_regex', 'artifact_craft', 'cover_action'];
DEFINE FIELD IF NOT EXISTS pattern ON craft_rule TYPE string;
DEFINE FIELD IF NOT EXISTS note    ON craft_rule TYPE option<string>;

DEFINE TABLE OVERWRITE voice_sample SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS character     ON voice_sample TYPE string;
DEFINE FIELD IF NOT EXISTS kind          ON voice_sample TYPE string
  ASSERT $value IN ['free', 'pressure', 'relation', 'narration'];
DEFINE FIELD IF NOT EXISTS text          ON voice_sample TYPE string;
DEFINE FIELD IF NOT EXISTS since_chapter ON voice_sample TYPE int;

DEFINE TABLE OVERWRITE voice_evolution_flag SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS character ON voice_evolution_flag TYPE string;
DEFINE FIELD IF NOT EXISTS seq       ON voice_evolution_flag TYPE int;
DEFINE FIELD IF NOT EXISTS reason    ON voice_evolution_flag TYPE string;
DEFINE FIELD IF NOT EXISTS status    ON voice_evolution_flag TYPE string
  ASSERT $value IN ['open', 'done'] DEFAULT 'open';
