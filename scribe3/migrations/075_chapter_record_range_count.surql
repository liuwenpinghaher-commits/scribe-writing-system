-- scribe3 · 075_chapter_record_range_count.surql · 章节计数快路
DEFINE INDEX IF NOT EXISTS idx_chapter_count ON chapter COUNT;
DEFINE INDEX IF NOT EXISTS idx_chapter_active_count ON chapter COUNT
    WHERE archived = NONE OR archived != true;
