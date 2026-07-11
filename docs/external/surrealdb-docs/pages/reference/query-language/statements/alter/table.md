---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/table"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/table"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/table

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/table

The `ALTER TABLE` statement is used to alter a defined table.
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER TABLE [
	[ IF EXISTS ] @name
		[ DROP COMMENT ]
        [ DROP CHANGEFEED ]
        [ COMPACT ]
		[ SCHEMAFULL | SCHEMALESS ]
		[ PERMISSIONS [ NONE | FULL
			| FOR select @expression
			| FOR create @expression
			| FOR update @expression
			| FOR delete @expression
		] ]
    [ CHANGEFEED @duration ]
    [ COMMENT @string ] 
    [ CHANGEFEED ]
]
```

ALTER TABLEIFEXISTS@tableDROPCOMMENTCHANGEFEEDCOMPACTTYPEANYNORMALRELATIONINFROM@tableOUTTO@tableENFORCEDVALUE@valueASSERT@expressionDEFAULTALWAYS@expressionPERMISSIONSNONEFULLWHERE@conditionCOMMENT@string
##  COMPACT[](https://surrealdb.com/docs/reference/query-language/statements/alter/table#compact)
Available since: v3.0.0
Performs storage compaction on a specific table keyspace. To compact other resources, use [ALTER SYSTEM](https://surrealdb.com/docs/reference/query-language/statements/alter/system) to compact the entire datastore, [ALTER NAMESPACE](https://surrealdb.com/docs/reference/query-language/statements/alter/namespace) to compact the current namespace keyspace, or [ALTER DATABASE](https://surrealdb.com/docs/reference/query-language/statements/alter/database) to compact the current database keyspace.
The actual compaction used will depend on the datastore, such as RocksDB or SurrealKV.
This clause will not work with in-memory storage which has nothing persistent to compact, producing the following error:

```surql
'The storage layer does not support compaction requests.'
```

A successful compaction will return `NONE`.

```surql
ALTER TABLE user COMPACT;
-- NONE
```

##  See also[](https://surrealdb.com/docs/reference/query-language/statements/alter/table#see-also)
  * •
[`DEFINE TABLE`](https://surrealdb.com/docs/reference/query-language/statements/define/table)
