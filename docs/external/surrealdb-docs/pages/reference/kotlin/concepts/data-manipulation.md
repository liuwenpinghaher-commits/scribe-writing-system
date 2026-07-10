---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation

Source: https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation

The Kotlin SDK provides fluent builders for the common CRUD operations. Each builder method (such as [`.select()`](/docs/reference/kotlin/api/core/surreal-client#select) or [`.create()`](/docs/reference/kotlin/api/core/surreal-client#create)) returns a [query builder](/docs/reference/kotlin/api/core/query-builder) that you refine and then terminate with `await()` (raw [`JsonElement`](/docs/reference/kotlin/concepts/value-types)) or the typed [`awaitAs()`](/docs/reference/kotlin/api/core/query-builder#await-as) extension. Under the hood these compile to [SurrealQL](/docs/reference/query-language) and dispatch through [`.query()`](/docs/reference/kotlin/concepts/executing-queries), mirroring the [JavaScript SDK](/docs/languages/javascript).
##  API references[](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`client.select(what)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#select)  | Selects records from a table or record  |  
| [`client.create(what)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#create)  | Creates a record  |  
| [`client.update(what)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#update)  | Replaces the content of records  |  
| [`client.upsert(what)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#upsert)  | Creates or updates records  |  
| [`client.merge(what, data)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#merge)  | Merges data into records  |  
| [`client.patch(what, patches)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#patch)  | Applies JSON patches to records  |  
| [`client.delete(what)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#delete)  | Deletes records  |  
| [`client.relate(in, relation, out)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#relate)  | Creates a graph edge between records  |  
| [`client.insert(into, data)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#insert)  | Inserts one or more records  |  
The `what` argument accepts a [`Table`](https://surrealdb.com/docs/reference/kotlin/api/values/table) to target every record in a table, a [`RecordId`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id) to target a single record, or a [`RecordIdRange`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range) to target a range.
##  Creating records[](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation#creating-records)
Build content with [`buildJsonObject`](/docs/reference/kotlin/concepts/value-types) and finish with the typed [`awaitAs()`](/docs/reference/kotlin/api/core/query-builder#await-as).

```kotlin
import com.surrealdb.kotlin.query.RecordId
import com.surrealdb.kotlin.query.awaitAs
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

@Serializable
data class Person(val name: String, val age: Int)

val ada: Person = client
    .create(RecordId("person", "ada"))
    .content(buildJsonObject {
        put("name", "Ada")
        put("age", 36)
    })
    .awaitAs()
```

##  Selecting records[](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation#selecting-records)
Refine a [`select`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#select-query) with [`.where()`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#where), [`.limit()`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#limit), [`.start()`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#start), [`.fetch()`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#fetch), and others, using the [expression helpers](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#expressions).

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

##  Updating and merging[](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation#updating-and-merging)
Use [`.update()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#update) to replace record content, [`.merge()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#merge) to merge data, or [`.upsert()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#upsert) to create or update. Control the returned payload with [`.returnMode()`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#return-mode).

```kotlin
import com.surrealdb.kotlin.query.RecordId
import com.surrealdb.kotlin.query.ReturnMode
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

client
    .merge(RecordId("person", "ada"), buildJsonObject { put("age", 37) })
    .returnMode(ReturnMode.After)
    .await()
```

##  Deleting records[](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation#deleting-records)

```kotlin
import com.surrealdb.kotlin.query.RecordId

client.delete(RecordId("person", "ada")).await()
```

##  Relating records[](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation#relating-records)
Create a graph edge between two records with [`.relate()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#relate).

```kotlin
import com.surrealdb.kotlin.query.RecordId
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

client
    .relate(RecordId("person", "ada"), RecordId("wrote", "w1"), RecordId("article", "a1"))
    .content(buildJsonObject { put("year", 1843) })
    .await()
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation#learn-more)
  * •
[Query builder reference](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder) for every builder method and expression helper
  * •
[Executing queries](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries) for raw SurrealQL
  * •
[Value types](https://surrealdb.com/docs/reference/kotlin/concepts/value-types) for `Table`, `RecordId`, and the JSON model
  * •
[Serialization](https://surrealdb.com/docs/reference/kotlin/concepts/serialization) for decoding into your own types
