---
title: "https://surrealdb.com/docs/learn/schema-management/computed-data/computed-fields"
url: "https://surrealdb.com/docs/learn/schema-management/computed-data/computed-fields"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/schema-management/computed-data/computed-fields

Source: https://surrealdb.com/docs/learn/schema-management/computed-data/computed-fields

Most fields are stored: you write a value and it stays on the record until you change it. A computed field differs from a normal field in that it is recalculated whenever the record is read, using an expression you attach in the schema. That makes it ideal for derived data that should always reflect a certain state instead of needing a separate update job.
##  Compared to `VALUE` and normal storage[](https://surrealdb.com/docs/learn/schema-management/computed-data/computed-fields#compared-to-value-and-normal-storage)
  * •
`VALUE` on a field sets what gets stored (often normalising input); it runs on write, not on every read in the same way a computed field does.
  * •
`COMPUTED` stores an expression, as opposed to set data.
  * •
You cannot mark `id` or nested paths (for example `meta.score`) as computed—only top-level field names.

For everything else about field definitions—types, `ASSERT`, `DEFAULT`, permissions—see [Fields and validation](https://surrealdb.com/docs/learn/schema-management/tables-and-fields/fields-and-validation) and the [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field) reference.
##  Example: always-fresh timestamp on read[](https://surrealdb.com/docs/learn/schema-management/computed-data/computed-fields#example-always-fresh-timestamp-on-read)

```surql
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD name ON user TYPE string;
DEFINE FIELD accessed_at ON user COMPUTED time::now();

CREATE user:one SET name = "Ada";
SELECT * FROM ONLY user:one;
SLEEP 1s;
SELECT * FROM ONLY user:one;
```

The second `SELECT` should show a new `accessed_at` each time, because the expression is evaluated when the record is projected.
##  Record references[](https://surrealdb.com/docs/learn/schema-management/computed-data/computed-fields#record-references)
A stored field can hold a [record link](/docs/reference/query-language/language-primitives/record-links)—a record ID that points at another record—often declared with `record  
` or `option>`, and optionally with [`REFERENCE`](/docs/reference/query-language/statements/define/field) so deletes on the target record are handled predictably. A computed field does not store a link itself (the `REFERENCE` clause applies to stored fields only), but the expression may traverse link fields already on the record and read fields from the related record.
In the example below, `book.author` stores `person:ada`, while `author_name` is derived from that link. If you change the person’s `name`, the next read of the book shows the updated label without writing back to `book`.

```surql
DEFINE TABLE person SCHEMAFULL;
DEFINE FIELD name ON person TYPE string;

DEFINE TABLE book SCHEMAFULL;
DEFINE FIELD title ON book TYPE string;
DEFINE FIELD author ON book TYPE record<person>;
DEFINE FIELD author_name ON book COMPUTED author.name;

CREATE person:ada SET name = "Ada Lovelace";
CREATE book:one SET title = "Notes", author = person:ada;

SELECT title, author_name FROM book:one;

UPDATE person:ada SET name = "Augusta Ada King";
SELECT title, author_name FROM book:one;
```

##  When to use computed fields[](https://surrealdb.com/docs/learn/schema-management/computed-data/computed-fields#when-to-use-computed-fields)
Use them when:
  * •
The result is cheap enough to evaluate on read and you want zero staleness.
  * •
The logic is purely relative to the record and its graph.

Computed fields may not always be the best option. They should not be used when:
  * •
You need the value indexed or searched like a normal field (compute into a stored field via events or application writes instead).
  * •
The expression depends on external systems.

##  See also[](https://surrealdb.com/docs/learn/schema-management/computed-data/computed-fields#see-also)
  * •
[Closures](https://surrealdb.com/docs/learn/schema-management/computed-data/closures) — small anonymous functions in expressions.
  * •
[Record links](https://surrealdb.com/docs/reference/query-language/language-primitives/record-links) — storing and traversing record IDs.
  * •
[Reactive patterns](https://surrealdb.com/docs/learn/schema-management/events-and-triggers/reactive-patterns) — when updates should flow from writes instead of reads.
