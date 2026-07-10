---
title: "https://surrealdb.com/docs/reference/golang/concepts/query-builder"
url: "https://surrealdb.com/docs/reference/golang/concepts/query-builder"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/query-builder

Source: https://surrealdb.com/docs/reference/golang/concepts/query-builder

Warning
This feature is provided by the `contrib/surrealql` package, which is outside of the backward compatibility guarantees of the core SDK. Its API may change without following semantic versioning.
The `surrealql` query builder lets you construct SurrealQL queries programmatically using a fluent Go API. It automatically binds values as parameters to prevent injection, and produces a query string and variables map that you can pass directly to [`surrealdb.Query`](https://surrealdb.com/docs/reference/golang/api/core/db#query).
##  Installing the package[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#installing-the-package)
The query builder is part of the SDK module. Import it alongside the main package:

```go
import "github.com/surrealdb/surrealdb.go/contrib/surrealql"
```

##  Building and executing queries[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#building-and-executing-queries)
Every query builder type has a `.Build()` method that returns a SurrealQL string and a `map[string]any` of parameters. Pass these directly to [`surrealdb.Query`](https://surrealdb.com/docs/reference/golang/api/core/db#query):

```go
q := surrealql.Select("users").Where("age > ?", 18).Limit(10)
sql, vars := q.Build()

results, err := surrealdb.Query[[]User](ctx, db, sql, vars)
```

##  Selecting records[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#selecting-records)
Use `Select` to start a `SELECT` query. Chain `.Fields()`, `.Where()`, `.OrderBy()`, `.Limit()`, and other methods to refine it.

```go
surrealql.Select("users")
// SELECT * FROM users

surrealql.Select("users").Fields("name", "email").Where("active = ?", true)
// SELECT name, email FROM users WHERE active = $param_1

surrealql.Select("users").
	Field(surrealql.Expr("count()").As("total")).
	GroupBy("department")
// SELECT count() AS total FROM users GROUP BY department
```

`SelectOnly` produces a `SELECT ... ONLY` query that returns a single record instead of an array. You can pass [`RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id) and [`Table`](https://surrealdb.com/docs/reference/golang/api/values/table) values directly as targets:

```go
surrealql.SelectOnly(models.NewRecordID("users", "tobie")).Fields("name")
// SELECT ONLY name FROM $id_1
```

###  Filtering with Where[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#filtering-with-where)
The `.Where()` method accepts a condition string with `?` placeholders. Values are bound as parameters automatically.

```go
surrealql.Select("products").
	Where("price < ?", 100).
	Where("category = ?", "electronics")
// SELECT * FROM products WHERE price < $param_1 AND category = $param_2
```

###  Ordering and pagination[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#ordering-and-pagination)

```go
surrealql.Select("users").
	OrderByDesc("created_at").
	Limit(20).
	Start(40)
// SELECT * FROM users ORDER BY created_at DESC LIMIT 20 START 40
```

##  Creating records[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#creating-records)
Use `Create` to build a `CREATE` query. Set fields with `.Set()` or provide the entire content with `.Content()`.

```go
surrealql.Create("users").
	Set("name", "Alice").
	Set("age", 30)
// CREATE users SET name = $set_1, age = $set_2

surrealql.Create("users").Content(map[string]any{
	"name": "Alice",
	"age":  30,
})
// CREATE users CONTENT $content_1
```

`CreateOnly` produces a `CREATE ... ONLY` query:

```go
surrealql.CreateOnly("users").Set("name", "Alice").ReturnNone()
// CREATE ONLY users SET name = $set_1 RETURN NONE
```

##  Updating records[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#updating-records)
Use `Update` to build an `UPDATE` query with `.Set()` and `.Where()`:

```go
surrealql.Update("users").
	Set("active", false).
	Where("last_login < ?", "2025-01-01")
// UPDATE users SET active = $set_1 WHERE last_login < $param_1
```

Compound operations are supported in `.Set()`:

```go
surrealql.Update("products").Set("stock -= ?", 1).Where("id = ?", "products:apple")
// UPDATE products SET stock -= $set_1 WHERE id = $param_1
```

##  Upserting records[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#upserting-records)
Use `Upsert` to build an `UPSERT` query. This creates a record if it does not exist, or updates it if it does. After calling `Upsert`, choose one of the data modes: `.Set()`, `.Content()`, `.Merge()`, `.Patch()`, or `.Replace()`.

```go
surrealql.Upsert("users:tobie").Set("name", "Tobie").Set("active", true)
// UPSERT users:tobie SET name = $set_1, active = $set_2

surrealql.Upsert("users:tobie").Content(map[string]any{
	"name": "Tobie",
	"active": true,
})
// UPSERT users:tobie CONTENT $upsert_content_1

surrealql.Upsert("users:tobie").Merge(map[string]any{"active": false})
// UPSERT users:tobie MERGE $upsert_merge_1
```

Upsert queries also support `.Where()`, `.Timeout()`, `.Parallel()`, and `.Explain()`.
##  Deleting records[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#deleting-records)
Use `Delete` to build a `DELETE` query:

```go
surrealql.Delete("sessions").Where("expired_at < ?", "2025-01-01")
// DELETE sessions WHERE expired_at < $param_1
```

##  Inserting records[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#inserting-records)
Use `Insert` to build an `INSERT` query. This is useful for bulk inserts and inserting from subqueries.

```go
surrealql.Insert("users").Value(map[string]any{
	"name": "Alice",
	"age":  30,
})
// INSERT INTO users $insert_data_1

surrealql.Insert("users").
	Fields("name", "age").
	Values("Alice", 30).
	Values("Bob", 25)
// INSERT INTO users (name, age) VALUES ($insert_0_0_1, $insert_0_1_1), ($insert_1_0_1, $insert_1_1_1)

surrealql.Insert("users").Relation().Value(map[string]any{
	"in":  "users:tobie",
	"out": "posts:first",
})
// INSERT RELATION INTO users $insert_data_1
```

Handle conflicts with `ON DUPLICATE KEY UPDATE`:

```go
surrealql.Insert("products").
	Fields("id", "stock").
	Values("products:apple", 10).
	OnDuplicateKeyUpdateRaw("stock += $input.stock")
```

##  Creating relations[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#creating-relations)
Use `Relate` to build a `RELATE` query between two records:

```go
surrealql.Relate(
	models.NewRecordID("users", "tobie"),
	"wrote",
	models.NewRecordID("posts", "first"),
).Set("created_at", "2026-01-01")
```

##  Using expressions[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#using-expressions)
The `Expr` function creates parameterised expressions with `?` placeholders. Use it for function calls, graph traversals, or any expression that needs value binding.

```go
surrealql.Select("users").
	Field(surrealql.Expr("math::mean([?, ?, ?])", 1, 2, 3).As("avg"))
// SELECT math::mean([$param_1, $param_2, $param_3]) AS avg FROM users

surrealql.Select(surrealql.Expr("?->knows->users", models.NewRecordID("users", "tobie")))
// SELECT * FROM $from_param_1->knows->users
```

##  Return clauses[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#return-clauses)
All mutation queries support return clauses:

```go
surrealql.Create("users").Set("name", "Alice").ReturnNone()
// CREATE users SET name = $set_1 RETURN NONE

surrealql.Update("users").Set("active", true).Return("AFTER")
// UPDATE users SET active = $set_1 RETURN AFTER

surrealql.Delete("sessions").ReturnBefore()
// DELETE sessions RETURN BEFORE
```

##  Building text-based transactions[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#building-text-based-transactions)
The query builder can compose text-based transactions with `Begin`:

```go
q := surrealql.Begin().
	Then(surrealql.Create("users").Set("name", "Alice")).
	Then(surrealql.Create("users").Set("name", "Bob"))

sql, vars := q.Build()
// BEGIN TRANSACTION; CREATE users SET name = $set_1; CREATE users SET name = $set_2; COMMIT TRANSACTION;
```

Note
Text-based transactions built with the query builder are different from [interactive transactions](https://surrealdb.com/docs/reference/golang/concepts/transactions). Text-based transactions execute all statements atomically in a single RPC call. Interactive transactions allow inspecting results between statements.
##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/query-builder#learn-more)
  * •
[Executing queries](https://surrealdb.com/docs/reference/golang/concepts/executing-queries) for running the built queries with `surrealdb.Query`
  * •
[Data manipulation](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation) for the typed CRUD functions as an alternative to the query builder
  * •
[SurrealQL statements](https://surrealdb.com/docs/reference/query-language/statements/overview) for the query language reference
