-- scribe3 · 023_preagg_view.surql · 预聚合视图(E枢纽 §3.4 方案B)
DEFINE TABLE IF NOT EXISTS word_stats AS
    SELECT
        count()                  AS chapter_count,
        math::sum(qc_word_count) AS word_count
    FROM chapter
    GROUP ALL;
