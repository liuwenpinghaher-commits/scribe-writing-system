---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/serialization"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/serialization"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/serialization

Source: https://surrealdb.com/docs/reference/kotlin/concepts/serialization

The Kotlin SDK uses [`kotlinx.serialization`](https://github.com/Kotlin/kotlinx.serialization) as its data model. Payloads are sent and received as JSON, so you work with [`JsonElement`](https://surrealdb.com/docs/reference/kotlin/concepts/value-types) values directly, or decode them into your own [`@Serializable`](https://kotlinlang.org/api/kotlinx.serialization/kotlinx-serialization-core/kotlinx.serialization/-serializable/) types.
##  Defining serializable types[](https://surrealdb.com/docs/reference/kotlin/concepts/serialization#defining-serializable-types)
Annotate your data classes with `@Serializable`. Field names map directly to record fields; use `@SerialName` to map a different key.

```kotlin
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Person(
    val name: String,
    val age: Int,
    @SerialName("created_at") val createdAt: String? = null,
)
```

##  Decoding query results[](https://surrealdb.com/docs/reference/kotlin/concepts/serialization#decoding-query-results)
The inline [`.queryAs()`](/docs/reference/kotlin/api/core/surreal-client#query-as) helper runs a query and decodes its result into `T`, while every fluent builder offers the typed [`.awaitAs()`](/docs/reference/kotlin/api/core/query-builder#await-as) terminal.

```kotlin
import com.surrealdb.kotlin.query.Table
import com.surrealdb.kotlin.query.awaitAs

// Via raw SurrealQL
val people: List<Person> = client.queryAs("SELECT * FROM person")

// Via a builder
val sameAgain: List<Person> = client.select(Table("person")).awaitAs()
```

To decode an arbitrary [`JsonElement`](/docs/reference/kotlin/concepts/value-types) you already hold, use [`.decode()`](/docs/reference/kotlin/api/core/surreal-client#decode).

```kotlin
val element = client.query("SELECT * FROM person:ada")
val ada: Person = client.decode(element)
```

##  Building payloads[](https://surrealdb.com/docs/reference/kotlin/concepts/serialization#building-payloads)
When writing data, build a [`JsonObject`](https://surrealdb.com/docs/reference/kotlin/concepts/value-types) with [`buildJsonObject`](https://kotlinlang.org/api/kotlinx.serialization/kotlinx-serialization-json/kotlinx.serialization.json/build-json-object.html), or encode a serializable instance with the client's [`json`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#json) instance.

```kotlin
import kotlinx.serialization.json.encodeToJsonElement

val data = client.json.encodeToJsonElement(Person("Ada", 36))
client.create(com.surrealdb.kotlin.query.Table("person")).content(data).await()
```

##  Customising the JSON format[](https://surrealdb.com/docs/reference/kotlin/concepts/serialization#customising-the-json-format)
The [`json`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config#json) field on [`SurrealClientConfig`](https://surrealdb.com/docs/reference/kotlin/api/core/client-config) lets you supply a custom [`Json`](https://kotlinlang.org/api/kotlinx.serialization/kotlinx-serialization-json/kotlinx.serialization.json/-json/) instance, for example to register contextual serializers or change null handling. The default ignores unknown keys and is lenient.

```kotlin
import kotlinx.serialization.json.Json

val client = SurrealClient(
    SurrealClientConfig(
        url = "ws://localhost:8000",
        json = Json {
            ignoreUnknownKeys = true
            isLenient = true
            explicitNulls = false
        },
    ),
)
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/serialization#learn-more)
  * •
[Value types](https://surrealdb.com/docs/reference/kotlin/concepts/value-types) for `Table`, `RecordId`, and the JSON model
  * •
[Executing queries](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries) for `queryAs`
  * •
[Query builder reference](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder) for `awaitAs`
  * •
[kotlinx.serialization](https://kotlinlang.org/docs/serialization.html) for the underlying library
