---
title: "https://surrealdb.com/docs/reference/query-language"
url: "https://surrealdb.com/docs/reference/query-language"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language

Source: https://surrealdb.com/docs/reference/query-language

SurrealQL is SurrealDB's query language. Syntax is broadly SQL-like, with extensions for nested fields, graph edges, record IDs, and other SurrealDB-specific constructs.
For a guided introduction, see [Learn: Querying](https://surrealdb.com/docs/learn/querying).
##  Examples[](https://surrealdb.com/docs/reference/query-language#examples)
A minimal query can follow a familiar SQL shape:

```surql
SELECT name,
       metadata
FROM   user
WHERE  age >= 18; 
```

Projections can include nested objects and graph traversals:

```surql
SELECT name,
       metadata.{
          date_registered,
          last_login
       },
       ->wrote->post AS posts
FROM user
WHERE age >= 18;
```

Further detail is organised under [Statements](https://surrealdb.com/docs/reference/query-language/statements/overview) and the other sections in this reference.
