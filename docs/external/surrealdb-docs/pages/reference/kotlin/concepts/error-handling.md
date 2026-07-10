---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/error-handling"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/error-handling"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/error-handling

Source: https://surrealdb.com/docs/reference/kotlin/concepts/error-handling

Networked operations on the SDK throw a [`SurrealException`](https://surrealdb.com/docs/reference/kotlin/api/errors) on failure, or you can use the [`Result` variants](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#result-variants) to handle failures functionally without exceptions.
##  Exception hierarchy[](https://surrealdb.com/docs/reference/kotlin/concepts/error-handling#exception-hierarchy)
All SDK exceptions extend the sealed base [`SurrealException`](https://surrealdb.com/docs/reference/kotlin/api/errors).  
| Exception  | Raised when  |  
| --- | --- |  
| [`SurrealTransportException`](https://surrealdb.com/docs/reference/kotlin/api/errors#transport)  | The connection fails or drops  |  
| [`SurrealProtocolException`](https://surrealdb.com/docs/reference/kotlin/api/errors#protocol)  | A malformed or unexpected protocol message is received  |  
| [`SurrealRpcException`](https://surrealdb.com/docs/reference/kotlin/api/errors#rpc)  | The server returns an RPC error (carries `code` and `data`)  |  
| [`SurrealAuthenticationException`](https://surrealdb.com/docs/reference/kotlin/api/errors#authentication)  | Authentication fails (a subclass of `SurrealRpcException`)  |  
| [`SurrealFeatureNotSupportedException`](https://surrealdb.com/docs/reference/kotlin/api/errors#feature-not-supported)  | A feature is unavailable on the current transport  |  
##  Catching exceptions[](https://surrealdb.com/docs/reference/kotlin/concepts/error-handling#catching-exceptions)
Because [`SurrealException`](https://surrealdb.com/docs/reference/kotlin/api/errors) is a sealed class, you can exhaustively branch on it with `when`.

```kotlin
import com.surrealdb.kotlin.error.SurrealAuthenticationException
import com.surrealdb.kotlin.error.SurrealException
import com.surrealdb.kotlin.error.SurrealRpcException
import com.surrealdb.kotlin.error.SurrealTransportException

try {
    client.signin(buildJsonObject {
        put("user", "root")
        put("pass", "wrong")
    })
} catch (e: SurrealAuthenticationException) {
    println("bad credentials: ${e.message}")
} catch (e: SurrealRpcException) {
    println("server error ${e.code}: ${e.message}")
} catch (e: SurrealTransportException) {
    println("connection problem: ${e.message}")
} catch (e: SurrealException) {
    println("unexpected: ${e.message}")
}
```

##  Feature support errors[](https://surrealdb.com/docs/reference/kotlin/concepts/error-handling#feature-support-errors)
Calling a feature that the current transport does not support — for example a [live query](https://surrealdb.com/docs/reference/kotlin/concepts/live-queries) over HTTP — throws [`SurrealFeatureNotSupportedException`](https://surrealdb.com/docs/reference/kotlin/api/errors#feature-not-supported). Guard against this with [`.supports()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#supports).

```kotlin
import com.surrealdb.kotlin.SurrealFeature

if (client.supports(SurrealFeature.LiveQueries)) {
    val subscription = client.live("person")
}
```

##  Using Result variants[](https://surrealdb.com/docs/reference/kotlin/concepts/error-handling#using-result-variants)
Each networked method has a `...Result` companion that wraps the outcome in a [`Result`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/-result/) instead of throwing.

```kotlin
client.queryResult("SELECT * FROM person")
    .onSuccess { println("got $it") }
    .onFailure { println("failed: ${it.message}") }
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/error-handling#learn-more)
  * •
[Errors reference](https://surrealdb.com/docs/reference/kotlin/api/errors) for every exception type
  * •
[Features and events](https://surrealdb.com/docs/reference/kotlin/api/features) for checking transport support
  * •
[Executing queries](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries) for the `Result` variants
