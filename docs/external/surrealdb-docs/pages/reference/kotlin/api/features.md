---
title: "https://surrealdb.com/docs/reference/kotlin/api/features"
url: "https://surrealdb.com/docs/reference/kotlin/api/features"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/features

Source: https://surrealdb.com/docs/reference/kotlin/api/features

The SDK exposes the capabilities of the active transport as a set of [`SurrealFeature`](https://surrealdb.com/docs/reference/kotlin/api/features#feature) values, and the lifecycle of the connection as a stream of [`SurrealConnectionEvent`](https://surrealdb.com/docs/reference/kotlin/api/features#connection-events).
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.SurrealFeature
import com.surrealdb.kotlin.engine.SurrealConnectionEvent
```

* * *
##  `SurrealFeature`[](https://surrealdb.com/docs/reference/kotlin/api/features#feature)
An enum of the features a transport may support. Inspect the active set via the [`features`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#properties) property, or check a single feature with [`.supports()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#supports).  
| Value  | Available on  |  
| --- | --- |  
| `LiveQueries`  | WebSocket  |  
| `Transactions`  | WebSocket  |  
| `Sessions`  | WebSocket  |  
| `RefreshTokens`  | WebSocket  |  
| `ExportImport`  | WebSocket, HTTP  |  
| `SurrealML`  | WebSocket, HTTP  |  
Example

```kotlin
if (client.supports(SurrealFeature.LiveQueries)) {
    val subscription = client.live("person")
}
```

* * *
##  `SurrealConnectionEvent`[](https://surrealdb.com/docs/reference/kotlin/api/features#connection-events)
A sealed class emitted on the client's [`connectionEvents`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#properties) [`SharedFlow`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-shared-flow/).  
| Variant  | Payload  | Description  |  
| --- | --- | --- |  
| `Connecting`  | —  | A connection attempt has started.  |  
| `Connected`  | —  | The connection is established.  |  
| `Disconnected`  | —  | The connection has dropped.  |  
| `Reconnecting`  |  `attempt: Int`, `delayMillis: Long`  | A reconnect is scheduled.  |  
| `Error`  | `cause: Throwable`  | A connection error occurred.  |  
Example

```kotlin
client.connectionEvents.collect { event ->
    when (event) {
        is SurrealConnectionEvent.Connected -> println("connected")
        is SurrealConnectionEvent.Reconnecting -> println("attempt ${event.attempt}")
        is SurrealConnectionEvent.Error -> println("error: ${event.cause.message}")
        else -> {}
    }
}
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/features#learn-more)
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb)
  * •
[SurrealClient API reference](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client)
