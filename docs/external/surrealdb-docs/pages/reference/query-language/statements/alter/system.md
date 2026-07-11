---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/system"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/system"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/system

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/system

Available since: v3.0.0
The `ALTER SYSTEM` statement is used to alter the entire datastore. It can be used to compact the system, or to set or drop a systemwide query timeout.
This statement is the only `ALTER` statement that does not have a corresponding `DEFINE` statement.
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/system#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER SYSTEM 
    COMPACT |
    QUERY_TIMEOUT |
    DROP QUERY_TIMEOUT
```

ALTER SYSTEMCOMPACTQUERY_TIMEOUT@durationDROP QUERY_TIMEOUT
##  `QUERY_TIMEOUT` clause[](https://surrealdb.com/docs/reference/query-language/statements/alter/system#query_timeout-clause)
A query timeout can be set for the system as a whole. The minimum possible timeout is one millisecond, below which the value will be set as `NONE`.

```surql
ALTER SYSTEM QUERY_TIMEOUT 100ns;
INFO FOR ROOT.config;
```

Output

```surql
{ QUERY_TIMEOUT: NONE }
```

Any value above `1ms` will set the timeout, beyond which no query that takes any longer than this will succeed.

```surql
ALTER SYSTEM QUERY_TIMEOUT 1ms;
FOR $_ IN 0..1000 {
    FOR $_ IN 0..1000 {
        CREATE |person:1000|;
    }
};

-- 'The query was not executed because it exceeded the timeout: 1ms'
```

##  COMPACT clause[](https://surrealdb.com/docs/reference/query-language/statements/alter/system#compact-clause)
Compacts the entire datastore. To compact other resources, use [ALTER NAMESPACE](https://surrealdb.com/docs/reference/query-language/statements/alter/namespace) to compact the current namespace keyspace, [ALTER DATABASE](https://surrealdb.com/docs/reference/query-language/statements/alter/database) to compact the current database keyspace, or [ALTER TABLE](https://surrealdb.com/docs/reference/query-language/statements/alter/table) to compact a specific table keyspace.
The actual compaction used will depend on the datastore, such as RocksDB or SurrealKV.
This clause will not work with in-memory storage which has nothing persistent to compact, producing the following error:

```surql
'The storage layer does not support compaction requests.'
```

A successful compaction will return `NONE`.

```surql
ALTER SYSTEM COMPACT;
-- NONE
```
