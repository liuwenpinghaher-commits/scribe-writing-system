---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/comments"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/comments"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/comments

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/comments

In SurrealQL, comments can be written in a number of different ways.

```surql
/*
In SurrealQL, comments can be written as single-line
or multi-line comments, and comments can be used and
interspersed within statements.
*/

SELECT * FROM /* get all users */ user;

# There are a number of ways to use single-line comments
SELECT * FROM user;

// Alternatively using two forward-slash characters
SELECT * FROM user;

-- Another way is to use two dash characters
SELECT * FROM user;
```
