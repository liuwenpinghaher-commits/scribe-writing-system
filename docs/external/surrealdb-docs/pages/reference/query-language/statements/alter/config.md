---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/config"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/config"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/config

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/config

Available since: v3.0.5
The `ALTER CONFIG` statement can be used to modify an existing defined [config](https://surrealdb.com/docs/reference/query-language/statements/define/config).
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/config#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER CONFIG [ IF EXISTS ]
  ( API
      [ MIDDLEWARE @function(...), ... ]
      PERMISSIONS [ NONE | FULL | @expression ]
  | GRAPHQL
      TABLES [ AUTO | NONE | INCLUDE @table, ... | EXCLUDE @table, ... ]
      FUNCTIONS [ AUTO | NONE | INCLUDE @function, ... | EXCLUDE @function, ... ]
      [ DEPTH @integer ]
      [ COMPLEXITY @integer ]
      [ INTROSPECTION NONE ]
  | DEFAULT
      NAMESPACE @namespace
      DATABASE @database
  )
  [ COMMENT @string | DROP COMMENT ]
```

ALTER CONFIGIFEXISTSAPIMIDDLEWARE@function(...),@function(...)PERMISSIONSNONEFULL@expressionGRAPHQLTABLESAUTONONEINCLUDE@table,@tableEXCLUDE@table,@tableFUNCTIONSAUTONONEINCLUDE@function,@functionEXCLUDE@function,@functionDEPTH@integerCOMPLEXITY@integerINTROSPECTIONNONEDEFAULTNAMESPACE@namespaceDATABASE@databaseCOMMENT@stringDROPCOMMENT
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/alter/config#example-usage)

```surql
DEFINE CONFIG GRAPHQL TABLES AUTO FUNCTIONS AUTO;

ALTER CONFIG GRAPHQL FUNCTIONS NONE;
```
