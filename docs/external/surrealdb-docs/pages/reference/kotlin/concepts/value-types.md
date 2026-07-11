---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/value-types"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/value-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/value-types

Source: https://surrealdb.com/docs/reference/kotlin/concepts/value-types

The Kotlin SDK represents data with [`kotlinx.serialization`](https://surrealdb.com/docs/reference/kotlin/concepts/serialization) JSON values, plus a small set of dedicated types for referring to tables and records. These are the building blocks passed to the [CRUD builders](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation) and queries.
##  Record and table types[](https://surrealdb.com/docs/reference/kotlin/concepts/value-types#record-and-table-types)  
| Type  | Description  |  
| --- | --- |  
| [`Table`](https://surrealdb.com/docs/reference/kotlin/api/values/table)  | Refers to a table by name  |  
| [`RecordId`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id)  | Refers to a single record (`table:id`)  |  
| [`RecordIdRange`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range)  | Refers to a range of records within a table  |  

```kotlin
import com.surrealdb.kotlin.query.RecordId
import com.surrealdb.kotlin.query.Table

val table = Table("person")
val record = RecordId("person", "ada")
```

When these are bound into a query, the SDK renders them with the appropriate SurrealDB casting functions — `type::table(name)` for a [`Table`](https://surrealdb.com/docs/reference/kotlin/api/values/table) and `type::record(table, id)` for a [`RecordId`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id) — so values are always passed safely.
##  The JSON value model[](https://surrealdb.com/docs/reference/kotlin/concepts/value-types#the-json-value-model)
Beyond the record types above, all data is modelled as [`JsonElement`](https://kotlinlang.org/api/kotlinx.serialization/kotlinx-serialization-json/kotlinx.serialization.json/-json-element/). Read methods return a [`JsonElement`](https://surrealdb.com/docs/reference/kotlin/api/values/value), and write methods accept a [`JsonObject`](https://surrealdb.com/docs/reference/kotlin/api/values/value). Build payloads with [`buildJsonObject`](https://kotlinlang.org/api/kotlinx.serialization/kotlinx-serialization-json/kotlinx.serialization.json/build-json-object.html).

```kotlin
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

val data = buildJsonObject {
    put("name", "Ada")
    put("age", 36)
}
```

Note
The SDK does not ship dedicated wrapper classes for datetimes, durations, or geometries. Express these as SurrealQL literals in a query, or as the JSON values that SurrealDB expects, and decode results into your own [`@Serializable`](https://surrealdb.com/docs/reference/kotlin/concepts/serialization) types.
##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/value-types#learn-more)
  * •
[`Table`](https://surrealdb.com/docs/reference/kotlin/api/values/table), [`RecordId`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id), and [`RecordIdRange`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range) references
  * •
[Value (JSON model)](https://surrealdb.com/docs/reference/kotlin/api/values/value) reference
  * •
[Serialization](https://surrealdb.com/docs/reference/kotlin/concepts/serialization) for decoding into your own types
