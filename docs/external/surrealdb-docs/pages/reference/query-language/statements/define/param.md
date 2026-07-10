---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/param"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/param"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/param

Source: https://surrealdb.com/docs/reference/query-language/statements/define/param

The `DEFINE PARAM` statement allows you to define global (database-wide) parameters that are available to every client.
##  Requirements[](https://surrealdb.com/docs/reference/query-language/statements/define/param#requirements)
  * •
You must be authenticated as a root owner or editor, namespace owner or editor, or database owner or editor before you can use the `DEFINE PARAM` statement.
  * •
[You must select your namespace and database](https://surrealdb.com/docs/reference/query-language/statements/use) before you can use the `DEFINE PARAM` statement.

##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/param#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
DEFINE PARAM [ OVERWRITE | IF NOT EXISTS ] $name 
    VALUE @value
    [ COMMENT @string ]
    [ PERMISSIONS [ NONE | FULL | WHERE @condition ] ]
```

DEFINEPARAMOVERWRITEIFNOTEXISTS$@nameVALUE@valueCOMMENT@stringPERMISSIONSNONEFULLWHERE@condition
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/define/param#example-usage)
Below shows how you can create a parameter using the `DEFINE PARAM` statement.

```surql
DEFINE PARAM $endpointBase VALUE "https://dummyjson.com";
```

Then, simply use the global parameter like you would with any variable.

```surql
RETURN http::get($endpointBase + "/products");
```

##  Using `IF NOT EXISTS` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/param#using-if-not-exists-clause)
The `IF NOT EXISTS` clause can be used to define a param only if it does not already exist. You should use the `IF NOT EXISTS` clause when defining a param in SurrealDB if you want to ensure that the param is only created if it does not already exist. If the param already exists, the `DEFINE PARAM` statement will return an error.
It's particularly useful when you want to safely attempt to define a param without manually checking its existence first.
On the other hand, you should not use the `IF NOT EXISTS` clause when you want to ensure that the param definition is updated regardless of whether it already exists. In such cases, you might prefer using the `OVERWRITE` clause, which allows you to define a param and overwrite an existing one if it already exists, ensuring that the latest version of the param definition is always in use

```surql
-- Create a PARAM if it does not already exist
DEFINE PARAM IF NOT EXISTS $example VALUE 123;
```

##  Using `OVERWRITE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/param#using-overwrite-clause)
The `OVERWRITE` clause can be used to define a param and overwrite an existing one if it already exists. You should use the `OVERWRITE` clause when you want to modify an existing param definition. If the param already exists, the `DEFINE PARAM` statement will overwrite the existing param definition with the new one.

```surql
-- Create an PARAM and overwrite if it already exists
DEFINE PARAM OVERWRITE $example VALUE 123;
```
