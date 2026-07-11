---
title: "https://surrealdb.com/docs/learn/data-models/full-text-search/search-indexes"
url: "https://surrealdb.com/docs/learn/data-models/full-text-search/search-indexes"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/full-text-search/search-indexes

Source: https://surrealdb.com/docs/learn/data-models/full-text-search/search-indexes

##  Defining an index that uses an analyzer[](https://surrealdb.com/docs/learn/data-models/full-text-search/search-indexes#defining-an-index-that-uses-an-analyzer)
Once a search analyzer is defined, it can be applied to the fields of a table to make them searchable by [defining an index](https://surrealdb.com/docs/reference/query-language/statements/define/indexes#full-text-search-index) that uses the `FULLTEXT ANALYZER` clause.

```surql
DEFINE ANALYZER my_analyzer
  TOKENIZERS class
  FILTERS lowercase, ascii;

DEFINE INDEX body_index 
  ON TABLE article
  FIELDS body
  FULLTEXT ANALYZER my_analyzer;

DEFINE INDEX title_index
  ON TABLE article
  FIELDS title 
  FULLTEXT ANALYZER my_analyzer;
```

An index can only be defined on a single field (column).

```surql
DEFINE ANALYZER my_analyzer
  TOKENIZERS class
  FILTERS lowercase, ascii;

DEFINE INDEX body_index 
  ON TABLE article 
  FIELDS body, title 
  FULLTEXT ANALYZER my_analyzer;
```

Output

```surql
'Parse error: Expected one column, found 2
 --> [5:55]
  |
5 | ...LDS body, title FULLTEXT ANALYZER my_analyzer;
  |              ^^^^^
'
```

For querying with `@@`, BM25, and highlights, continue to [Scoring and ranking](https://surrealdb.com/docs/learn/data-models/full-text-search/scoring-and-ranking).
