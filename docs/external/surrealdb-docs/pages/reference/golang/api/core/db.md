---
title: "https://surrealdb.com/docs/reference/golang/api/core/db"
url: "https://surrealdb.com/docs/reference/golang/api/core/db"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/core/db

Source: https://surrealdb.com/docs/reference/golang/api/core/db

The `DB` struct is the main client for interacting with SurrealDB. It holds the underlying connection and provides methods for [authentication](https://surrealdb.com/docs/reference/golang/concepts/authentication), namespace selection, and [live query](https://surrealdb.com/docs/reference/golang/concepts/live-queries) management. Data operations are performed through generic top-level functions that accept `*DB` as a parameter.
**Source:** [db.go](https://github.com/surrealdb/surrealdb.go/blob/main/db.go)
* * *
##  Constructors[](https://surrealdb.com/docs/reference/golang/api/core/db#constructors)
###  `FromEndpointURLString`[](https://surrealdb.com/docs/reference/golang/api/core/db#fromendpointurlstring)
Creates a new `*DB` and connects to a SurrealDB instance. The URL scheme determines the connection type (WebSocket or HTTP).
Syntax

```go
db, err := surrealdb.FromEndpointURLString(ctx, connectionURL)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for canceling the connection attempt.  |  
| `connectionURL`  | `string`  |  The endpoint URL. Supported schemes: `ws://`, `wss://`, `http://`, `https://`.  |  
**Returns:** `(*DB, error)`
####  Examples[](https://surrealdb.com/docs/reference/golang/api/core/db#examples)
WebSocket

```go
db, err := surrealdb.FromEndpointURLString(ctx, "ws://localhost:8000")
```

HTTPS

```go
db, err := surrealdb.FromEndpointURLString(ctx, "https://cloud.surrealdb.com")
```

###  `FromConnection`[](https://surrealdb.com/docs/reference/golang/api/core/db#fromconnection)
Creates a new `*DB` from a custom `connection.Connection` implementation. Calls `.Connect(ctx)` automatically.
Syntax

```go
db, err := surrealdb.FromConnection(ctx, conn)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for canceling the connection attempt.  |  
| `conn`  | `connection.Connection`  |  A connection implementation (e.g., `gorillaws.New(conf)`or `http.New(conf)`).  |  
**Returns:** `(*DB, error)`
* * *
##  Connection methods[](https://surrealdb.com/docs/reference/golang/api/core/db#connection-methods)
###  `.Close()`[](https://surrealdb.com/docs/reference/golang/api/core/db#close)
Closes the underlying connection and releases resources.
Syntax

```go
err := db.Close(ctx)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the close operation.  |  
**Returns:** `error`
###  `.Use()`[](https://surrealdb.com/docs/reference/golang/api/core/db#use)
Selects the namespace and database to use for subsequent operations.
Syntax

```go
err := db.Use(ctx, ns, database)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `ns`  | `string`  | The namespace to use.  |  
| `database`  | `string`  | The database to use.  |  
**Returns:** `error`
###  `.Version()`[](https://surrealdb.com/docs/reference/golang/api/core/db#version)
Returns version information about the connected SurrealDB instance.
Syntax

```go
ver, err := db.Version(ctx)
```

**Returns:** `(*VersionData, error)`, see [`VersionData`](https://surrealdb.com/docs/reference/golang/api/types#versiondata)
####  Examples[](https://surrealdb.com/docs/reference/golang/api/core/db#examples-1)

```go
ver, err := db.Version(ctx)
if err != nil {
    log.Fatal(err)
}
fmt.Println(ver.Version)
```

* * *
##  Authentication methods[](https://surrealdb.com/docs/reference/golang/api/core/db#authentication-methods)
###  `.SignIn()`[](https://surrealdb.com/docs/reference/golang/api/core/db#signin)
Signs in an existing user. The fields provided in `authData` determine the authentication level (root, namespace, database, or record).
Syntax

```go
token, err := db.SignIn(ctx, authData)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `authData`  | `any`  |  An [`Auth`](https://surrealdb.com/docs/reference/golang/api/types#auth)struct or `map[string]any`with credentials.  |  
**Returns:** `(string, error)` — the JWT token string
####  Examples[](https://surrealdb.com/docs/reference/golang/api/core/db#examples-2)
Root signin

```go
token, err := db.SignIn(ctx, surrealdb.Auth{
    Username: "root",
    Password: "root",
})
```

Record signin

```go
token, err := db.SignIn(ctx, map[string]any{
    "NS": "my_ns", "DB": "my_db", "AC": "user_access",
    "user": "tobie", "pass": "s3cret",
})
```

###  `.SignInWithRefresh()`[](https://surrealdb.com/docs/reference/golang/api/core/db#signinwithrefresh)
Signs in using a `TYPE RECORD` access method with `WITH REFRESH` enabled. Returns both an access token and a refresh token. SurrealDB v3+ only.
Syntax

```go
tokens, err := db.SignInWithRefresh(ctx, authData)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `authData`  | `any`  |  Credentials as `map[string]any`. Use `"refresh"`key for token refresh.  |  
**Returns:** `(*Tokens, error)` — see [`Tokens`](https://surrealdb.com/docs/reference/golang/api/types#tokens)
####  Examples[](https://surrealdb.com/docs/reference/golang/api/core/db#examples-3)
Initial signin

```go
tokens, err := db.SignInWithRefresh(ctx, map[string]any{
    "NS": "my_ns", "DB": "my_db", "AC": "user_access",
    "user": "tobie", "pass": "s3cret",
})
```

Refresh

```go
newTokens, err := db.SignInWithRefresh(ctx, map[string]any{
    "NS": "my_ns", "DB": "my_db", "AC": "user_access",
    "refresh": tokens.Refresh,
})
```

###  `.SignUp()`[](https://surrealdb.com/docs/reference/golang/api/core/db#signup)
Signs up a new record user.
Syntax

```go
token, err := db.SignUp(ctx, authData)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `authData`  | `any`  |  An [`Auth`](https://surrealdb.com/docs/reference/golang/api/types#auth)struct or `map[string]any`with signup credentials.  |  
**Returns:** `(string, error)` — the JWT token string
###  `.SignUpWithRefresh()`[](https://surrealdb.com/docs/reference/golang/api/core/db#signupwithrefresh)
Signs up using a `TYPE RECORD` access method with `WITH REFRESH` enabled. SurrealDB v3+ only.
Syntax

```go
tokens, err := db.SignUpWithRefresh(ctx, authData)
```

**Returns:** `(*Tokens, error)` — see [`Tokens`](https://surrealdb.com/docs/reference/golang/api/types#tokens)
###  `.Authenticate()`[](https://surrealdb.com/docs/reference/golang/api/core/db#authenticate)
Authenticates the connection with a JWT token.
Syntax

```go
err := db.Authenticate(ctx, token)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `token`  | `string`  | The JWT token to authenticate with.  |  
**Returns:** `error`
###  `.Invalidate()`[](https://surrealdb.com/docs/reference/golang/api/core/db#invalidate)
Invalidates the current authentication, returning the connection to an unauthenticated state.
Syntax

```go
err := db.Invalidate(ctx)
```

**Returns:** `error`
###  `.Info()`[](https://surrealdb.com/docs/reference/golang/api/core/db#info)
Returns the record of the currently authenticated user.
Syntax

```go
info, err := db.Info(ctx)
```

**Returns:** `(map[string]any, error)`
* * *
##  Variables[](https://surrealdb.com/docs/reference/golang/api/core/db#variables)
###  `.Let()`[](https://surrealdb.com/docs/reference/golang/api/core/db#let)
Defines a variable on the connection that can be used in subsequent queries.
Syntax

```go
err := db.Let(ctx, key, val)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `key`  | `string`  |  The variable name (without `$`prefix).  |  
| `val`  | `any`  | The value to assign.  |  
**Returns:** `error`
###  `.Unset()`[](https://surrealdb.com/docs/reference/golang/api/core/db#unset)
Removes a previously defined variable from the connection.
Syntax

```go
err := db.Unset(ctx, key)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `key`  | `string`  | The variable name to remove.  |  
**Returns:** `error`
* * *
##  Sessions and transactions[](https://surrealdb.com/docs/reference/golang/api/core/db#sessions-and-transactions)
###  `.Attach()`[](https://surrealdb.com/docs/reference/golang/api/core/db#attach)
Creates a new session on the WebSocket connection. Sessions are only supported on WebSocket connections (SurrealDB v3+).
Syntax

```go
session, err := db.Attach(ctx)
```

**Returns:** `(*Session, error)` — see [`Session`](https://surrealdb.com/docs/reference/golang/api/core/session)
###  `.Begin()`[](https://surrealdb.com/docs/reference/golang/api/core/db#begin)
Starts a new interactive transaction on the default session. Transactions are only supported on WebSocket connections (SurrealDB v3+).
Syntax

```go
tx, err := db.Begin(ctx)
```

**Returns:** `(*Transaction, error)` — see [`Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction)
* * *
##  Query functions[](https://surrealdb.com/docs/reference/golang/api/core/db#query-functions)
These are top-level generic functions that accept [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db#db), [`*Session`](https://surrealdb.com/docs/reference/golang/api/core/session), or [`*Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction) as the `s` parameter.
###  `Query`[](https://surrealdb.com/docs/reference/golang/api/core/db#query)
Executes a SurrealQL query string and returns typed results.
Syntax

```go
results, err := surrealdb.Query[TResult](ctx, s, sql, vars)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `TResult`  | type parameter  | The expected result type for each statement.  |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `s`  | `*DB | *Session | *Transaction`  | The sender to execute the query on.  |  
| `sql`  | `string`  | The SurrealQL query string.  |  
| `vars`  | `map[string]any`  |  Variables to bind into the query. Pass `nil`for no variables.  |  
**Returns:** `(*[]QueryResult[TResult], error)` — see [`QueryResult`](https://surrealdb.com/docs/reference/golang/api/types#queryresult)
####  Examples[](https://surrealdb.com/docs/reference/golang/api/core/db#examples-4)

```go
results, err := surrealdb.Query[[]Person](ctx, db,
    "SELECT * FROM persons WHERE age > $min",
    map[string]any{"min": 18},
)
```

###  `QueryRaw`[](https://surrealdb.com/docs/reference/golang/api/core/db#queryraw)
Composes and executes a batch of query statements with per-statement results.
Syntax

```go
err := surrealdb.QueryRaw(ctx, s, queries)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `s`  | `*DB | *Session | *Transaction`  | The sender to execute the query on.  |  
| `queries`  | `*[]QueryStmt`  |  A pointer to a slice of [`QueryStmt`](https://surrealdb.com/docs/reference/golang/api/types#querystmt)objects. Results are written back to each statement.  |  
**Returns:** `error`
* * *
##  Data functions[](https://surrealdb.com/docs/reference/golang/api/core/db#data-functions)
These are top-level generic functions that accept [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db#db), [`*Session`](https://surrealdb.com/docs/reference/golang/api/core/session), or [`*Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction) as the `s` parameter.
###  `Select`[](https://surrealdb.com/docs/reference/golang/api/core/db#select)
Retrieves records from the database.
Syntax

```go
result, err := surrealdb.Select[TResult](ctx, s, what)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `TResult`  | type parameter  | Use a slice type for tables, a single type for record IDs.  |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `s`  | `*DB | *Session | *Transaction`  | The sender.  |  
| `what`  |  `string |`[`Table`](https://surrealdb.com/docs/reference/golang/api/values/table)`|`[`RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id)  | The table or record to select.  |  
**Returns:** `(*TResult, error)`
###  `Create`[](https://surrealdb.com/docs/reference/golang/api/core/db#create)
Creates a new record.
Syntax

```go
result, err := surrealdb.Create[TResult](ctx, s, what, data)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `s`  | `*DB | *Session | *Transaction`  | The sender.  |  
| `what`  |  `string |`[`Table`](https://surrealdb.com/docs/reference/golang/api/values/table)`|`[`RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id)  | The table or record ID to create.  |  
| `data`  | `any`  | The record data (struct or map).  |  
**Returns:** `(*TResult, error)`
###  `Insert`[](https://surrealdb.com/docs/reference/golang/api/core/db#insert)
Inserts one or more records into a table.
Syntax

```go
results, err := surrealdb.Insert[TResult](ctx, s, table, data)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `s`  | `*DB | *Session | *Transaction`  | The sender.  |  
| `table`  | [`models.Table`](https://surrealdb.com/docs/reference/golang/api/values/table)  | The table to insert into.  |  
| `data`  | `any`  | A single record or slice of records to insert.  |  
**Returns:** `(*[]TResult, error)`
###  `Update`[](https://surrealdb.com/docs/reference/golang/api/core/db#update)
Replaces the entire content of a record (like a PUT).
Syntax

```go
result, err := surrealdb.Update[TResult](ctx, s, what, data)
```

**Returns:** `(*TResult, error)`
###  `Upsert`[](https://surrealdb.com/docs/reference/golang/api/core/db#upsert)
Creates a record if it does not exist, or replaces it entirely.
Syntax

```go
result, err := surrealdb.Upsert[TResult](ctx, s, what, data)
```

**Returns:** `(*TResult, error)`
###  `Merge`[](https://surrealdb.com/docs/reference/golang/api/core/db#merge)
Merges data into an existing record, preserving unmentioned fields.
Syntax

```go
result, err := surrealdb.Merge[TResult](ctx, s, what, data)
```

**Returns:** `(*TResult, error)`
###  `Patch`[](https://surrealdb.com/docs/reference/golang/api/core/db#patch)
Applies JSON Patch operations to a record or table.
Syntax

```go
result, err := surrealdb.Patch(ctx, s, what, patches)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `s`  | `*DB | *Session | *Transaction`  | The sender.  |  
| `what`  |  `string |`[`Table`](https://surrealdb.com/docs/reference/golang/api/values/table)`|`[`RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id)  | The table or record to patch.  |  
| `patches`  | `[]PatchData`  |  JSON Patch operations. See [`PatchData`](https://surrealdb.com/docs/reference/golang/api/types#patchdata).  |  
**Returns:** `(*[]PatchData, error)`
###  `Delete`[](https://surrealdb.com/docs/reference/golang/api/core/db#delete)
Removes records from the database.
Syntax

```go
result, err := surrealdb.Delete[TResult](ctx, s, what)
```

**Returns:** `(*TResult, error)`
###  `Relate`[](https://surrealdb.com/docs/reference/golang/api/core/db#relate)
Creates a relationship between two records with an auto-generated ID.
Syntax

```go
result, err := surrealdb.Relate[TResult](ctx, s, rel)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `s`  | `*DB | *Session | *Transaction`  | The sender.  |  
| `rel`  | `*Relationship`  |  The relationship to create. See [`Relationship`](https://surrealdb.com/docs/reference/golang/api/types#relationship).  |  
**Returns:** `(*TResult, error)`
###  `InsertRelation`[](https://surrealdb.com/docs/reference/golang/api/core/db#insertrelation)
Inserts a relation record, optionally with a specified ID.
Syntax

```go
result, err := surrealdb.InsertRelation[TResult](ctx, s, rel)
```

**Returns:** `(*TResult, error)`
* * *
##  Live query methods[](https://surrealdb.com/docs/reference/golang/api/core/db#live-query-methods)
###  `Live`[](https://surrealdb.com/docs/reference/golang/api/core/db#live)
Starts a live query on a table. Only available on `*DB` and `*Session`.
Syntax

```go
liveID, err := surrealdb.Live(ctx, s, table, diff)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ctx`  | `context.Context`  | Context for the operation.  |  
| `s`  | `*DB | *Session`  |  The sender (not `*Transaction`).  |  
| `table`  | [`models.Table`](https://surrealdb.com/docs/reference/golang/api/values/table)  | The table to watch.  |  
| `diff`  | `bool`  |  If `true`, notifications contain JSON Patch diffs.  |  
**Returns:** [`(*models.UUID, error)`](https://surrealdb.com/docs/reference/golang/api/values/uuid)
###  `Kill`[](https://surrealdb.com/docs/reference/golang/api/core/db#kill)
Terminates a live query and closes its notification channel.
Syntax

```go
err := surrealdb.Kill(ctx, s, id)
```

**Returns:** `error`
###  `.LiveNotifications()`[](https://surrealdb.com/docs/reference/golang/api/core/db#livenotifications)
Returns the notification channel for a live query.
Syntax

```go
ch, err := db.LiveNotifications(liveQueryID)
```

**Returns:** `(chan` [`connection.Notification`](https://surrealdb.com/docs/reference/golang/api/types#notification)`, error)`
###  `.CloseLiveNotifications()`[](https://surrealdb.com/docs/reference/golang/api/core/db#closelivenotifications)
Closes the notification channel without killing the server-side live query.
Syntax

```go
err := db.CloseLiveNotifications(liveQueryID)
```

**Returns:** `error`
* * *
##  Low-level RPC[](https://surrealdb.com/docs/reference/golang/api/core/db#low-level-rpc)
###  `Send`[](https://surrealdb.com/docs/reference/golang/api/core/db#send)
Sends a raw RPC request to SurrealDB. Limited to data methods: `select`, `create`, `insert`, `insert_relation`, `kill`, `live`, `merge`, `relate`, `update`, `upsert`, `patch`, `delete`, `query`.
Syntax

```go
err := surrealdb.Send[Result](ctx, db, res, method, params...)
```

**Returns:** `error`
* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/core/db#see-also)
  * •
[Session](https://surrealdb.com/docs/reference/golang/api/core/session) for session management reference
  * •
[Transaction](https://surrealdb.com/docs/reference/golang/api/core/transaction) for transaction reference
  * •
[Types](https://surrealdb.com/docs/reference/golang/api/types) for type definitions used by these methods
  * •
[Errors](https://surrealdb.com/docs/reference/golang/api/errors) for error types
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb) for connection patterns
