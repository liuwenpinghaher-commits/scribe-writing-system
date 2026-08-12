-- GAP-5: 扩展聚合视图（字数 / 阶段分布）
DEFINE TABLE IF NOT EXISTS stats_total_words AS
    SELECT math::sum(qc_word_count) AS total_words FROM chapter GROUP ALL;

DEFINE TABLE IF NOT EXISTS stats_phase_distribution AS
    SELECT stage, count() AS n FROM chapter GROUP BY stage;
