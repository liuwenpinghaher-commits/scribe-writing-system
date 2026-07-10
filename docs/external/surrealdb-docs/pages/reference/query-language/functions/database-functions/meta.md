---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/meta"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/meta"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/meta

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/meta

Note
These functions are deprecated. Prefer SurrealDB's [record](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record) functions instead.
These functions can be used to retrieve specific metadata from a SurrealDB Record ID.  
| Function  | Description  |  
| --- | --- |  
| [`meta::id()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/meta#metaid)  | Extracts and returns the identifier from a SurrealDB Record ID  |  
| [`meta::tb()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/meta#metatb)  | Extracts and returns the table name from a SurrealDB Record ID  |  
##  `meta::id`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/meta#metaid)
The `meta::id` function extracts and returns the identifier from a SurrealDB Record ID.
API DEFINITION

```surql
meta::id(record) -> value
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN meta::id(person:tobie);

"tobie"
```

  

##  `meta::tb`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/meta#metatb)
The `meta::tb` function extracts and returns the table name from a SurrealDB Record ID.
API DEFINITION

```surql
meta::tb(record) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN meta::tb(person:tobie);

"person"
```

This function can also be called using the path `meta::table`.

```surql
RETURN meta::table(person:tobie);

"person"
```
