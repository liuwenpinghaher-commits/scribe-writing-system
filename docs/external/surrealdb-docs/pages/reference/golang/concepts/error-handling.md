---
title: "https://surrealdb.com/docs/reference/golang/concepts/error-handling"
url: "https://surrealdb.com/docs/reference/golang/concepts/error-handling"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/error-handling

Source: https://surrealdb.com/docs/reference/golang/concepts/error-handling

The Go SDK uses Go's standard `error` interface and the `errors.As` / `errors.Is` functions for error handling. Errors fall into three main categories: structured [server errors](https://surrealdb.com/docs/reference/golang/api/errors#servererror) from SurrealDB, per-statement [query errors](https://surrealdb.com/docs/reference/golang/api/errors#queryerror), and transport-level failures.
This page covers how to identify and handle each error type, and which errors are safe to retry.
##  API references[](https://surrealdb.com/docs/reference/golang/concepts/error-handling#api-references)  
| Error type  | Description  |  
| --- | --- |  
| [`ServerError`](https://surrealdb.com/docs/reference/golang/api/errors#servererror)  | Structured error from SurrealDB v3 with kind, details, and cause chain  |  
| [`QueryError`](https://surrealdb.com/docs/reference/golang/api/errors#queryerror)  | Per-statement query failure returned within QueryResult  |  
| [`RPCError`](https://surrealdb.com/docs/reference/golang/api/errors#rpcerror)  | RPC error (deprecated in favor of ServerError on v3)  |  
##  Handling structured server errors[](https://surrealdb.com/docs/reference/golang/concepts/error-handling#handling-structured-server-errors)
SurrealDB v3 returns structured errors with a `Kind`, `Message`, `Details`, and an optional `Cause` chain. Use `errors.As` to extract a [`ServerError`](https://surrealdb.com/docs/reference/golang/api/errors#servererror):

```go
import "errors"

_, err := surrealdb.Select[Person](ctx, db, models.NewRecordID("persons", "missing"))
if err != nil {
	var se *surrealdb.ServerError
	if errors.As(err, &se) {
		fmt.Println("Kind:", se.Kind)
		fmt.Println("Message:", se.Message)
		if se.Cause != nil {
			fmt.Println("Caused by:", se.Cause.Message)
		}
	}
}
```

The `Cause` field forms a linked list. Use `errors.Unwrap` or iterate through `Cause` to traverse the full chain.
##  Handling query errors[](https://surrealdb.com/docs/reference/golang/concepts/error-handling#handling-query-errors)
When using `Query`, individual statements can fail without causing the entire call to error. Each [`QueryResult`](https://surrealdb.com/docs/reference/golang/api/types#queryresult) has an `Error` field that contains a [`QueryError`](https://surrealdb.com/docs/reference/golang/api/errors#queryerror) if that statement failed.

```go
results, err := surrealdb.Query[[]any](ctx, db,
	"SELECT * FROM persons; INVALID STATEMENT;",
	nil,
)

for i, qr := range *results {
	if qr.Error != nil {
		fmt.Printf("Statement %d failed: %s\n", i, qr.Error.Message)
	}
}
```

The `err` returned by `Query` is a joined error containing all per-statement `QueryError` values. You can check it directly:

```go
if errors.Is(err, &surrealdb.QueryError{}) {
	fmt.Println("One or more statements failed")
}
```

##  Handling sentinel errors[](https://surrealdb.com/docs/reference/golang/concepts/error-handling#handling-sentinel-errors)
The SDK defines several [sentinel errors](https://surrealdb.com/docs/reference/golang/api/errors#sentinel-errors) for common failure conditions:  
| Error  | Description  |  
| --- | --- |  
| `constants.ErrSessionsNotSupported`  | Sessions require a WebSocket connection  |  
| `constants.ErrTransactionsNotSupported`  | Interactive transactions require a WebSocket connection  |  
| `constants.ErrSessionClosed`  | The session has been detached  |  
| `constants.ErrTransactionClosed`  | The transaction has been committed or canceled  |  
Check for these using `errors.Is`:

```go
import "github.com/surrealdb/surrealdb.go/pkg/constants"

if errors.Is(err, constants.ErrSessionClosed) {
	fmt.Println("Session was already detached")
}
```

##  Deciding whether to retry[](https://surrealdb.com/docs/reference/golang/concepts/error-handling#deciding-whether-to-retry)
Not all errors are safe to retry. Use the following guidelines:  
| Error type  | Retriable  | Reason  |  
| --- | --- | --- |  
| `ServerError`  | Sometimes  | Depends on the error kind; network-related kinds may be retriable  |  
| `QueryError`  | No  | The query itself is invalid or caused a logical error  |  
|  `RPCError` (from `Query`)  | Yes  | The RPC failed before the query was processed  |  
|  `RPCError` (from other methods)  | No  | May indicate a data-level error (e.g., duplicate record)  |  
| Unmarshal errors  | No  | Type mismatch between expected and actual response  |  
##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/error-handling#learn-more)
  * •
[Errors API reference](https://surrealdb.com/docs/reference/golang/api/errors) for complete error type definitions
  * •
[Executing queries](https://surrealdb.com/docs/reference/golang/concepts/executing-queries) for query-level error handling
  * •
[Types reference](https://surrealdb.com/docs/reference/golang/api/types) for `QueryResult` and `QueryError` definitions
