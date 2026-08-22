-- 长篇情节单元。structure_mode 关时产品不读写。option 无 DEFAULT。

DEFINE TABLE IF NOT EXISTS arc_unit SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS volume_id ON arc_unit TYPE record<volume>;
DEFINE FIELD IF NOT EXISTS seq ON arc_unit TYPE int;
DEFINE FIELD IF NOT EXISTS title ON arc_unit TYPE string;
DEFINE FIELD IF NOT EXISTS goal ON arc_unit TYPE option<string>;
DEFINE FIELD IF NOT EXISTS events ON arc_unit TYPE array;
DEFINE FIELD IF NOT EXISTS chapter_from ON arc_unit TYPE option<int>;
DEFINE FIELD IF NOT EXISTS chapter_to ON arc_unit TYPE option<int>;
DEFINE FIELD IF NOT EXISTS status ON arc_unit TYPE string;
DEFINE INDEX IF NOT EXISTS arc_unit_vol_seq ON arc_unit FIELDS volume_id, seq UNIQUE;
