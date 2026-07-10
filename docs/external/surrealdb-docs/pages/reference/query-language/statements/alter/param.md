---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/param"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/param"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/param

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/param

Available since: v3.0.5
The `ALTER PARAM` statement can be used to modify an existing defined [param](https://surrealdb.com/docs/reference/query-language/statements/define/param).
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/param#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER PARAM [ IF EXISTS ] $name
  [ VALUE @value ]
  [ COMMENT @string | DROP COMMENT ]
  [ PERMISSIONS [ NONE | FULL | WHERE @condition ] ]
```

ALTER PARAMIFEXISTS$nameVALUE@valueCOMMENT@stringDROPCOMMENTPERMISSIONSNONEFULLWHERE@condition
Note that `ALTER PARAM` does not support `DROP VALUE` as a parameter without a value is not valid.
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/alter/param#example-usage)

```surql
DEFINE PARAM $MODE VALUE "production" COMMENT "Don't use this param yet";

ALTER PARAM $MODE DROP COMMENT;

-- Check the statement
(INFO FOR DB).params.MODE;
```

Output: comment is gone

```surql
"DEFINE PARAM $MODE VALUE 'production' PERMISSIONS FULL"
```
