---
title: "https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client"
url: "https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client

Source: https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client

The `SurrealClient` class is the main entry point for the Kotlin SDK. It connects to a SurrealDB instance, authenticates, queries, and manages data. It extends [`SurrealSession`](https://surrealdb.com/docs/reference/kotlin/api/core/session) and implements `AutoCloseable`. Almost every networked method is a `suspend` function and has a `...Result` companion that returns a [`Result`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/-result/) instead of throwing.
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.SurrealClient
import com.surrealdb.kotlin.SurrealClientConfig
```

* * *
##  Connection methods[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#connection-methods)
###  `SurrealClient(config)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#constructor)
Creates a new client from a [`SurrealClientConfig`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config). With `autoConnect = true` (the default) the client connects lazily on the first request.
Method Syntax

```kotlin
SurrealClient(config)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `config`  | `SurrealClientConfig`  |  The client configuration, including the connection `url`.  |  
**Returns:** `SurrealClient`
Example

```kotlin
val client = SurrealClient(SurrealClientConfig(url = "ws://localhost:8000"))
```

###  `.connect()`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#connect)
Establishes the connection explicitly. Rarely needed when `autoConnect` is enabled.
Method Syntax

```kotlin
client.connect()
```

**Returns:** `Unit`
Example

```kotlin
client.connect()
```

###  `.close()`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#close)
Closes the active connection and releases all associated resources.
Method Syntax

```kotlin
client.close()
```

**Returns:** `Unit`
Example

```kotlin
client.close()
```

###  `.use(namespace, database)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#use)
Selects the namespace and database for subsequent operations.
Method Syntax

```kotlin
client.use(namespace, database)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `namespace`  | `String`  | The namespace to select.  |  
| `database`  | `String`  | The database to select.  |  
**Returns:** `JsonElement`
Example

```kotlin
client.use("surrealdb", "docs")
```

###  `.ping()`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#ping)
Pings the server to verify connectivity.
Method Syntax

```kotlin
client.ping()
```

**Returns:** `JsonElement`
###  `.version()`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#version)
Returns the version of the connected SurrealDB server.
Method Syntax

```kotlin
client.version()
```

**Returns:** `JsonElement`
Example

```kotlin
val version = client.version()
```

###  `.supports(feature)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#supports)
Returns whether the current transport supports the given [`SurrealFeature`](https://surrealdb.com/docs/reference/kotlin/api/features#feature).
Method Syntax

```kotlin
client.supports(feature)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `feature`  | `SurrealFeature`  | The feature to check.  |  
**Returns:** `Boolean`
Example

```kotlin
if (client.supports(SurrealFeature.LiveQueries)) { /* ... */ }
```

* * *
##  Authentication methods[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#authentication-methods)
###  `.signup(params)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#signup)
Signs up against a [record access](https://surrealdb.com/docs/reference/query-language/statements/define/access/record) method and returns a token.
Method Syntax

```kotlin
client.signup(params)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `params`  | `JsonObject`  | The sign-up parameters (namespace, database, access, and any record variables).  |  
**Returns:** `JsonElement`
###  `.signin(params)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#signin)
Signs in with the given credentials and returns a token.
Method Syntax

```kotlin
client.signin(params)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `params`  | `JsonObject`  | The sign-in credentials.  |  
**Returns:** `JsonElement`
Example

```kotlin
client.signin(buildJsonObject {
    put("user", "root")
    put("pass", "root")
})
```

###  `.authenticate(token)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#authenticate)
Authenticates the session with an existing token.
Method Syntax

```kotlin
client.authenticate(token)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `token`  | `String`  | A JWT previously issued by SurrealDB.  |  
**Returns:** `JsonElement`
###  `.auth()`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#auth)
Returns the record of the currently authenticated user.
Method Syntax

```kotlin
client.auth()
```

**Returns:** `JsonElement`
###  `.invalidate()`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#invalidate)
Invalidates the current authentication for the session.
Method Syntax

```kotlin
client.invalidate()
```

**Returns:** `JsonElement`
###  `.reset()`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#reset)
Resets the session to its initial, unauthenticated state.
Method Syntax

```kotlin
client.reset()
```

**Returns:** `JsonElement`
* * *
##  Query methods[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#query-methods)
###  `.query(sql, vars)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#query)
Runs a raw [SurrealQL](https://surrealdb.com/docs/reference/query-language) statement with optional bound parameters.
Method Syntax

```kotlin
client.query(sql, vars)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `sql`  | `String`  | The SurrealQL to execute.  |  
| `vars`  | `JsonObject?`  |  Optional parameters bound as `$name`in the query.  |  
**Returns:** `JsonElement`
Example

```kotlin
val result = client.query(
    "SELECT * FROM person WHERE age > \$min",
    buildJsonObject { put("min", 18) },
)
```

There is also an overload that accepts a `BoundQuery` built with the [`surql`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#surql) DSL.
###  `.queryAs<T>(sql, vars)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#query-as)
Runs SurrealQL and decodes the result into `T` using [`kotlinx.serialization`](https://surrealdb.com/docs/reference/kotlin/concepts/serialization).
Method Syntax

```kotlin
client.queryAs<T>(sql, vars)
```

**Returns:** `T`
Example

```kotlin
val people: List<Person> = client.queryAs("SELECT * FROM person")
```

###  `.decode<T>(element)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#decode)
Decodes a [`JsonElement`](https://surrealdb.com/docs/reference/kotlin/api/values/value) into `T` using the client's configured `Json` instance.
Method Syntax

```kotlin
client.decode<T>(element)
```

**Returns:** `T`
###  `.let(key, value)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#let)
Defines a session parameter referenced as `$key` in subsequent queries.
Method Syntax

```kotlin
client.let(key, value)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `key`  | `String`  | The parameter name.  |  
| `value`  | `JsonElement`  | The parameter value.  |  
**Returns:** `JsonElement`
###  `.unset(key)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#unset)
Removes a previously defined session parameter.
Method Syntax

```kotlin
client.unset(key)
```

**Returns:** `JsonElement`
* * *
##  CRUD methods[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#crud-methods)
These methods return a [query builder](/docs/reference/kotlin/api/core/query-builder) that you refine and terminate with `await()` or [`awaitAs()`](/docs/reference/kotlin/api/core/query-builder#await-as). The `what` argument accepts a [`Table`](/docs/reference/kotlin/api/values/table), [`RecordId`](/docs/reference/kotlin/api/values/record-id), or [`RecordIdRange`](/docs/reference/kotlin/api/values/record-id-range).
###  `.select(what)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#select)
Returns a [`SelectQuery`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#select-query) for reading records.
Method Syntax

```kotlin
client.select(what)
```

**Returns:** `SelectQuery`
Example

```kotlin
val all: List<Person> = client.select(Table("person")).awaitAs()
```

###  `.create(what)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#create)
Returns a [`CreateQuery`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#create-query) for inserting a record.
Method Syntax

```kotlin
client.create(what)
```

**Returns:** `CreateQuery`
###  `.update(what)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#update)
Returns an `UpdateQuery` for replacing record content.
Method Syntax

```kotlin
client.update(what)
```

**Returns:** `UpdateQuery`
###  `.upsert(what)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#upsert)
Returns an `UpsertQuery` for creating or updating records.
Method Syntax

```kotlin
client.upsert(what)
```

**Returns:** `UpsertQuery`
###  `.merge(what, data)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#merge)
Returns a `MergeQuery` that merges `data` into the matched records.
Method Syntax

```kotlin
client.merge(what, data)
```

**Returns:** `MergeQuery`
###  `.patch(what, patches, diff)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#patch)
Returns a `PatchQuery` that applies [JSON Patch](https://jsonpatch.com/) operations.
Method Syntax

```kotlin
client.patch(what, patches, diff = false)
```

**Returns:** `PatchQuery`
###  `.delete(what)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#delete)
Returns a `DeleteQuery` for removing records.
Method Syntax

```kotlin
client.delete(what)
```

**Returns:** `DeleteQuery`
###  `.relate(in, relation, out)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#relate)
Returns a `RelateQuery` that creates a graph edge between two records.
Method Syntax

```kotlin
client.relate(`in`, relation, out)
```

**Returns:** `RelateQuery`
###  `.insert(into, data)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#insert)
Returns an `InsertQuery` that inserts one or more records into a [`Table`](https://surrealdb.com/docs/reference/kotlin/api/values/table).
Method Syntax

```kotlin
client.insert(into, data)
```

**Returns:** `InsertQuery`
###  `.insertRelation(into, data)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#insert-relation)
Returns an `InsertRelationQuery` that inserts relation records into a [`Table`](https://surrealdb.com/docs/reference/kotlin/api/values/table).
Method Syntax

```kotlin
client.insertRelation(into, data)
```

**Returns:** `InsertRelationQuery`
###  `.run(function)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#run)
Returns a `RunQuery` that invokes a built-in or custom [function](https://surrealdb.com/docs/reference/query-language/functions/database-functions).
Method Syntax

```kotlin
client.run(function)
```

**Returns:** `RunQuery`
* * *
##  Live query methods[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#live-query-methods)
###  `.live(table, diff)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#live)
Starts a [live query](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries) and returns a [`LiveQuerySubscription`](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription). **WebSocket only.**
Method Syntax

```kotlin
client.live(table, diff = null)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `String`  | The table to watch.  |  
| `diff`  | `Boolean?`  |  When `true`, emit JSON Patch diffs instead of full records.  |  
**Returns:** `LiveQuerySubscription`
###  `.kill(liveQueryId)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#kill)
Kills a live query by its ID. **WebSocket only.**
Method Syntax

```kotlin
client.kill(liveQueryId)
```

**Returns:** `JsonElement`
* * *
##  Sessions[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#sessions)
###  `.newSession()`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#new-session)
Creates a new isolated [`SurrealSession`](https://surrealdb.com/docs/reference/kotlin/api/core/session) over the same connection. **WebSocket only.**
Method Syntax

```kotlin
client.newSession()
```

**Returns:** `SurrealSession`
###  `.closeSession(session)`[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#close-session)
Closes a session previously created with [`.newSession()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#new-session).
Method Syntax

```kotlin
client.closeSession(session)
```

**Returns:** `Unit`
* * *
##  Properties[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#properties)  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `config`  | `SurrealClientConfig`  | The configuration the client was created with.  |  
| `features`  | `Set<SurrealFeature>`  | The features supported by the active transport.  |  
| `connectionEvents`  | `SharedFlow<SurrealConnectionEvent>`  | A flow of connection lifecycle events.  |  
| `json`  | `Json`  |  The `kotlinx.serialization`instance used for encoding and decoding.  |  
##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#learn-more)
  * •
[Client configuration](https://surrealdb.com/docs/reference/kotlin/api/core/client-config)
  * •
[Session](https://surrealdb.com/docs/reference/kotlin/api/core/session)
  * •
[Query builder](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder)
  * •
[Features and events](https://surrealdb.com/docs/reference/kotlin/api/features)
  * •
[Errors](https://surrealdb.com/docs/reference/kotlin/api/errors)
