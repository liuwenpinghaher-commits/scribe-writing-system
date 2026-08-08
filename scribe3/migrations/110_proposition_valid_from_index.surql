-- 110: proposition 时间门字段索引（限知后过滤 / 列表按章）
-- semantic_recall 仍为 KNN 后过滤；本索引利于 WHERE valid_from / 范围扫描类查询。
DEFINE INDEX IF NOT EXISTS idx_prop_valid_from ON proposition FIELDS valid_from;
