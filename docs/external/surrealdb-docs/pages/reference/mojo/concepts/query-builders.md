---
title: "https://surrealdb.com/docs/reference/mojo/concepts/query-builders"
url: "https://surrealdb.com/docs/reference/mojo/concepts/query-builders"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/concepts/query-builders

Source: https://surrealdb.com/docs/reference/mojo/concepts/query-builders

The Mojo SDK ships a set of fluent builders that construct SurrealQL statements for you. Each builder is `Copyable` and `Movable`, so you can chain calls or pass it around, and each has a `build()` method that returns the statement as a string.

```python
var qb = client.select_builder("person")
    .fields("id, name, age")
    .where_clause("age >= 18")
    .order_by("age DESC")
    .limit(20)

var resp = client.query_select(qb)
```

`query_select()` runs a `SelectBuilder`. The generic `query_builder()` runs any builder via its `build()` output.
##  Available builders[](https://surrealdb.com/docs/reference/mojo/concepts/query-builders#available-builders)
The client exposes a factory method for each builder.  
| Builder  | Factory  | Methods  |  
| --- | --- | --- |  
| `SelectBuilder`  | `select_builder(target)`  |  `fields`, `where_clause`, `order_by`, `limit`, `start`, `fetch`  |  
| `CreateBuilder`  | `create_builder(target)`  |  `content`, `set_field`  |  
| `UpdateBuilder`  | `update_builder(target)`  |  `content`, `merge`, `patch`, `replace`, `where_clause`  |  
| `UpsertBuilder`  | `upsert_builder(target)`  |  `content`, `merge`  |  
| `DeleteBuilder`  | `delete_builder(target)`  | `where_clause`  |  
| `InsertBuilder`  | `insert_builder(table)`  |  `values`, `relation`  |  
##  Examples[](https://surrealdb.com/docs/reference/mojo/concepts/query-builders#examples)
Build and inspect a statement without running it:

```python
var qb = client.select_builder("person")
    .fields("name, age")
    .where_clause("age >= 18")
    .limit(10)

print(qb.build())  # SELECT name, age FROM person WHERE age >= 18 LIMIT 10;
```

Create a record:

```python
var cb = client.create_builder("person").content('{ "name": "Chiru" }')
var resp = client.query(cb.build())
```

Note
The older `QueryBuilder` is kept for backwards compatibility. New code should use the builders above.
