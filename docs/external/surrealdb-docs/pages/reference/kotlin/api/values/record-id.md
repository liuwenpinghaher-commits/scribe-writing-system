---
title: "https://surrealdb.com/docs/reference/kotlin/api/values/record-id"
url: "https://surrealdb.com/docs/reference/kotlin/api/values/record-id"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/values/record-id

Source: https://surrealdb.com/docs/reference/kotlin/api/values/record-id

`RecordId` identifies a single record by its table and ID, rendered as `table:id`. Pass it to the [CRUD builders](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation) to target one record.
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.query.RecordId
```

* * *
##  Constructor[](https://surrealdb.com/docs/reference/kotlin/api/values/record-id#constructor)
Method Syntax

```kotlin
RecordId(table, id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `String`  | The table name.  |  
| `id`  | `String`  | The record identifier within the table.  |  
Example

```kotlin
val ada = RecordId("person", "ada")

client.select(ada).awaitAs<Person>()
```

When bound into a query, a `RecordId` is rendered with `type::record(table, id)` so the value is always passed safely.
##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/values/record-id#learn-more)
  * •
[Value types](https://surrealdb.com/docs/reference/kotlin/concepts/value-types)
  * •
[`Table`](https://surrealdb.com/docs/reference/kotlin/api/values/table) and [`RecordIdRange`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range)
