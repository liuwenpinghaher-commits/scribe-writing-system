---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/database"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/database"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/database

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/database

Available since: v3.0.0
The `ALTER DATABASE` statement can be used to modify the database. `ALTER DATABASE` is used on the current database, which is why a `IF EXISTS` clause does not exist.
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/database#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER DATABASE COMPACT
```

ALTER DATABASECOMPACT
##  COMPACT[](https://surrealdb.com/docs/reference/query-language/statements/alter/database#compact)
Performs storage compaction on the current database keyspace. To compact other resources, use [ALTER SYSTEM](https://surrealdb.com/docs/reference/query-language/statements/alter/system) to compact the entire datastore, [ALTER NAMESPACE](https://surrealdb.com/docs/reference/query-language/statements/alter/namespace) to compact the current namespace keyspace, or [ALTER TABLE](https://surrealdb.com/docs/reference/query-language/statements/alter/table) to compact a specific table keyspace.
The actual compaction used will depend on the datastore, such as RocksDB or SurrealKV.
This clause will not work with in-memory storage which has nothing persistent to compact, producing the following error:

```surql
'The storage layer does not support compaction requests.'
```

A successful compaction will return `NONE`.

```surql
ALTER DATABASE COMPACT;
-- NONE
```

##  See also[](https://surrealdb.com/docs/reference/query-language/statements/alter/database#see-also)
  * •
[`DEFINE DATABASE`](https://surrealdb.com/docs/reference/query-language/statements/define/database)
