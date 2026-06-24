-- scribe3 · 022_chapter_qc.surql · 章级QC缓存(E枢纽 P29)

DEFINE FIELD IF NOT EXISTS qc_word_count ON chapter TYPE option<int>;
DEFINE FIELD IF NOT EXISTS qc_issues     ON chapter TYPE option<int>;
DEFINE FIELD IF NOT EXISTS qc_causal     ON chapter TYPE option<int>;
DEFINE FIELD IF NOT EXISTS qc_at         ON chapter TYPE option<datetime>;
