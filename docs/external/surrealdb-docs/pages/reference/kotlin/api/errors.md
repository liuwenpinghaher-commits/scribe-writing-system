---
title: "https://surrealdb.com/docs/reference/kotlin/api/errors"
url: "https://surrealdb.com/docs/reference/kotlin/api/errors"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/errors

Source: https://surrealdb.com/docs/reference/kotlin/api/errors

The Kotlin SDK raises exceptions that all extend the sealed base class `SurrealException`. Because the hierarchy is sealed, you can branch over it exhaustively with `when`. See [Error handling](https://surrealdb.com/docs/reference/kotlin/concepts/error-handling) for usage patterns and the [`Result` variants](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#result-variants) that avoid exceptions altogether.
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.error.SurrealException
```

* * *
##  `SurrealException`[](https://surrealdb.com/docs/reference/kotlin/api/errors#surreal-exception)
The sealed base class of all SDK exceptions. Extends `RuntimeException`.
##  `SurrealTransportException`[](https://surrealdb.com/docs/reference/kotlin/api/errors#transport)
Raised when the underlying connection fails, drops, or cannot be established.
##  `SurrealProtocolException`[](https://surrealdb.com/docs/reference/kotlin/api/errors#protocol)
Raised when a malformed or unexpected message is received from the server.
##  `SurrealRpcException`[](https://surrealdb.com/docs/reference/kotlin/api/errors#rpc)
Raised when the server returns an RPC error.  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `code`  | `Int?`  | The RPC error code.  |  
| `data`  | `JsonElement?`  | Additional error data from the server.  |  
##  `SurrealAuthenticationException`[](https://surrealdb.com/docs/reference/kotlin/api/errors#authentication)
A subclass of [`SurrealRpcException`](https://surrealdb.com/docs/reference/kotlin/api/errors#rpc) raised when authentication fails (for example, invalid credentials or an expired token).
##  `SurrealFeatureNotSupportedException`[](https://surrealdb.com/docs/reference/kotlin/api/errors#feature-not-supported)
Raised when a feature is invoked that the current transport does not support — for example a [live query](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries) or [transaction](https://surrealdb.com/docs/reference/kotlin/concepts/transactions) over HTTP. Extends the base [`SurrealException`](https://surrealdb.com/docs/reference/kotlin/api/errors#surreal-exception). Guard against it with [`.supports()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#supports).
Example

```kotlin
import com.surrealdb.kotlin.error.SurrealAuthenticationException
import com.surrealdb.kotlin.error.SurrealException

try {
    client.signin(buildJsonObject { put("user", "root"); put("pass", "wrong") })
} catch (e: SurrealAuthenticationException) {
    println("authentication failed: ${e.message}")
} catch (e: SurrealException) {
    println("error: ${e.message}")
}
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/errors#learn-more)
  * •
[Error handling](https://surrealdb.com/docs/reference/kotlin/concepts/error-handling)
  * •
[Features and events](https://surrealdb.com/docs/reference/kotlin/api/features)
