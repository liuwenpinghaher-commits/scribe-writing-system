-- S-6: 聚合视图（章计数 / 开放伏笔）— 只读统计
-- Surreal 3.x TABLE AS SELECT 物化视图表
DEFINE TABLE IF NOT EXISTS stats_chapter_count AS
    SELECT count() AS n FROM chapter GROUP ALL;

DEFINE TABLE IF NOT EXISTS stats_open_promises AS
    SELECT count() AS n FROM promise WHERE status = 'open' GROUP ALL;
