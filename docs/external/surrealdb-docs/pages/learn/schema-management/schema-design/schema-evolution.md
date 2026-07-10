---
title: "https://surrealdb.com/docs/learn/schema-management/schema-design/schema-evolution"
url: "https://surrealdb.com/docs/learn/schema-management/schema-design/schema-evolution"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/schema-management/schema-design/schema-evolution

Source: https://surrealdb.com/docs/learn/schema-management/schema-design/schema-evolution

Production databases rarely stay still, and in SurrealDB they tend to move from less to more strict over time as you become more aware of the expected behaviour of your database. Some examples of schema changes are tightening a table from schemaless to schemafull, changing permissions, or preparing an index for removal. SurrealDB's `ALTER` statement is the lever for mutating definitions in place without always rewriting a full `DEFINE` block.
When you are ready to version and apply those changes across environments (for example from CI or with reviewed rollouts), use [SurrealKit schema migration](https://surrealdb.com/docs/manage/schema-migration) — the official `.surql`-based workflow documented in the **Manage** section.
For a wholesale replacement, you can always use `DEFINE` with the `OVERWRITE` clause.
##  Tightening a table from schemaless to schemafull[](https://surrealdb.com/docs/learn/schema-management/schema-design/schema-evolution#tightening-a-table-from-schemaless-to-schemafull)
A common pattern is to start with a completely schemaless table, adding defined fields one at a time to ensure that they are present in all records of a certain table. If you are certain that no other fields should be present, you can move the entire table from `SCHEMALESS` to `SCHEMAFULL` to ensure that only defined fields are present.

```surql
DEFINE TABLE user SCHEMALESS;
DEFINE FIELD name ON TABLE user TYPE string;
CREATE user SET name = "LordofSalty";

-- Now make it schemafull so undeclared fields are rejected
ALTER TABLE user SCHEMAFULL;
```

##  Adjusting permissions without restating the whole table[](https://surrealdb.com/docs/learn/schema-management/schema-design/schema-evolution#adjusting-permissions-without-restating-the-whole-table)
`ALTER` only needs the parts you are changing. Here the table stays schemafull; only create permission moves from the default to FULL.

```surql
DEFINE TABLE user SCHEMAFULL;

ALTER TABLE user PERMISSIONS FOR create FULL;
```

##  Idempotent alterations[](https://surrealdb.com/docs/learn/schema-management/schema-design/schema-evolution#idempotent-alterations)
In scripts, `IF EXISTS` avoids failing when the resource name was never created in that environment.

```surql
ALTER TABLE IF EXISTS user SCHEMAFULL;
DEFINE TABLE IF EXISTS writer;
```

##  Where to read more[](https://surrealdb.com/docs/learn/schema-management/schema-design/schema-evolution#where-to-read-more)
  * •
[`ALTER` overview](https://surrealdb.com/docs/reference/query-language/statements/alter/overview)
  * •
[Schema best practices](https://surrealdb.com/docs/learn/schema-management/schema-design/schema-best-practices)
  * •
[SurrealKit schema migration](https://surrealdb.com/docs/manage/schema-migration) — sync and rollout workflows for schema files
