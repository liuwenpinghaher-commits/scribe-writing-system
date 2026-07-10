---
title: "https://surrealdb.com/docs/reference/kotlin/api/core/client-config"
url: "https://surrealdb.com/docs/reference/kotlin/api/core/client-config"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/core/client-config

Source: https://surrealdb.com/docs/reference/kotlin/api/core/client-config

`SurrealClientConfig` configures a [`SurrealClient`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client). The only required field is `url`; everything else has a sensible default.
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.SurrealClientConfig
```

* * *
##  Fields[](https://surrealdb.com/docs/reference/kotlin/api/core/client-config#fields)  
| Field  | Type  | Default  | Description  |  
| --- | --- | --- | --- |  
| `url`  | `String`  | —  |  The connection URL. The scheme ( `ws`/ `wss`/ `http`/ `https`) selects the transport.  |  
| `json`  | `Json`  | lenient  |  The `kotlinx.serialization`instance used for encoding and decoding.  |  
| `autoConnect`  | `Boolean`  | `true`  | Connect lazily on the first request.  |  
| `autoAuthenticate`  | `Boolean`  | `false`  |  Authenticate automatically using `credentialProvider`on connect and reconnect.  |  
| `credentialProvider`  | `(suspend () -> SurrealAuthInput?)?`  | `null`  | Supplies credentials for automatic authentication and token renewal.  |  
| `requestTimeoutMillis`  | `Long`  | `30_000`  | Per-request timeout in milliseconds.  |  
| `reconnect`  | `ReconnectConfig`  | `ReconnectConfig()`  | WebSocket reconnection behaviour.  |  
| `tokenRenewalLeadMillis`  | `Long`  | `60_000`  | How long before token expiry to renew, in milliseconds.  |  
| `httpClientFactory`  | `((SurrealClientConfig) -> HttpClient)?`  | `null`  |  Supplies a custom Ktor `HttpClient`.  |  
Example

```kotlin
import com.surrealdb.kotlin.SurrealAuthInput
import com.surrealdb.kotlin.SurrealClientConfig
import com.surrealdb.kotlin.engine.ReconnectConfig
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

val config = SurrealClientConfig(
    url = "wss://example.com",
    requestTimeoutMillis = 30_000,
    autoAuthenticate = true,
    tokenRenewalLeadMillis = 60_000,
    reconnect = ReconnectConfig(enabled = true, multiplier = 1.5),
    credentialProvider = {
        SurrealAuthInput.SignIn(buildJsonObject {
            put("user", "root")
            put("pass", "root")
        })
    },
)
```

* * *
##  `ReconnectConfig`[](https://surrealdb.com/docs/reference/kotlin/api/core/client-config#reconnect-config)
Controls exponential-backoff reconnection on the WebSocket transport.
Import

```kotlin
import com.surrealdb.kotlin.engine.ReconnectConfig
```
  
| Field  | Type  | Default  | Description  |  
| --- | --- | --- | --- |  
| `enabled`  | `Boolean`  | `true`  | Whether reconnection is attempted.  |  
| `initialDelayMillis`  | `Long`  | `250`  | Delay before the first retry.  |  
| `maxDelayMillis`  | `Long`  | `30_000`  | Maximum delay between retries.  |  
| `multiplier`  | `Double`  | `1.5`  | Backoff multiplier applied each attempt.  |  
| `maxAttempts`  | `Int?`  | `null`  |  Maximum attempts; `null`retries indefinitely.  |  
* * *
##  `SurrealAuthInput`[](https://surrealdb.com/docs/reference/kotlin/api/core/client-config#surreal-auth-input)
A sealed interface describing how `credentialProvider` should authenticate.
Import

```kotlin
import com.surrealdb.kotlin.SurrealAuthInput
```
  
| Variant  | Payload  | Description  |  
| --- | --- | --- |  
| `SurrealAuthInput.SignIn`  | `params: JsonObject`  | Sign in with credentials.  |  
| `SurrealAuthInput.Token`  | `token: String`  | Authenticate with an existing token.  |  
##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/core/client-config#learn-more)
  * •
[SurrealClient API reference](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client)
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb)
  * •
[Authentication](https://surrealdb.com/docs/reference/kotlin/concepts/authentication)
