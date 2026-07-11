---
title: "https://surrealdb.com/docs/reference/golang/concepts/executing-queries"
url: "https://surrealdb.com/docs/reference/golang/concepts/executing-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/executing-queries

Source: https://surrealdb.com/docs/reference/golang/concepts/executing-queries

The Go SDK provides two ways to execute SurrealQL queries: [`Query`](https://surrealdb.com/docs/reference/golang/api/core/db#query) for typed, parameterised queries and [`QueryRaw`](https://surrealdb.com/docs/reference/golang/api/core/db#queryraw) for composing multiple statements with per-statement results. Both are generic functions that work with [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db), [`*Session`](https://surrealdb.com/docs/reference/golang/api/core/session), and [`*Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction).
This page covers running queries, parameterising them, handling multi-statement results, and managing connection-scoped variables.
##  API references[](https://surrealdb.com/docs/reference/golang/concepts/executing-queries#api-references)  
| Function  | Description  |  
| --- | --- |  
| [`surrealdb.Query[T](ctx, s, sql, vars)`](https://surrealdb.com/docs/reference/golang/api/core/db#query)  | Executes a SurrealQL query with typed results  |  
| [`surrealdb.QueryRaw(ctx, s, queries)`](https://surrealdb.com/docs/reference/golang/api/core/db#queryraw)  | Executes a batch of query statements with per-statement results  |  
| [`db.Let(ctx, key, val)`](https://surrealdb.com/docs/reference/golang/api/core/db#let)  | Defines a variable on the connection for use in queries  |  
| [`db.Unset(ctx, key)`](https://surrealdb.com/docs/reference/golang/api/core/db#unset)  | Removes a previously defined connection variable  |  
##  Running a query[](https://surrealdb.com/docs/reference/golang/concepts/executing-queries#running-a-query)
The [`Query`](https://surrealdb.com/docs/reference/golang/api/core/db#query) function executes a SurrealQL string and returns typed results. The first type parameter specifies the expected result type. The second parameter `s` can be a [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db), [`*Session`](https://surrealdb.com/docs/reference/golang/api/core/session), or [`*Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction).

```go
results, err := surrealdb.Query[[]Person](ctx, db,
	"SELECT * FROM persons WHERE age > $min_age",
	map[string]any{"min_age": 18},
)
if err != nil {
	log.Fatal(err)
}

for _, qr := range *results {
	fmt.Println(qr.Status, qr.Result)
}
```

The function returns `*[]QueryResult[T]`, where each [`QueryResult`](https://surrealdb.com/docs/reference/golang/api/types#queryresult) contains the `Status`, execution `Time`, `Result`, and an optional `Error` for that statement.
##  Parameterising queries[](https://surrealdb.com/docs/reference/golang/concepts/executing-queries#parameterising-queries)
Always use parameters (`$name`) instead of string interpolation to prevent injection attacks and ensure correct CBOR encoding of [value types](https://surrealdb.com/docs/reference/golang/concepts/value-types).

```go
results, err := surrealdb.Query[[]Person](ctx, db,
	"SELECT * FROM persons WHERE name = $name AND age > $age",
	map[string]any{
		"name": "Tobie",
		"age":  25,
	},
)
```

Pass `nil` for the variables map when no parameters are needed:

```go
results, err := surrealdb.Query[[]Person](ctx, db,
	"SELECT * FROM persons",
	nil,
)
```

##  Handling multi-statement queries[](https://surrealdb.com/docs/reference/golang/concepts/executing-queries#handling-multi-statement-queries)
When a query string contains multiple statements, `Query` returns a `QueryResult` for each statement. Check the `Error` field on each result to detect per-statement failures.

```go
results, err := surrealdb.Query[[]any](ctx, db,
	"CREATE person:tobie SET name = 'Tobie'; SELECT * FROM person;",
	nil,
)

for i, qr := range *results {
	if qr.Error != nil {
		fmt.Printf("Statement %d failed: %s\n", i, qr.Error.Message)
		continue
	}
	fmt.Printf("Statement %d: %v\n", i, qr.Result)
}
```

Note
The `err` returned by `Query` is a joined error containing all per-statement [`QueryError`](https://surrealdb.com/docs/reference/golang/api/errors#queryerror) values. You can check individual statements via the `Error` field, or use `errors.Is(err, &surrealdb.QueryError{})` on the returned error.
##  Composing queries with QueryRaw[](https://surrealdb.com/docs/reference/golang/concepts/executing-queries#composing-queries-with-queryraw)
`QueryRaw` lets you compose a batch of [`QueryStmt`](https://surrealdb.com/docs/reference/golang/api/types#querystmt) objects, each with its own SQL and variables. After execution, each statement's result is available via `.GetResult()`.

```go
stmts := []surrealdb.QueryStmt{
	{SQL: "CREATE person:alice SET name = $name", Vars: map[string]any{"name": "Alice"}},
	{SQL: "SELECT * FROM person", Vars: nil},
}

if err := surrealdb.QueryRaw(ctx, db, &stmts); err != nil {
	log.Fatal(err)
}

var persons []Person
if err := stmts[1].GetResult(&persons); err != nil {
	log.Fatal(err)
}
```

##  Defining connection variables[](https://surrealdb.com/docs/reference/golang/concepts/executing-queries#defining-connection-variables)
Use `.Let()` to define a variable that persists on the connection and is available in all subsequent queries. Use `.Unset()` to remove it.

```go
if err := db.Let(ctx, "app_version", "1.0.0"); err != nil {
	log.Fatal(err)
}

results, err := surrealdb.Query[[]any](ctx, db,
	"RETURN $app_version",
	nil,
)

db.Unset(ctx, "app_version")
```

Connection variables are scoped to the connection (or [session](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions) if using sessions). They do not affect other connections. You can also build queries programmatically using the [query builder](https://surrealdb.com/docs/reference/golang/concepts/query-builder).
##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/executing-queries#learn-more)
  * •
[DB API reference](https://surrealdb.com/docs/reference/golang/api/core/db) for complete method signatures and parameters
  * •
[Data manipulation](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation) for typed CRUD operations
  * •
[Error handling](https://surrealdb.com/docs/reference/golang/concepts/error-handling) for distinguishing between query errors and transport errors
  * •
[Types reference](https://surrealdb.com/docs/reference/golang/api/types) for `QueryResult` and `QueryStmt` definitions
  * •
[SurrealQL statements](https://surrealdb.com/docs/reference/query-language/statements/overview) for the query language syntax
