---
title: "https://surrealdb.com/docs/reference/golang/api/core/transaction"
url: "https://surrealdb.com/docs/reference/golang/api/core/transaction"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/core/transaction

Source: https://surrealdb.com/docs/reference/golang/api/core/transaction

The `Transaction` struct represents an interactive SurrealDB transaction on a WebSocket connection. Unlike text-based transactions, interactive transactions allow executing statements one at a time and conditionally committing or canceling based on results. Transactions require SurrealDB v3+ and a WebSocket connection.
`Transaction` satisfies the [`sendable`](https://surrealdb.com/docs/reference/golang/api/types#sendable) constraint, so all generic functions like [`Query`](https://surrealdb.com/docs/reference/golang/api/core/db#query), [`Select`](https://surrealdb.com/docs/reference/golang/api/core/db#select), [`Create`](https://surrealdb.com/docs/reference/golang/api/core/db#create), etc. accept `*Transaction` directly. However, transactions do not support session state changes (authentication, namespace selection, variables) or [live queries](https://surrealdb.com/docs/reference/golang/concepts/live-queries).
**Source:** [transaction.go](https://github.com/surrealdb/surrealdb.go/blob/main/transaction.go)
* * *
##  Creating a transaction[](https://surrealdb.com/docs/reference/golang/api/core/transaction#creating-a-transaction)
###  `db.Begin()`[](https://surrealdb.com/docs/reference/golang/api/core/transaction#db-begin)
Starts a transaction on the default session.
Syntax

```go
tx, err := db.Begin(ctx)
```

**Returns:** `(*Transaction, error)`
Returns [`ErrTransactionsNotSupported`](https://surrealdb.com/docs/reference/golang/api/errors#sentinel-errors) if the connection is not WebSocket.
###  `session.Begin()`[](https://surrealdb.com/docs/reference/golang/api/core/transaction#session-begin)
Starts a transaction within a specific session.
Syntax

```go
tx, err := session.Begin(ctx)
```

**Returns:** `(*Transaction, error)`
Returns [`ErrSessionClosed`](https://surrealdb.com/docs/reference/golang/api/errors#sentinel-errors) if the session has been detached.
####  Examples[](https://surrealdb.com/docs/reference/golang/api/core/transaction#examples)

```go
tx, err := db.Begin(ctx)
if err != nil {
    log.Fatal(err)
}
defer tx.Cancel(ctx)

_, err = surrealdb.Create[any](ctx, tx, models.Table("events"), map[string]any{
    "type": "transfer",
    "amount": 100,
})
if err != nil {
    log.Fatal(err)
}

if err := tx.Commit(ctx); err != nil {
    log.Fatal(err)
}
```

* * *
##  Properties[](https://surrealdb.com/docs/reference/golang/api/core/transaction#properties)
###  `.ID()`[](https://surrealdb.com/docs/reference/golang/api/core/transaction#id)
Returns the transaction's UUID.
Syntax

```go
id := tx.ID()
```

**Returns:** [`*models.UUID`](https://surrealdb.com/docs/reference/golang/api/values/uuid)
###  `.SessionID()`[](https://surrealdb.com/docs/reference/golang/api/core/transaction#sessionid)
Returns the session UUID if the transaction was started within a [`Session`](https://surrealdb.com/docs/reference/golang/api/core/session). Returns `nil` for transactions started on the default session.
Syntax

```go
sessionID := tx.SessionID()
```

**Returns:** [`*models.UUID`](https://surrealdb.com/docs/reference/golang/api/values/uuid)
###  `.IsClosed()`[](https://surrealdb.com/docs/reference/golang/api/core/transaction#isclosed)
Returns whether the transaction has been committed or canceled.
Syntax

```go
closed := tx.IsClosed()
```

**Returns:** `bool`
* * *
##  Methods[](https://surrealdb.com/docs/reference/golang/api/core/transaction#methods)
###  `.Commit()`[](https://surrealdb.com/docs/reference/golang/api/core/transaction#commit)
Commits the transaction, making all changes permanent. After calling `.Commit()`, the transaction cannot be used.
Syntax

```go
err := tx.Commit(ctx)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
**Returns:** `error`
Returns [`ErrTransactionClosed`](https://surrealdb.com/docs/reference/golang/api/errors#sentinel-errors) if the transaction has already been committed or canceled.
###  `.Cancel()`[](https://surrealdb.com/docs/reference/golang/api/core/transaction#cancel)
Cancels the transaction, discarding all changes. After calling `.Cancel()`, the transaction cannot be used.
It is safe to call `.Cancel()` on an already committed or canceled transaction. It returns [`ErrTransactionClosed`](https://surrealdb.com/docs/reference/golang/api/errors#sentinel-errors) but causes no harm, making it safe for use with `defer`.
Syntax

```go
err := tx.Cancel(ctx)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
**Returns:** `error`
* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/core/transaction#see-also)
  * •
[DB](https://surrealdb.com/docs/reference/golang/api/core/db) for starting transactions from the main client
  * •
[Session](https://surrealdb.com/docs/reference/golang/api/core/session) for starting transactions from sessions
  * •
[Transactions](https://surrealdb.com/docs/reference/golang/concepts/transactions) for transaction usage patterns
  * •
[Errors](https://surrealdb.com/docs/reference/golang/api/errors) for `ErrTransactionClosed` and `ErrTransactionsNotSupported`
