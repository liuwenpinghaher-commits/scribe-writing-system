---
title: "https://surrealdb.com/docs/reference/kotlin/api/values/value"
url: "https://surrealdb.com/docs/reference/kotlin/api/values/value"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/values/value

Source: https://surrealdb.com/docs/reference/kotlin/api/values/value

The Kotlin SDK models all data — beyond the dedicated [record types](https://surrealdb.com/docs/reference/kotlin/api/values/record-id) — using [`kotlinx.serialization`](https://surrealdb.com/docs/reference/kotlin/concepts/serialization) JSON types. Read methods return a [`JsonElement`](https://kotlinlang.org/api/kotlinx.serialization/kotlinx-serialization-json/kotlinx.serialization.json/-json-element/); write methods accept a [`JsonObject`](https://kotlinlang.org/api/kotlinx.serialization/kotlinx-serialization-json/kotlinx.serialization.json/-json-object/).
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
```

* * *
##  Building values[](https://surrealdb.com/docs/reference/kotlin/api/values/value#building-values)
Construct objects with [`buildJsonObject`](https://kotlinlang.org/api/kotlinx.serialization/kotlinx-serialization-json/kotlinx.serialization.json/build-json-object.html).
Example

```kotlin
val data = buildJsonObject {
    put("name", "Ada")
    put("age", 36)
}
```

##  Decoding values[](https://surrealdb.com/docs/reference/kotlin/api/values/value#decoding-values)
Rather than navigating raw `JsonElement` trees, decode results into your own [`@Serializable`](/docs/reference/kotlin/concepts/serialization) types with [`.queryAs()`](/docs/reference/kotlin/api/core/surreal-client#query-as), [`.awaitAs()`](/docs/reference/kotlin/api/core/query-builder#await-as), or [`.decode()`](/docs/reference/kotlin/api/core/surreal-client#decode).
Example

```kotlin
val people: List<Person> = client.queryAs("SELECT * FROM person")
```

Note
The SDK does not provide dedicated wrapper classes for datetimes, durations, or geometries. Express these as SurrealQL literals or the JSON values SurrealDB expects, and decode results into your own types.
##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/values/value#learn-more)
  * •
[Value types](https://surrealdb.com/docs/reference/kotlin/concepts/value-types)
  * •
[Serialization](https://surrealdb.com/docs/reference/kotlin/concepts/serialization)
