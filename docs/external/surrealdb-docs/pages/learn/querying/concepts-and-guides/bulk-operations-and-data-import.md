---
title: "https://surrealdb.com/docs/learn/querying/concepts-and-guides/bulk-operations-and-data-import"
url: "https://surrealdb.com/docs/learn/querying/concepts-and-guides/bulk-operations-and-data-import"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/concepts-and-guides/bulk-operations-and-data-import

Source: https://surrealdb.com/docs/learn/querying/concepts-and-guides/bulk-operations-and-data-import

A bulk operation can either be one involving many records in one SurrealQL statement, or loading a file or stream from outside the database.
##  In-query bulk patterns[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/bulk-operations-and-data-import#in-query-bulk-patterns)
An [`INSERT`](https://surrealdb.com/docs/reference/query-language/statements/insert) statement is most commonly used for bulk operations. An `INSERT` can even use the output from another query as its input values:

```surql
INSERT INTO archive (SELECT * FROM readings WHERE city = 'London');
```

An `INSERT` can use an array of objects or classic SQL tuple syntax.

```surql
INSERT INTO person [
	{ id: "jaime", name: "Jaime" },
	{ id: "tobie", name: "Tobie" },
];

INSERT INTO company (name, founded)
VALUES
	('Acme Inc.', '1967-05-03'),
	('SurrealDB', '2021-09-10');
```

The `ON DUPLICATE KEY UPDATE` clause can be used to add extra logic when a unique key clashes instead of failing the operation.

```surql
INSERT INTO city (id,
  population,
  at_year) VALUES ("Calgary",
  1665000,
  2024)
ON DUPLICATE KEY UPDATE
	population = $input.population,
	at_year = $input.at_year;
```

##  Tools and HTTP endpoints[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/bulk-operations-and-data-import#tools-and-http-endpoints)
Importing data from external sources can be done through a number of methods.
  * •
**[Surreal Sync](https://github.com/surrealdb/surreal-sync/)** helps migrate from other databases and streams into SurrealDB. See the [migrations overview](https://surrealdb.com/docs/build/migrating/from-other-databases/overview) for how it fits with the rest of the import story.
  * •
**`POST /import`**is the HTTP endpoint for importing SurrealQL at volume. Imports must include an`OPTION IMPORT` line which instructs the server to skip events, live queries, query output and so on. For details, see [`POST /import`](https://surrealdb.com/docs/reference/rest-api/http-protocol#import).
  * •
**`POST /sql`**runs SurrealQL like a normal query session. Use this endpoint when you**want side effects** during a load such as events and live query behaviour. The [HTTP API](https://surrealdb.com/docs/reference/rest-api/http-protocol#sql) documents the `/sql` endpoint; the [CLI `import`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import) page describes the same trade-off for file-based imports.
  * •
**Surrealist** can import SurrealQL files and **CSV** from the Explorer view (choose fields, map to a table, and create records). See [exploring database records / import](https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records).

For large one-off file loads from the shell, the **[`surreal import`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import)**command is the usual companion to`POST /import`.
