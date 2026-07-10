---
title: "https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription"
url: "https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription

Source: https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription

`LiveQuerySubscription` is returned by [`.live()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#live). It exposes a coroutine [`Flow`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-flow/) of notifications and a method to stop the subscription. See [Live queries](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries) for the concept.
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.live.LiveQuerySubscription
```

* * *
##  Members[](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#members)
###  `id`[](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#id)
The server-assigned live query ID.
**Type:** `String`
###  `events`[](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#events)
A flow of [`SurrealLiveNotification`](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#notification) events for this subscription.
**Type:** `Flow`
Example

```kotlin
subscription.events.collect { event ->
    println("${event.action}: ${event.result}")
}
```

###  `.cancel()`[](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#cancel)
Stops the subscription and kills the underlying live query on the server.
Method Syntax

```kotlin
subscription.cancel()
```

**Returns:** `Unit`
* * *
##  `SurrealLiveNotification`[](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#notification)
The payload emitted on the [`events`](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#events) flow.
Import

```kotlin
import com.surrealdb.kotlin.model.SurrealLiveNotification
```
  
| Field  | Type  | Description  |  
| --- | --- | --- |  
| `action`  | `String`  |  The change kind: `"CREATE"`, `"UPDATE"`, or `"DELETE"`.  |  
| `liveQueryId`  | `String`  | The ID of the originating live query.  |  
| `result`  | `JsonElement`  | The changed record or diff.  |  
##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/core/live-subscription#learn-more)
  * •
[Live queries](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries)
  * •
[SurrealClient API reference](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) for `.live()` and `.kill()`
