---
title: "https://surrealdb.com/docs/reference/kotlin/api/values/table"
url: "https://surrealdb.com/docs/reference/kotlin/api/values/table"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/values/table

Source: https://surrealdb.com/docs/reference/kotlin/api/values/table

`Table` refers to a table by name. Pass it to the [CRUD builders](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation) to target every record in the table.
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.query.Table
```

* * *
##  Constructor[](https://surrealdb.com/docs/reference/kotlin/api/values/table#constructor)
Method Syntax

```kotlin
Table(name)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `String`  | The table name.  |  
Example

```kotlin
val person = Table("person")

client.select(person).awaitAs<List<Person>>()
```

When bound into a query, a `Table` is rendered with `type::table(name)` so the value is always passed safely.
##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/values/table#learn-more)
  * •
[Value types](https://surrealdb.com/docs/reference/kotlin/concepts/value-types)
  * •
[`RecordId`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id) and [`RecordIdRange`](https://surrealdb.com/docs/reference/kotlin/api/values/record-id-range)
