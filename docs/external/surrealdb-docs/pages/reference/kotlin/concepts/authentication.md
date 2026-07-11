---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/authentication"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/authentication"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/authentication

Source: https://surrealdb.com/docs/reference/kotlin/concepts/authentication

The Kotlin SDK supports the full range of SurrealDB [authentication](https://surrealdb.com/docs/learn/security/authentication/authentication) methods: root, namespace, and database users, as well as record (scoped) access. Credentials are supplied as a [`JsonObject`](https://surrealdb.com/docs/reference/kotlin/concepts/value-types), built with [`buildJsonObject`](https://kotlinlang.org/api/kotlinx.serialization/kotlinx-serialization-json/kotlinx.serialization.json/build-json-object.html).
##  API references[](https://surrealdb.com/docs/reference/kotlin/concepts/authentication#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`client.signup(params)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#signup)  | Signs up against a record access method  |  
| [`client.signin(params)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#signin)  | Signs in with credentials  |  
| [`client.authenticate(token)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#authenticate)  | Authenticates with an existing token  |  
| [`client.auth()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#auth)  | Returns the current authentication record  |  
| [`client.invalidate()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#invalidate)  | Invalidates the current session authentication  |  
| [`client.reset()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#reset)  | Resets the session to an unauthenticated state  |  
##  Signing in[](https://surrealdb.com/docs/reference/kotlin/concepts/authentication#signing-in)
Use [`.signin()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#signin) with the credentials appropriate to the [level of access](https://surrealdb.com/docs/learn/security/authentication/authentication) you need. It returns the authentication token as a [`JsonElement`](https://surrealdb.com/docs/reference/kotlin/concepts/value-types).

```kotlin
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

// Root user
client.signin(buildJsonObject {
    put("user", "root")
    put("pass", "root")
})

// Database user
client.signin(buildJsonObject {
    put("namespace", "surrealdb")
    put("database", "docs")
    put("user", "admin")
    put("pass", "secret")
})
```

##  Signing up[](https://surrealdb.com/docs/reference/kotlin/concepts/authentication#signing-up)
Use [`.signup()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#signup) to register against a [record access](https://surrealdb.com/docs/reference/query-language/statements/define/access/record) method.

```kotlin
val token = client.signup(buildJsonObject {
    put("namespace", "surrealdb")
    put("database", "docs")
    put("access", "user")
    put("email", "ada@example.com")
    put("password", "hunter2")
})
```

##  Authenticating with a token[](https://surrealdb.com/docs/reference/kotlin/concepts/authentication#authenticating-with-a-token)
If you already hold a token (for example from a previous session), authenticate the connection with [`.authenticate()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#authenticate).

```kotlin
client.authenticate("eyJ0eXAiOiJKV1Qi...")
```

##  Inspecting and clearing authentication[](https://surrealdb.com/docs/reference/kotlin/concepts/authentication#inspecting-and-clearing-authentication)
Retrieve the currently authenticated record with [`.auth()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#auth), drop the authentication while keeping the connection open with [`.invalidate()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#invalidate), or fully reset the session state with [`.reset()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#reset).

```kotlin
val me = client.auth()
client.invalidate()
client.reset()
```

##  Automatic authentication and token renewal[](https://surrealdb.com/docs/reference/kotlin/concepts/authentication#automatic-authentication-and-token-renewal)
The client can authenticate automatically on connect and after reconnects, and renew tokens shortly before they expire. Provide a `credentialProvider` and enable `autoAuthenticate` on your [`SurrealClientConfig`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config). The provider returns a [`SurrealAuthInput`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config#surreal-auth-input) — either a `SignIn` with credentials or an existing `Token`.

```kotlin
import com.surrealdb.kotlin.SurrealAuthInput
import com.surrealdb.kotlin.SurrealClientConfig
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

val client = SurrealClient(
    SurrealClientConfig(
        url = "wss://example.com",
        autoAuthenticate = true,
        tokenRenewalLeadMillis = 60_000, // renew 60s before expiry
        credentialProvider = {
            SurrealAuthInput.SignIn(buildJsonObject {
                put("user", "root")
                put("pass", "root")
            })
        },
    ),
)
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/authentication#learn-more)
  * •
[SurrealClient API reference](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) for complete method signatures
  * •
[Client configuration](https://surrealdb.com/docs/reference/kotlin/api/core/client-config) for `credentialProvider` and renewal options
  * •
[Multiple sessions](https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions) for per-session authentication
  * •
[SurrealDB authentication](https://surrealdb.com/docs/learn/security/authentication/authentication) for an overview of authentication concepts
