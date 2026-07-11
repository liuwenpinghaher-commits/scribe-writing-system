---
title: "https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions"
url: "https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions

Source: https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions

Sessions allow you to create isolated contexts on a single WebSocket connection. Each session has its own authentication state, namespace and database selection, and connection variables. This is useful when a single application needs to serve multiple users or tenants over one connection.
Sessions require a WebSocket connection (`ws://` or `wss://`) and SurrealDB v3 or later.
##  API references[](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.Attach(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/session#attach)  | Creates a new session on the connection  |  
| [`session.Detach(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/session#detach)  | Removes the session from the server  |  
| [`session.ID()`](https://surrealdb.com/docs/reference/golang/api/core/session#id)  | Returns the session's UUID  |  
##  Creating a session[](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions#creating-a-session)
Call `.Attach()` on the `*DB` to create a new session. The session starts unauthenticated and without a selected namespace or database, so you must configure it before making queries.

```go
session, err := db.Attach(ctx)
if err != nil {
	log.Fatal(err)
}
defer session.Detach(ctx)

_, err = session.SignIn(ctx, surrealdb.Auth{
	Username: "root",
	Password: "root",
})
if err != nil {
	log.Fatal(err)
}

if err := session.Use(ctx, "my_ns", "my_db"); err != nil {
	log.Fatal(err)
}
```

##  Querying with a session[](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions#querying-with-a-session)
Sessions satisfy the [`sendable`](https://surrealdb.com/docs/reference/golang/api/types#sendable) constraint, so all generic functions like [`Query`](https://surrealdb.com/docs/reference/golang/api/core/db#query), [`Select`](https://surrealdb.com/docs/reference/golang/api/core/db#select), [`Create`](https://surrealdb.com/docs/reference/golang/api/core/db#create), etc. accept a [`*Session`](https://surrealdb.com/docs/reference/golang/api/core/session) directly.

```go
results, err := surrealdb.Query[[]Person](ctx, session,
	"SELECT * FROM persons",
	nil,
)
```

Each session maintains its own state. Changes to variables, authentication, or namespace on one session do not affect the parent [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db) or other sessions.
##  Session isolation[](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions#session-isolation)
Sessions are fully isolated from each other and from the parent connection:
  * •
Authentication is independent: signing in on a session does not affect other sessions or the [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db).
  * •
[`.Use()`](https://surrealdb.com/docs/reference/golang/api/core/session#use) on a session does not change the namespace/database of other sessions.
  * •
Variables set with [`.Let()`](https://surrealdb.com/docs/reference/golang/api/core/session#let) are scoped to the session.
  * •
[Live queries](https://surrealdb.com/docs/reference/golang/concepts/live-queries) started on a session are scoped to that session.

```go
sessionA, _ := db.Attach(ctx)
defer sessionA.Detach(ctx)

sessionB, _ := db.Attach(ctx)
defer sessionB.Detach(ctx)

sessionA.SignIn(ctx, surrealdb.Auth{Username: "admin", Password: "admin"})
sessionA.Use(ctx, "ns_a", "db_a")

sessionB.SignIn(ctx, surrealdb.Auth{Namespace: "ns_b", Database: "db_b", Access: "user_access", Username: "user1", Password: "pass1"})
sessionB.Use(ctx, "ns_b", "db_b")
```

##  Starting transactions from a session[](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions#starting-transactions-from-a-session)
Sessions can start their own transactions using `.Begin()`. The transaction inherits the session's authentication and namespace context.

```go
tx, err := session.Begin(ctx)
if err != nil {
	log.Fatal(err)
}
defer tx.Cancel(ctx)

surrealdb.Create[any](ctx, tx, models.Table("events"), map[string]any{"type": "login"})

if err := tx.Commit(ctx); err != nil {
	log.Fatal(err)
}
```

See [Transactions](https://surrealdb.com/docs/reference/golang/concepts/transactions) for more on interactive transactions.
##  Detaching a session[](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions#detaching-a-session)
Call [`.Detach()`](https://surrealdb.com/docs/reference/golang/api/core/session#detach) to remove the session from the server. After detaching, the session cannot be used and any operations on it return [`ErrSessionClosed`](https://surrealdb.com/docs/reference/golang/api/errors#sentinel-errors).

```go
if err := session.Detach(ctx); err != nil {
	log.Fatal(err)
}
```

Use `defer session.Detach(ctx)` immediately after `.Attach()` to ensure cleanup.
##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions#learn-more)
  * •
[Session API reference](https://surrealdb.com/docs/reference/golang/api/core/session) for complete method signatures
  * •
[Transactions](https://surrealdb.com/docs/reference/golang/concepts/transactions) for interactive transaction support
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb) for WebSocket connection requirements
  * •
[Errors reference](https://surrealdb.com/docs/reference/golang/api/errors) for session-related error types
