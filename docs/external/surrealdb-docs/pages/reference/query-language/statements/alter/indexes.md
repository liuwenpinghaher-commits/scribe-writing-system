---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/indexes"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/indexes"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/indexes

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/indexes

Available since: v3.0.0
The `ALTER INDEX` statement is used to alter a defined index on a table.
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER INDEX @name ON TABLE @table
    COMMENT @string |
    PREPARE REMOVE |
    DROP COMMENT
```

ALTER INDEX@nameON TABLE@tableCOMMENT@stringPREPAREREMOVEDROPCOMMENT
##  `PREPARE REMOVE` clause[](https://surrealdb.com/docs/reference/query-language/statements/alter/indexes#prepare-remove-clause)
As the name implies, an `ALTER INDEX PREPARE REMOVE` statement alters an index to prepare it for removal. This statement sets up a step in which the index has been decommissioned (prepared for removal), but not yet removed. At this point, `SELECT` queries along with the `EXPLAIN` clause to monitor query performance without the index.

```surql
-- 1. Decommission the index
ALTER INDEX my_index ON my_table PREPARE REMOVE;

-- 2. Monitor query performance and verify queries still work
SELECT ... FROM my_table EXPLAIN;

-- 3. If satisfied, permanently remove the index
REMOVE INDEX my_index ON my_table;
```

If removing the index is no longer desired, it can be restored to a useful state by using a [REBUILD INDEX](https://surrealdb.com/docs/reference/query-language/statements/rebuild) statement.

```surql
REBUILD INDEX my_index ON my_table;
```

##  See also[](https://surrealdb.com/docs/reference/query-language/statements/alter/indexes#see-also)
  * •
[`DEFINE INDEX`](https://surrealdb.com/docs/reference/query-language/statements/define/indexes)
