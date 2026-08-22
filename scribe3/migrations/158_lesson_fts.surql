-- 经验课全文检索。tokens 已在 157；此处补 BM25，范式同 070 material_fts。

DEFINE ANALYZER OVERWRITE lesson_zh TOKENIZERS blank FILTERS lowercase;
DEFINE INDEX IF NOT EXISTS lesson_fts ON lesson FIELDS tokens FULLTEXT ANALYZER lesson_zh BM25;
