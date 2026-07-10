---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions

Source: https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions

A single WebSocket connection can host multiple independent **sessions** , each with its own authentication, namespace, database, and parameters. This is useful for multi-tenant applications where requests act on behalf of different users over one shared connection. The [`SurrealClient`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) is itself the root session.
Note
Multiple sessions require a stateful connection and are only available over the **WebSocket** transport. Check support with [`client.supports(SurrealFeature.Sessions)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#supports).
##  API references[](https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`client.newSession()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#new-session)  | Creates a new isolated session  |  
| [`client.closeSession(session)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#close-session)  | Closes a session  |  
##  Creating sessions[](https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions#creating-sessions)
Each session created with [`.newSession()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#new-session) is a [`SurrealSession`](https://surrealdb.com/docs/reference/kotlin/api/core/session) that exposes the same querying and authentication API as the client, but with isolated state.

```kotlin
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

val tenantA = client.newSession()
val tenantB = client.newSession()

tenantA.signin(buildJsonObject { put("user", "a"); put("pass", "a") })
tenantA.use("acme", "main")

tenantB.signin(buildJsonObject { put("user", "b"); put("pass", "b") })
tenantB.use("globex", "main")

// Each query runs as its own authenticated tenant, isolated from the other.
val aPeople = tenantA.query("SELECT * FROM person")
val bPeople = tenantB.query("SELECT * FROM person")
```

##  Closing sessions[](https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions#closing-sessions)
Close a session with [`.closeSession()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#close-session) when you no longer need it. This does not close the underlying connection.

```kotlin
client.closeSession(tenantA)
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions#learn-more)
  * •
[Session reference](https://surrealdb.com/docs/reference/kotlin/api/core/session) for the session API
  * •
[Authentication](https://surrealdb.com/docs/reference/kotlin/concepts/authentication) for per-session credentials
  * •
[Transactions](https://surrealdb.com/docs/reference/kotlin/concepts/transactions) — transactions run within a session
