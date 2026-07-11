---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/namespace"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/namespace"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/namespace

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/namespace

Available since: v3.0.0
The `ALTER NAMESPACE` statement can be used to modify the namespace. `ALTER NAMESPACE` is used on the current namespace, which is why a `IF EXISTS` clause does not exist.
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/namespace#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER NAMESPACE COMPACT
```

ALTER NAMESPACECOMPACT
##  COMPACT[](https://surrealdb.com/docs/reference/query-language/statements/alter/namespace#compact)
Performs storage compaction onPerforms storage compaction on the current namespace keyspace. To compact other resources, use [ALTER SYSTEM](https://surrealdb.com/docs/reference/query-language/statements/alter/system) to compact the entire datastore, [ALTER DATABASE](https://surrealdb.com/docs/reference/query-language/statements/alter/database) to compact the current database keyspace, or [ALTER TABLE](https://surrealdb.com/docs/reference/query-language/statements/alter/table) to compact a specific table keyspace.
The actual compaction used will depend on the datastore, such as RocksDB or SurrealKV.
This clause will not work with in-memory storage which has nothing persistent to compact, producing the following error:

```surql
'The storage layer does not support compaction requests.'
```

A successful compaction will return `NONE`.

```surql
ALTER NAMESPACE COMPACT;
-- NONE
```

##  See also[](https://surrealdb.com/docs/reference/query-language/statements/alter/namespace#see-also)
  * •
[`DEFINE NAMESPACE`](https://surrealdb.com/docs/reference/query-language/statements/define/namespace)
