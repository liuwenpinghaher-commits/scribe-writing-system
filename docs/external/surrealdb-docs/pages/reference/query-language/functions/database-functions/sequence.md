---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/sequence"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/sequence"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/sequence

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/sequence

Available since: v3.0.0
These functions can be used to work with [sequences](https://surrealdb.com/docs/reference/query-language/statements/define/sequence).  
| Function  | Description  |  
| --- | --- |  
| [`sequence::next()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sequence#sequencenext)  | Returns the next value in a sequence.  |  
##  `sequence::next`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sequence#sequencenext)
The `sequence::next` function returns the next value in a sequence.
API DEFINITION

```surql
sequence::next($seq_name: string) -> int
```

```surql
DEFINE SEQUENCE mySeq2 BATCH 1000 START 100 TIMEOUT 5s;
sequence::nextval('mySeq2');

-- 100
```
