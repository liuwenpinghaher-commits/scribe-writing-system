---
title: "https://surrealdb.com/docs/reference/kotlin/api/core/session"
url: "https://surrealdb.com/docs/reference/kotlin/api/core/session"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/core/session

Source: https://surrealdb.com/docs/reference/kotlin/api/core/session

`SurrealSession` is the base class of [`SurrealClient`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) and the type returned by [`.newSession()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#new-session). It exposes the full querying, authentication, and CRUD API with state — authentication, namespace, database, and parameters — isolated to that session. See [Multiple sessions](https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions) for the concept.
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
* * *
##  Shared API[](https://surrealdb.com/docs/reference/kotlin/api/core/session#shared-api)
Because [`SurrealClient`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) extends `SurrealSession`, every session — root or child — provides the same methods documented on the client:
  * •
Connection: [`.use()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#use), [`.ping()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#ping), [`.version()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#version)
  * •
Authentication: [`.signin()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#signin), [`.signup()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#signup), [`.authenticate()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#authenticate), [`.auth()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#auth), [`.invalidate()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#invalidate), [`.reset()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#reset)
  * •
Queries: [`.query()`](/docs/reference/kotlin/api/core/surreal-client#query), [`.queryAs()`](/docs/reference/kotlin/api/core/surreal-client#query-as), [`.let()`](/docs/reference/kotlin/api/core/surreal-client#let), [`.unset()`](/docs/reference/kotlin/api/core/surreal-client#unset)
  * •
CRUD builders: [`.select()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#select), [`.create()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#create), [`.update()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#update), [`.upsert()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#upsert), [`.merge()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#merge), [`.patch()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#patch), [`.delete()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#delete), [`.relate()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#relate), [`.insert()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#insert)
  * •
Live queries: [`.live()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#live), [`.kill()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#kill)

##  Session state accessors[](https://surrealdb.com/docs/reference/kotlin/api/core/session#session-state-accessors)  
| Method  | Type  | Description  |  
| --- | --- | --- |  
| `.namespace()`  | `String?`  | The session's current namespace.  |  
| `.database()`  | `String?`  | The session's current database.  |  
| `.accessToken()`  | `String?`  | The session's current access token, if authenticated.  |  
##  Creating and closing sessions[](https://surrealdb.com/docs/reference/kotlin/api/core/session#creating-and-closing-sessions)
Example

```kotlin
val session = client.newSession()
session.signin(buildJsonObject { put("user", "a"); put("pass", "a") })
session.use("acme", "main")

// ... use the session ...

client.closeSession(session)
```

##  Transactions[](https://surrealdb.com/docs/reference/kotlin/api/core/session#transactions)
Transactions are started on a session via the [`transaction { }`](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#transaction-block) and [`beginTransaction()`](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#begin-transaction) extension functions. See the [Transaction reference](https://surrealdb.com/docs/reference/kotlin/api/core/transaction).
##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/core/session#learn-more)
  * •
[SurrealClient API reference](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client)
  * •
[Multiple sessions](https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions)
  * •
[Transaction reference](https://surrealdb.com/docs/reference/kotlin/api/core/transaction)
