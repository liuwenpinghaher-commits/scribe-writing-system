-- scribe3 · 041_tail_cleanup.surql · P3-f 尾批清理
-- Fix2: 删 event 死 taxonomy 列(024 引入,无生产读写)
REMOVE FIELD IF EXISTS event_category ON event;
REMOVE FIELD IF EXISTS event_subtype ON event;
REMOVE INDEX IF EXISTS idx_event_category ON event;

-- Fix3: acquired_via 枚举扩展,补入 narrated(ingest.py reader_knows 写的值)
-- 010_enums.surql 中定义的旧域: ['saw','told','inferred','given','learned']
-- ingest.py L43/L69 写 acquired_via="narrated",与旧 ASSERT 冲突 → 扩展 ASSERT 以包含 narrated
DEFINE FIELD OVERWRITE acquired_via ON knows TYPE string
  ASSERT $value IN ['saw', 'told', 'inferred', 'given', 'learned', 'narrated'] DEFAULT 'given';
