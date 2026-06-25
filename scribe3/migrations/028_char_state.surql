-- scribe3 · 028_char_state.surql · 角色弧光时间线(层3 动静结合)
-- 参考:门槛2-设定圣经.md §3.1.3 CharState
-- 只在叙事意义上的质变或明显量变时创建记录(不是每章都写)

DEFINE TABLE IF NOT EXISTS char_state SCHEMALESS;
DEFINE FIELD IF NOT EXISTS character_id  ON char_state TYPE string;
DEFINE FIELD IF NOT EXISTS chapter       ON char_state TYPE int;
DEFINE FIELD IF NOT EXISTS change_type   ON char_state TYPE string
    ASSERT $value IN ['ability','relation','personality','composite'];
DEFINE FIELD IF NOT EXISTS summary       ON char_state TYPE string;
DEFINE FIELD IF NOT EXISTS trigger_event ON char_state TYPE option<string>;
DEFINE FIELD IF NOT EXISTS arc_phase     ON char_state TYPE option<string>;
DEFINE FIELD IF NOT EXISTS affects_voice ON char_state TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS confidence    ON char_state TYPE string DEFAULT 'confirmed'
    ASSERT $value IN ['confirmed','inferred'];
DEFINE INDEX IF NOT EXISTS idx_charstate_char ON char_state FIELDS character_id, chapter;

-- character_relation 加 until_chapter(关系结束/变化)
DEFINE FIELD IF NOT EXISTS until_chapter ON character_relation TYPE option<int>;
