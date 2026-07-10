---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/function"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/function"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/function

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/function

Available since: v3.0.5
The `ALTER FUNCTION` statement can be used to modify an existing defined [function](https://surrealdb.com/docs/reference/query-language/statements/define/function).
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/function#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER FUNCTION [ IF EXISTS ] fn::@name
  [ ( [ $argument: @type, ... ] ) ] [ -> @type | DROP RETURNS ]
  [ { @query ... } ]
  [ COMMENT @string | DROP COMMENT ]
  [ PERMISSIONS [ NONE | FULL | WHERE @condition ] ] 
```

ALTER FUNCTIONIFEXISTSfn::@name($argument:@type,$argument:@type)->@typeDROPRETURNS{@query...}COMMENT@stringDROPCOMMENTPERMISSIONSNONEFULLWHERE@condition
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/alter/function#example-usage)

```surql
-- Declare a function
DEFINE FUNCTION fn::get_message($input: any) {
    $input.message
};

-- No `message` field, returns nothing
fn::get_message("wrong input");

-- Tighten up the valid input for the function
ALTER FUNCTION fn::get_message($input: { error_code: 200, message: string } | {error_code: 404, message: string} ) {
    $input.message
};

-- Returns an error now
fn::get_message("wrong input");

-- Okay, returns 'Looks good'
fn::get_message({ error_code: 200, message: "Looks good" });
```
