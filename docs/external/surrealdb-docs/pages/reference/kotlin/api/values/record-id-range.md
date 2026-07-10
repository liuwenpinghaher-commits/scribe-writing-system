---
title: "https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range"
url: "https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range

Source: https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range

`RecordIdRange` targets a contiguous range of records within a table by their IDs. Pass it to the [CRUD builders](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation) to operate on a [range of records](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#record-ranges).
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.query.RecordIdRange
```

* * *
##  Constructor[](https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range#constructor)
Method Syntax

```kotlin
RecordIdRange(table, start, end, includeEnd)
```
  
| Parameter  | Type  | Default  | Description  |  
| --- | --- | --- | --- |  
| `table`  | `String`  | —  | The table name.  |  
| `start`  | `String?`  | `null`  |  The inclusive start ID, or `null`for unbounded.  |  
| `end`  | `String?`  | `null`  |  The end ID, or `null`for unbounded.  |  
| `includeEnd`  | `Boolean`  | `false`  |  Whether the `end`ID is inclusive.  |  
Example

```kotlin
val range = RecordIdRange("person", start = "a", end = "m", includeEnd = true)

client.select(range).awaitAs<List<Person>>()
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range#learn-more)
  * •
[Value types](https://surrealdb.com/docs/reference/kotlin/concepts/value-types)
  * •
[`RecordId`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id) and [`Table`](https://surrealdb.com/docs/reference/kotlin/api/values/table)
  * •
[Record ranges](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#record-ranges) in SurrealQL
