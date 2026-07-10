---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/bytes"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/bytes"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/bytes

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/bytes

These functions can be used when working with bytes in SurrealQL.  
| Function  | Description  |  
| --- | --- |  
| [`bytes::len()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/bytes#byteslen)  | Gives the length in bytes  |  
##  `bytes::len`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/bytes#byteslen)
The `bytes::len` function returns the length in bytes of a `bytes` value.
API DEFINITION

```surql
bytes::len(bytes) -> int
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN [
    bytes::len(<bytes>"Simple ASCII string"),
    bytes::len(<bytes>"οὐ γὰρ δυνατόν ἐστιν ἔτι καθεύδειν"),
    bytes::len(<bytes>"청춘예찬 靑春禮讚")
];
```

Output

```surql
[ 19, 67, 25 ]
```
