---
title: "https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb"
url: "https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb

Source: https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb

The Go SDK supports connecting to SurrealDB over WebSocket or HTTP. The `FromEndpointURLString` factory function inspects the URL scheme and creates the appropriate connection automatically.
This page covers how to create, configure, and manage connections to a SurrealDB instance.
##  API references[](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb#api-references)  
| Function  | Description  |  
| --- | --- |  
| [`surrealdb.FromEndpointURLString(ctx, url)`](https://surrealdb.com/docs/reference/golang/api/core/db#fromendpointurlstring)  | Creates a connection from a URL string  |  
| [`surrealdb.FromConnection(ctx, conn)`](https://surrealdb.com/docs/reference/golang/api/core/db#fromconnection)  | Creates a client from a custom connection implementation  |  
| [`db.Close(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/db#close)  | Closes the connection and releases resources  |  
| [`db.Use(ctx, ns, db)`](https://surrealdb.com/docs/reference/golang/api/core/db#use)  | Selects a namespace and database  |  
| [`db.Version(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/db#version)  | Returns the version of the connected SurrealDB instance  |  
##  Opening a connection[](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb#opening-a-connection)
Use `FromEndpointURLString` to create a new client and connect to a SurrealDB instance. The function accepts a `context.Context` for cancellation and a URL string that determines the connection type.

```go
ctx := context.Background()

db, err := surrealdb.FromEndpointURLString(ctx, "ws://localhost:8000")
if err != nil {
	log.Fatal(err)
}
defer db.Close(ctx)
```

The context controls how long the connection attempt blocks. You can use `context.WithTimeout` to limit the connection time on unreliable networks:

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

db, err := surrealdb.FromEndpointURLString(ctx, "ws://localhost:8000")
```

##  Connection string protocols[](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb#connection-string-protocols)
The URL scheme determines the connection type and its capabilities.  
| Scheme  | Connection type  | Description  |  
| --- | --- | --- |  
| `ws://`  | WebSocket  | Unencrypted stateful connection  |  
| `wss://`  | WebSocket  | TLS-encrypted stateful connection  |  
| `http://`  | HTTP  | Unencrypted stateless connection  |  
| `https://`  | HTTP  | TLS-encrypted stateless connection  |  
| `mem://`  | Memory  | In-memory [embedded instance](https://surrealdb.com/docs/reference/golang/embedding)  |  
WebSocket connections are long-lived and stateful. They support all SDK features including [live queries](https://surrealdb.com/docs/reference/golang/concepts/live-queries), [sessions](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions), and [transactions](https://surrealdb.com/docs/reference/golang/concepts/transactions).
HTTP connections are stateless. Each request is independent and requires its own authentication token. [Live queries](https://surrealdb.com/docs/reference/golang/concepts/live-queries), [sessions](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions), and [transactions](https://surrealdb.com/docs/reference/golang/concepts/transactions) are not available over HTTP.
##  Using a custom connection[](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb#using-a-custom-connection)
If you need to configure the underlying connection (for example, custom TLS settings or a specific WebSocket implementation), you can create a connection manually and pass it to [`FromConnection`](https://surrealdb.com/docs/reference/golang/api/core/db#fromconnection):

```go
import (
	"net/url"

	"github.com/surrealdb/surrealdb.go/pkg/connection"
	"github.com/surrealdb/surrealdb.go/pkg/connection/gorillaws"
)

endpoint, _ := url.Parse("ws://localhost:8000/rpc")
conf := connection.NewConfig(endpoint)
conn := gorillaws.New(conf)

db, err := surrealdb.FromConnection(ctx, conn)
```

[`FromConnection`](https://surrealdb.com/docs/reference/golang/api/core/db#fromconnection) calls `.Connect(ctx)` on the connection for you, so you do not need to call it separately. For auto-reconnecting connections, see [Reliable connections](https://surrealdb.com/docs/reference/golang/concepts/reliable-connections).
##  Selecting a namespace and database[](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb#selecting-a-namespace-and-database)
After connecting, use `.Use()` to select the namespace and database you want to work with. Most operations require a namespace and database to be selected first.

```go
if err := db.Use(ctx, "my_namespace", "my_database"); err != nil {
	log.Fatal(err)
}
```

You can call `.Use()` multiple times to switch between namespaces and databases on the same connection.
##  Effect of connection protocol on token and session duration[](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb#effect-of-connection-protocol-on-token-and-session-duration)
WebSocket connections (`ws://`, `wss://`) are long-lived and stateful. After authentication, the session persists for the lifetime of the connection. The session duration defaults to `NONE`, meaning it never expires unless configured otherwise.
HTTP connections (`http://`, `https://`) are stateless. Each request requires its own authentication token. The token duration defaults to 1 hour.
You can configure token and session durations using the `DURATION` clause in [`DEFINE ACCESS METHOD`](https://surrealdb.com/docs/reference/query-language/statements/define/access) or [`DEFINE USER`](https://surrealdb.com/docs/reference/query-language/statements/define/user) statements.
Note
Learn more about token and session duration in the [security best practices](https://surrealdb.com/docs/learn/security/best-practices/security-best-practices#expiration) documentation.
##  Closing a connection[](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb#closing-a-connection)
Call `.Close()` to release the underlying connection resources when you are done.

```go
db.Close(ctx)
```

Use `defer db.Close(ctx)` immediately after creating the connection to ensure cleanup happens even when errors occur.
##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb#learn-more)
  * •
[DB API reference](https://surrealdb.com/docs/reference/golang/api/core/db) for complete method signatures and parameters
  * •
[Authentication](https://surrealdb.com/docs/reference/golang/concepts/authentication) for signing in and managing user sessions
  * •
[Error handling](https://surrealdb.com/docs/reference/golang/concepts/error-handling) for handling connection and authentication errors
