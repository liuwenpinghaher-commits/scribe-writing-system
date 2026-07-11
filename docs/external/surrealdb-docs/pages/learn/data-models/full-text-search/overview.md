---
title: "https://surrealdb.com/docs/learn/data-models/full-text-search/overview"
url: "https://surrealdb.com/docs/learn/data-models/full-text-search/overview"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/full-text-search/overview

Source: https://surrealdb.com/docs/learn/data-models/full-text-search/overview

A full-text search database is designed to index and retrieve text-based data (like articles, messages, or comments) based on tokenized and modified parts of the text itself, rather than exact, literal matches. This allows you to:
  * •
Find documents containing certain keywords.
  * •
Search for phrases or words with variants (e.g., “run,” “runs,” “running”).
  * •
Rank results by relevance, not just by literal string matches.

As a multi-model database, SurrealDB has integrated full-text search capabilities so that you can store your data and query it with advanced text search features.
Note: SurrealDB has many other built-in ways of working with text besides full-text search. For more details, see [Other ways to work with text](https://surrealdb.com/docs/learn/data-models/full-text-search/other-ways-to-work-with-text).
##  How full-text search differs from keyword matching[](https://surrealdb.com/docs/learn/data-models/full-text-search/overview#how-full-text-search-differs-from-keyword-matching)
In traditional databases, you might do something like:

```surql
SELECT * FROM articles WHERE 'fox' IN title;
```

This approach:
  * •
Doesn’t rank results by relevance; it just returns every article containing “fox.”
  * •
Ignores language variations, e.g., “Foxes,” “FoX,” or synonyms like “vixen.”
  * •
May scan an entire table, making it slower for large datasets.

Full-text search, by contrast, uses an inverted index or other specialised structures for fast lookups and can handle a variety of linguistic transformations. It can highlight results and rank them by how relevant or frequent the terms are.
##  Advantages of SurrealDB for FTS[](https://surrealdb.com/docs/learn/data-models/full-text-search/overview#advantages-of-surrealdb-for-fts)
  * •
**Unified model** : You can keep your data, relationships, and search logic in a single engine.
  * •
**Flexible schema** : SurrealDB can be schemaless, so adding new fields or text columns doesn’t require schema migrations.
  * •
**Powerful query language** : SurrealQL blends SQL-like syntax with searching syntax (the [`@@` matching operator](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#matches) for FTS queries, advanced indexing features, and so on).
  * •
**Real-time updates** : SurrealDB can handle real-time changes, so newly inserted or updated text becomes searchable quickly.

##  Implementing full-text search[](https://surrealdb.com/docs/learn/data-models/full-text-search/overview#implementing-full-text-search)
There are three steps involved in full-text search:
  * •
Defining an analyzer
  * •
Defining an index that uses the analyzer
  * •
Querying using syntax that specifically uses full-text search

The guides in this section walk through each part.
##  Where to go next[](https://surrealdb.com/docs/learn/data-models/full-text-search/overview#where-to-go-next)
  * •
[Analyzers and tokenizers](https://surrealdb.com/docs/learn/data-models/full-text-search/analyzers-and-tokenizers): `DEFINE ANALYZER`, tokenizers, filters, stemming, and `search::analyze`.
  * •
[Search indexes](https://surrealdb.com/docs/learn/data-models/full-text-search/search-indexes): `FULLTEXT ANALYZER` on a single field per index.
  * •
[Scoring and ranking](https://surrealdb.com/docs/learn/data-models/full-text-search/scoring-and-ranking): the `@@` operator, BM25, highlights, and `search::score` / `search::highlight`.
  * •
[Other ways to work with text](https://surrealdb.com/docs/learn/data-models/full-text-search/other-ways-to-work-with-text): sorting and collating text, contains, fuzzy matching, regex, and related string tools.

For reference, see [`DEFINE INDEX`](https://surrealdb.com/docs/reference/query-language/statements/define/indexes), [`DEFINE ANALYZER`](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer), and [Search functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/search).
