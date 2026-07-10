---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/live-queries"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/live-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/live-queries

Source: https://surrealdb.com/docs/reference/kotlin/concepts/live-queries

[Live queries](https://surrealdb.com/docs/reference/query-language/statements/live-select) push changes to your application as records are created, updated, or deleted. In the Kotlin SDK, a live subscription exposes a coroutine [`Flow`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-flow/) of notifications that you collect.
Note
Live queries require a stateful connection and are only available over the **WebSocket** transport. Calling [`.live()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#live) over HTTP throws [`SurrealFeatureNotSupportedException`](https://surrealdb.com/docs/reference/kotlin/api/errors). Check support with [`client.supports(SurrealFeature.LiveQueries)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#supports).
##  API references[](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`client.live(table)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#live)  | Starts a live query and returns a subscription  |  
| [`subscription.events`](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#events)  |  A `Flow`of live notifications  |  
| [`subscription.cancel()`](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#cancel)  | Stops the subscription  |  
| [`client.kill(id)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#kill)  | Kills a live query by ID  |  
##  Starting a live query[](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries#starting-a-live-query)
Call [`.live()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#live) with a table name to receive a [`LiveQuerySubscription`](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription), then collect its [`events`](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#events) flow. Each [`SurrealLiveNotification`](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#notification) carries an `action` (`"CREATE"`, `"UPDATE"`, or `"DELETE"`) and a `result` payload.

```kotlin
import com.surrealdb.kotlin.SurrealFeature
import kotlinx.coroutines.launch

if (client.supports(SurrealFeature.LiveQueries)) {
    val subscription = client.live("person")

    val job = scope.launch {
        subscription.events.collect { event ->
            println("${event.action}: ${event.result}")
        }
    }
}
```

Pass `diff = true` to receive [JSON Patch](https://jsonpatch.com/) diffs instead of the full record.

```kotlin
val subscription = client.live("person", diff = true)
```

##  Filtered live queries[](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries#filtered-live-queries)
To watch a subset of records with a `WHERE` clause, run a `LIVE SELECT` statement through [`.query()`](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries); the result is the live query UUID, which you can later pass to [`.kill()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#kill).

```kotlin
val liveId = client.query("LIVE SELECT * FROM person WHERE age >= 18")
```

##  Stopping a subscription[](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries#stopping-a-subscription)
Cancel a subscription started with [`.live()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#live) by calling [`.cancel()`](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#cancel), which also kills the underlying live query on the server. Cancel the collecting coroutine separately.

```kotlin
subscription.cancel()
job.cancel()
```

For live queries started via raw SurrealQL, kill them with their UUID.

```kotlin
client.kill(liveId.toString())
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries#learn-more)
  * •
[Live subscription reference](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription) for the subscription and notification types
  * •
[SurrealClient API reference](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) for `.live()` and `.kill()`
  * •
[Features and events](https://surrealdb.com/docs/reference/kotlin/api/features) for checking transport support
  * •
[LIVE SELECT](https://surrealdb.com/docs/reference/query-language/statements/live-select) for the SurrealQL statement
