---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb

Source: https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb

The first step towards interacting with [SurrealDB](https://surrealdb.com/docs/start) is to create a connection to a database instance. This involves constructing a [`SurrealClient`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) with a [`SurrealClientConfig`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config), then selecting a namespace and database. The SDK supports remote connections over WebSocket and HTTP.
##  API references[](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`SurrealClient(config)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#constructor)  | Creates a new client from a configuration  |  
| [`client.connect()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#connect)  | Establishes the connection explicitly  |  
| [`client.close()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#close)  | Closes the connection and releases resources  |  
| [`client.use(ns, db)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#use)  | Selects a namespace and database  |  
| [`client.version()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#version)  | Returns the server version  |  
| [`client.ping()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#ping)  | Pings the server  |  
##  Opening a connection[](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb#opening-a-connection)
Construct a [`SurrealClient`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) with a [`SurrealClientConfig`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config) whose `url` points at your SurrealDB instance. By default (`autoConnect = true`) the client connects lazily on the first request, so you rarely need to call [`.connect()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#connect) yourself.

```kotlin
import com.surrealdb.kotlin.SurrealClient
import com.surrealdb.kotlin.SurrealClientConfig

val client = SurrealClient(SurrealClientConfig(url = "ws://localhost:8000"))
```

##  Connection string protocols[](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb#connection-string-protocols)
The URL scheme determines the transport. For more on server configuration, see the [start command](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start) documentation.  
| Protocol  | Description  |  
| --- | --- |  
| `ws://`  | Plain WebSocket connection  |  
| `wss://`  | Secure WebSocket connection (TLS)  |  
| `http://`  | Plain HTTP connection  |  
| `https://`  | Secure HTTP connection (TLS)  |  
The WebSocket engine maintains a single long-lived connection, while the HTTP engine issues a request per call.
##  Feature support by protocol[](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb#feature-support-by-protocol)
Not all features are available on every transport. You can check support at runtime with [`.supports()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#supports); unsupported calls throw [`SurrealFeatureNotSupportedException`](https://surrealdb.com/docs/reference/kotlin/api/errors).  
| Feature  | WebSocket  | HTTP  |  
| --- | --- | --- |  
| Authentication  | Yes  | Yes  |  
| Queries  | Yes  | Yes  |  
| CRUD operations  | Yes  | Yes  |  
| Live queries  | Yes  | No  |  
| Transactions  | Yes  | No  |  
| Multiple sessions  | Yes  | No  |  
| Refresh tokens  | Yes  | No  |  
| Export / Import  | Yes  | Yes  |  
| SurrealML  | Yes  | Yes  |  
See [Features and events](https://surrealdb.com/docs/reference/kotlin/api/features) for the full [`SurrealFeature`](https://surrealdb.com/docs/reference/kotlin/api/features#feature) enum.
##  Selecting a namespace and database[](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb#selecting-a-namespace-and-database)
After connecting, select a [namespace](https://surrealdb.com/docs/reference/query-language/statements/define/namespace) and [database](https://surrealdb.com/docs/reference/query-language/statements/define/database) with [`.use()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#use).

```kotlin
client.use("surrealdb", "docs")
```

##  Reconnection[](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb#reconnection)
The WebSocket engine automatically reconnects with exponential backoff. Tune this through the [`ReconnectConfig`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config#reconnect-config) on your [`SurrealClientConfig`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config).

```kotlin
import com.surrealdb.kotlin.SurrealClientConfig
import com.surrealdb.kotlin.engine.ReconnectConfig

val client = SurrealClient(
    SurrealClientConfig(
        url = "wss://example.com",
        reconnect = ReconnectConfig(
            enabled = true,
            initialDelayMillis = 250,
            maxDelayMillis = 30_000,
            multiplier = 1.5,
            maxAttempts = null, // null means retry indefinitely
        ),
    ),
)
```

##  Observing connection events[](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb#observing-connection-events)
The client exposes a [`connectionEvents`](https://surrealdb.com/docs/reference/kotlin/api/features#connection-events) [`SharedFlow`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-shared-flow/) you can collect to react to lifecycle changes.

```kotlin
import com.surrealdb.kotlin.engine.SurrealConnectionEvent
import kotlinx.coroutines.launch

scope.launch {
    client.connectionEvents.collect { event ->
        when (event) {
            is SurrealConnectionEvent.Connected -> println("connected")
            is SurrealConnectionEvent.Reconnecting -> println("reconnecting, attempt ${event.attempt}")
            is SurrealConnectionEvent.Disconnected -> println("disconnected")
            is SurrealConnectionEvent.Error -> println("error: ${event.cause.message}")
            else -> {}
        }
    }
}
```

##  Closing a connection[](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb#closing-a-connection)
Call [`.close()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#close) to release all resources associated with the connection.

```kotlin
client.close()
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb#learn-more)
  * •
[SurrealClient API reference](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) for complete method signatures
  * •
[Client configuration](https://surrealdb.com/docs/reference/kotlin/api/core/client-config) for all configuration options
  * •
[Authentication](https://surrealdb.com/docs/reference/kotlin/concepts/authentication) for signing in and managing sessions
  * •
[Error handling](https://surrealdb.com/docs/reference/kotlin/concepts/error-handling) for handling connection errors
