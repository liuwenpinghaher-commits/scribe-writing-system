---
title: "https://surrealdb.com/docs/reference/golang/api/core/session"
url: "https://surrealdb.com/docs/reference/golang/api/core/session"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/core/session

Source: https://surrealdb.com/docs/reference/golang/api/core/session

The `Session` struct represents an additional SurrealDB session on a WebSocket connection. Each session has its own authentication state, namespace and database selection, and connection variables. Sessions require SurrealDB v3+ and a WebSocket connection.
`Session` satisfies the [`sendable`](https://surrealdb.com/docs/reference/golang/api/types#sendable) constraint, so all generic functions like [`Query`](https://surrealdb.com/docs/reference/golang/api/core/db#query), [`Select`](https://surrealdb.com/docs/reference/golang/api/core/db#select), [`Create`](https://surrealdb.com/docs/reference/golang/api/core/db#create), etc. accept `*Session` directly.
**Source:** [session.go](https://github.com/surrealdb/surrealdb.go/blob/main/session.go)
* * *
##  Creating a session[](https://surrealdb.com/docs/reference/golang/api/core/session#creating-a-session)
###  `db.Attach()`[](https://surrealdb.com/docs/reference/golang/api/core/session#attach)
Creates a new session on the WebSocket connection. The session starts unauthenticated and without a selected namespace or database.
Syntax

```go
session, err := db.Attach(ctx)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
**Returns:** `(*Session, error)`
Returns `ErrSessionsNotSupported` if the connection is not WebSocket.
####  Examples[](https://surrealdb.com/docs/reference/golang/api/core/session#examples)

```go
session, err := db.Attach(ctx)
if err != nil {
    log.Fatal(err)
}
defer session.Detach(ctx)

session.SignIn(ctx, surrealdb.Auth{Username: "root",
    Password: "root"})
session.Use(ctx, "my_ns", "my_db")

results, err := surrealdb.Query[[]Person](ctx, session,
    "SELECT * FROM persons", nil)
```

* * *
##  Properties[](https://surrealdb.com/docs/reference/golang/api/core/session#properties)
###  `.ID()`[](https://surrealdb.com/docs/reference/golang/api/core/session#id)
Returns the session's UUID.
Syntax

```go
id := session.ID()
```

**Returns:** [`*models.UUID`](https://surrealdb.com/docs/reference/golang/api/values/uuid)
* * *
##  Methods[](https://surrealdb.com/docs/reference/golang/api/core/session#methods)
###  `.Detach()`[](https://surrealdb.com/docs/reference/golang/api/core/session#detach)
Removes the session from the server. After calling `.Detach()`, the session cannot be used.
Syntax

```go
err := session.Detach(ctx)
```

**Returns:** `error`
Returns [`ErrSessionClosed`](https://surrealdb.com/docs/reference/golang/api/errors#sentinel-errors) if the session has already been detached.
###  `.Begin()`[](https://surrealdb.com/docs/reference/golang/api/core/session#begin)
Starts a new interactive transaction within this session.
Syntax

```go
tx, err := session.Begin(ctx)
```

**Returns:** `(*Transaction, error)` — see [`Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction)
Returns [`ErrSessionClosed`](https://surrealdb.com/docs/reference/golang/api/errors#sentinel-errors) if the session has been detached.
###  `.SignIn()`[](https://surrealdb.com/docs/reference/golang/api/core/session#signin)
Signs in an existing user within this session.
Syntax

```go
token, err := session.SignIn(ctx, authData)
```

**Returns:** `(string, error)`
###  `.SignInWithRefresh()`[](https://surrealdb.com/docs/reference/golang/api/core/session#signinwithrefresh)
Signs in with refresh token support within this session. SurrealDB v3+ only.
Syntax

```go
tokens, err := session.SignInWithRefresh(ctx, authData)
```

**Returns:** [`(*Tokens, error)`](https://surrealdb.com/docs/reference/golang/api/types#tokens)
###  `.SignUp()`[](https://surrealdb.com/docs/reference/golang/api/core/session#signup)
Signs up a new record user within this session.
Syntax

```go
token, err := session.SignUp(ctx, authData)
```

**Returns:** `(string, error)`
###  `.SignUpWithRefresh()`[](https://surrealdb.com/docs/reference/golang/api/core/session#signupwithrefresh)
Signs up with refresh token support within this session. SurrealDB v3+ only.
Syntax

```go
tokens, err := session.SignUpWithRefresh(ctx, authData)
```

**Returns:** [`(*Tokens, error)`](https://surrealdb.com/docs/reference/golang/api/types#tokens)
###  `.Authenticate()`[](https://surrealdb.com/docs/reference/golang/api/core/session#authenticate)
Authenticates this session with a JWT token.
Syntax

```go
err := session.Authenticate(ctx, token)
```

**Returns:** `error`
###  `.Invalidate()`[](https://surrealdb.com/docs/reference/golang/api/core/session#invalidate)
Invalidates the current authentication for this session.
Syntax

```go
err := session.Invalidate(ctx)
```

**Returns:** `error`
###  `.Use()`[](https://surrealdb.com/docs/reference/golang/api/core/session#use)
Selects the namespace and database for this session.
Syntax

```go
err := session.Use(ctx, ns, database)
```

**Returns:** `error`
###  `.Let()`[](https://surrealdb.com/docs/reference/golang/api/core/session#let)
Defines a variable scoped to this session.
Syntax

```go
err := session.Let(ctx, key, val)
```

**Returns:** `error`
###  `.Unset()`[](https://surrealdb.com/docs/reference/golang/api/core/session#unset)
Removes a variable from this session.
Syntax

```go
err := session.Unset(ctx, key)
```

**Returns:** `error`
###  `.Info()`[](https://surrealdb.com/docs/reference/golang/api/core/session#info)
Returns the record of the currently authenticated user in this session.
Syntax

```go
info, err := session.Info(ctx)
```

**Returns:** `(map[string]any, error)`
###  `.Version()`[](https://surrealdb.com/docs/reference/golang/api/core/session#version)
Returns the SurrealDB version information.
Syntax

```go
ver, err := session.Version(ctx)
```

**Returns:** [`(*VersionData, error)`](https://surrealdb.com/docs/reference/golang/api/types#versiondata)
###  `.LiveNotifications()`[](https://surrealdb.com/docs/reference/golang/api/core/session#livenotifications)
Returns the notification channel for a live query.
Syntax

```go
ch, err := session.LiveNotifications(liveQueryID)
```

**Returns:** `(chan` [`connection.Notification`](https://surrealdb.com/docs/reference/golang/api/types#notification)`, error)`
###  `.CloseLiveNotifications()`[](https://surrealdb.com/docs/reference/golang/api/core/session#closelivenotifications)
Closes the notification channel for a live query.
Syntax

```go
err := session.CloseLiveNotifications(liveQueryID)
```

**Returns:** `error`
* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/core/session#see-also)
  * •
[DB](https://surrealdb.com/docs/reference/golang/api/core/db) for the main client reference
  * •
[Transaction](https://surrealdb.com/docs/reference/golang/api/core/transaction) for session-scoped transactions
  * •
[Multiple sessions](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions) for session usage patterns
  * •
[Errors](https://surrealdb.com/docs/reference/golang/api/errors) for `ErrSessionClosed` and `ErrSessionsNotSupported`
