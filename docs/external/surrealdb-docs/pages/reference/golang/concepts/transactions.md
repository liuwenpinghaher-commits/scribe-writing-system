---
title: "https://surrealdb.com/docs/reference/golang/concepts/transactions"
url: "https://surrealdb.com/docs/reference/golang/concepts/transactions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/transactions

Source: https://surrealdb.com/docs/reference/golang/concepts/transactions

Interactive transactions let you group multiple operations into an atomic unit. Unlike text-based transactions (`BEGIN TRANSACTION; ... COMMIT;` — see the [query builder](https://surrealdb.com/docs/reference/golang/concepts/query-builder#building-text-based-transactions) for composing those), interactive transactions allow you to execute statements one at a time, inspect results, and conditionally decide whether to commit or cancel.
Transactions require a WebSocket connection (`ws://` or `wss://`) and SurrealDB v3 or later.
##  API references[](https://surrealdb.com/docs/reference/golang/concepts/transactions#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.Begin(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/db#begin)  | Starts a transaction on the default session  |  
| [`session.Begin(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/session#begin)  | Starts a transaction within a session  |  
| [`tx.Commit(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/transaction#commit)  | Commits the transaction, applying all changes  |  
| [`tx.Cancel(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/transaction#cancel)  | Cancels the transaction, discarding all changes  |  
| [`tx.ID()`](https://surrealdb.com/docs/reference/golang/api/core/transaction#id)  | Returns the transaction's UUID  |  
| [`tx.IsClosed()`](https://surrealdb.com/docs/reference/golang/api/core/transaction#isclosed)  | Returns whether the transaction has been committed or canceled  |  
##  Starting a transaction[](https://surrealdb.com/docs/reference/golang/concepts/transactions#starting-a-transaction)
Call [`.Begin()`](https://surrealdb.com/docs/reference/golang/api/core/db#begin) on a [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db) or [`*Session`](https://surrealdb.com/docs/reference/golang/api/core/session) to start a transaction. The transaction inherits the authentication and namespace context from the connection or session that started it.

```go
tx, err := db.Begin(ctx)
if err != nil {
	log.Fatal(err)
}
defer tx.Cancel(ctx)
```

Note
Always use `defer tx.Cancel(ctx)` immediately after `.Begin()`. If the transaction has already been committed, [`.Cancel()`](https://surrealdb.com/docs/reference/golang/api/core/transaction#cancel) returns [`ErrTransactionClosed`](https://surrealdb.com/docs/reference/golang/api/errors#sentinel-errors) but does not cause any harm.
##  Executing operations within a transaction[](https://surrealdb.com/docs/reference/golang/concepts/transactions#executing-operations-within-a-transaction)
Transactions satisfy the [`sendable`](https://surrealdb.com/docs/reference/golang/api/types#sendable) constraint, so all generic functions like [`Query`](https://surrealdb.com/docs/reference/golang/api/core/db#query), [`Select`](https://surrealdb.com/docs/reference/golang/api/core/db#select), [`Create`](https://surrealdb.com/docs/reference/golang/api/core/db#create), [`Update`](https://surrealdb.com/docs/reference/golang/api/core/db#update), and [`Delete`](https://surrealdb.com/docs/reference/golang/api/core/db#delete) accept a [`*Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction).

```go
tx, err := db.Begin(ctx)
if err != nil {
	log.Fatal(err)
}
defer tx.Cancel(ctx)

_, err = surrealdb.Create[any](ctx, tx, models.Table("accounts"), map[string]any{
	"name":    "Alice",
	"balance": 1000,
})
if err != nil {
	log.Fatal(err)
}

_, err = surrealdb.Create[any](ctx, tx, models.Table("accounts"), map[string]any{
	"name":    "Bob",
	"balance": 500,
})
if err != nil {
	log.Fatal(err)
}

if err := tx.Commit(ctx); err != nil {
	log.Fatal(err)
}
```

Changes made within a transaction are not visible to other connections or sessions until the transaction is committed.
##  Conditional commit or cancel[](https://surrealdb.com/docs/reference/golang/concepts/transactions#conditional-commit-or-cancel)
Because interactive transactions let you inspect results between operations, you can decide whether to commit based on runtime conditions.

```go
tx, err := db.Begin(ctx)
if err != nil {
	log.Fatal(err)
}
defer tx.Cancel(ctx)

results, err := surrealdb.Query[[]map[string]any](ctx, tx,
	"SELECT * FROM accounts WHERE name = 'Alice'",
	nil,
)
if err != nil {
	log.Fatal(err)
}

balance, ok := (*results)[0].Result[0]["balance"].(float64)
if !ok || balance < 100 {
	fmt.Println("Insufficient balance, canceling")
	return
}

_, err = surrealdb.Query[[]any](ctx, tx,
	"UPDATE accounts SET balance -= 100 WHERE name = 'Alice'; UPDATE accounts SET balance += 100 WHERE name = 'Bob';",
	nil,
)
if err != nil {
	log.Fatal(err)
}

if err := tx.Commit(ctx); err != nil {
	log.Fatal(err)
}
```

##  Transaction limitations[](https://surrealdb.com/docs/reference/golang/concepts/transactions#transaction-limitations)
Transactions do not support session state changes. The following operations are not available on a [`*Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction):
  * •
[`.SignIn()`](https://surrealdb.com/docs/reference/golang/api/core/db#signin), [`.SignUp()`](https://surrealdb.com/docs/reference/golang/api/core/db#signup), [`.Authenticate()`](https://surrealdb.com/docs/reference/golang/api/core/db#authenticate), [`.Invalidate()`](https://surrealdb.com/docs/reference/golang/api/core/db#invalidate)
  * •
[`.Use()`](https://surrealdb.com/docs/reference/golang/api/core/db#use)
  * •
[`.Let()`](https://surrealdb.com/docs/reference/golang/api/core/db#let), [`.Unset()`](https://surrealdb.com/docs/reference/golang/api/core/db#unset)
  * •
[Live queries](https://surrealdb.com/docs/reference/golang/concepts/live-queries) ([`Live`](https://surrealdb.com/docs/reference/golang/api/core/db#live), [`Kill`](https://surrealdb.com/docs/reference/golang/api/core/db#kill))

The namespace, database, authentication, and variables are inherited from the `*DB` or `*Session` that started the transaction.
##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/transactions#learn-more)
  * •
[Transaction API reference](https://surrealdb.com/docs/reference/golang/api/core/transaction) for complete method signatures
  * •
[Multiple sessions](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions) for session-scoped transactions
  * •
[Error handling](https://surrealdb.com/docs/reference/golang/concepts/error-handling) for transaction error types
  * •
[SurrealQL transactions](https://surrealdb.com/docs/reference/query-language/statements/begin) for text-based transaction syntax
