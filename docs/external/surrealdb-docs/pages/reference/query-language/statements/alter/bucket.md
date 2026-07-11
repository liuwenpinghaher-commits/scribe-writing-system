---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/bucket"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/bucket"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/bucket

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/bucket

Available since: v3.0.5
The `ALTER BUCKET` statement can be used to modify an existing defined [bucket](https://surrealdb.com/docs/reference/query-language/statements/define/bucket).
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/bucket#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER BUCKET [ IF EXISTS ] @name
  [ READONLY | DROP READONLY ]
  [ BACKEND @string | DROP BACKEND ]
  [ PERMISSIONS @expression ]
  [ COMMENT @string | DROP COMMENT ]
```

ALTER BUCKETIFEXISTS@nameREADONLYDROPREADONLYBACKEND@stringDROPBACKENDPERMISSIONS@expressionCOMMENT@stringDROPCOMMENT
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/alter/bucket#example-usage)

```surql
DEFINE BUCKET my_bucket BACKEND "memory";

ALTER BUCKET my_bucket COMMENT "Should we make this read-only too??";
```
