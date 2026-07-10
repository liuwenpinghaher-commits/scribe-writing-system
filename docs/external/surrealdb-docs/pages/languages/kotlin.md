---
title: "https://surrealdb.com/docs/languages/kotlin"
url: "https://surrealdb.com/docs/languages/kotlin"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/languages/kotlin

Source: https://surrealdb.com/docs/languages/kotlin

The Kotlin SDK for SurrealDB lets you connect to a database and query it from your application with coroutines. This guide covers connecting, authenticating, and running your first queries.
Note
Every network operation on the SDK is a `suspend` function, so the examples below run inside a coroutine (for example, a [`runBlocking`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/run-blocking.html) block or a `CoroutineScope`).
##  1. Install the SDK[](https://surrealdb.com/docs/languages/kotlin#1-install-the-sdk)
Follow the [installation guide](https://surrealdb.com/docs/reference/kotlin/installation) to add the SDK as a dependency in your project. Once installed, import the client to start using it.

```kotlin
import com.surrealdb.kotlin.SurrealClient
import com.surrealdb.kotlin.SurrealClientConfig
```

##  2. Connect to SurrealDB[](https://surrealdb.com/docs/languages/kotlin#2-connect-to-surrealdb)
Create a [`SurrealClient`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) with a [`SurrealClientConfig`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config), then call [`.use()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#use) to select a namespace and database, and [`.signin()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#signin) to authenticate.
The transport is selected automatically from the URL scheme:
  * •
**WebSocket** (`ws://`, `wss://`) for long-lived stateful connections that support live queries, transactions, and multiple sessions
  * •
**HTTP** (`http://`, `https://`) for short-lived stateless connections

```kotlin
import com.surrealdb.kotlin.SurrealClient
import com.surrealdb.kotlin.SurrealClientConfig
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

fun main() = runBlocking {
    val client = SurrealClient(SurrealClientConfig(url = "ws://localhost:8000"))

    client.signin(buildJsonObject {
        put("user", "root")
        put("pass", "root")
    })
    client.use("surrealdb", "docs")

    // ...

    client.close()
}
```

The client connects automatically on first use (`autoConnect` defaults to `true`). Call [`.close()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#close) when you are finished to release resources.
##  3. Inserting data into SurrealDB[](https://surrealdb.com/docs/languages/kotlin#3-inserting-data-into-surrealdb)
To represent records in your application, define [`@Serializable`](https://surrealdb.com/docs/reference/kotlin/concepts/serialization) data classes that match your table structure.

```kotlin
import kotlinx.serialization.Serializable

@Serializable
data class Person(val name: String, val age: Int)
```

Use the [`.create()`](/docs/reference/kotlin/api/core/surreal-client#create) builder to insert a record. Pass a [`Table`](/docs/reference/kotlin/api/values/table) to create in a table with a generated ID, or a [`RecordId`](/docs/reference/kotlin/api/values/record-id) to create a record with a specific ID. Builders are terminated with `await()` (raw JSON) or the typed [`awaitAs()`](/docs/reference/kotlin/api/core/query-builder#await-as) extension.

```kotlin
import com.surrealdb.kotlin.query.RecordId
import com.surrealdb.kotlin.query.Table
import com.surrealdb.kotlin.query.awaitAs
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

val created: Person = client
    .create(RecordId("person", "john"))
    .content(buildJsonObject {
        put("name", "John")
        put("age", 32)
    })
    .awaitAs()
```

##  4. Retrieving data from SurrealDB[](https://surrealdb.com/docs/languages/kotlin#4-retrieving-data-from-surrealdb)
###  Selecting records[](https://surrealdb.com/docs/languages/kotlin#selecting-records)
The [`.select()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#select) builder retrieves records from a table or a single record by its [`RecordId`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id). Refine it with [`.where()`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#where) using the [expression helpers](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#expressions).

```kotlin
import com.surrealdb.kotlin.query.Table
import com.surrealdb.kotlin.query.field
import com.surrealdb.kotlin.query.gte
import com.surrealdb.kotlin.query.awaitAs

val adults: List<Person> = client
    .select(Table("person"))
    .where(field("age") gte 18)
    .limit(50)
    .awaitAs()
```

###  Running SurrealQL queries[](https://surrealdb.com/docs/languages/kotlin#running-surrealql-queries)
For more advanced use cases, use [`.query()`](/docs/reference/kotlin/api/core/surreal-client#query) to execute [SurrealQL](/docs/reference/query-language) statements with bound [parameters](/docs/reference/query-language/language-primitives/parameters), or [`.queryAs()`](/docs/reference/kotlin/api/core/surreal-client#query-as) to decode the result directly.

```kotlin
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

val people: List<Person> = client.queryAs(
    "SELECT * FROM person WHERE age > \$min_age",
    buildJsonObject { put("min_age", 25) },
)
```

##  5. Closing the connection[](https://surrealdb.com/docs/languages/kotlin#5-closing-the-connection)
Call [`.close()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#close) to release the connection and all associated resources.

```kotlin
client.close()
```

##  Next steps[](https://surrealdb.com/docs/languages/kotlin#next-steps)
You have learned how to install the SDK, connect to SurrealDB, create records, and retrieve data. There is a lot more you can do with the SDK, including updating and deleting records, authentication, live queries, and transactions.
[Connecting to SurrealDB Learn how to manage connections, protocols, and reconnection.](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb)[Authentication Read more about authentication and how to integrate it into your application.](https://surrealdb.com/docs/reference/kotlin/concepts/authentication)[Data manipulation Learn how to create, read, update, and delete records using the builders.](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation)[API Reference Complete reference for the client, builders, types, and errors.](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client)
Note
This getting-started guide covers the essentials. For the complete methods, API, and concept reference, see the [Kotlin SDK reference](https://surrealdb.com/docs/reference/kotlin).
