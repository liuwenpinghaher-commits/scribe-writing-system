-- 036: knows.certainty 落列(P1-c)
-- 给 knows 关系表加 certainty 字段,默认 1.0(全信),旧边自动补默认值。
DEFINE FIELD IF NOT EXISTS certainty ON knows TYPE float DEFAULT 1.0;
