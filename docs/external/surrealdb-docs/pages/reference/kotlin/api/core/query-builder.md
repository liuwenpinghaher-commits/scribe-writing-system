---
title: "https://surrealdb.com/docs/reference/kotlin/api/core/query-builder"
url: "https://surrealdb.com/docs/reference/kotlin/api/core/query-builder"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/core/query-builder

Source: https://surrealdb.com/docs/reference/kotlin/api/core/query-builder

The CRUD methods on [`SurrealClient`](/docs/reference/kotlin/api/core/surreal-client) return fluent builders that compile to [SurrealQL](/docs/reference/query-language). Each builder is refined with chainable methods and terminated with [`await()`](#await) (raw [`JsonElement`](/docs/reference/kotlin/api/values/value)) or the typed [`awaitAs()`](#await-as) extension.
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.query.awaitAs
import com.surrealdb.kotlin.query.field
import com.surrealdb.kotlin.query.gte
```

* * *
##  Terminal methods[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#terminal-methods)
###  `.await()`[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#await)
Executes the builder and returns the unwrapped result of the first statement as a [`JsonElement`](https://surrealdb.com/docs/reference/kotlin/api/values/value).
Method Syntax

```kotlin
builder.await()
```

**Returns:** `JsonElement`
###  `.awaitRaw()`[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#await-raw)
Executes the builder and returns the raw `[{ status, result, time, type }]` response envelope.
Method Syntax

```kotlin
builder.awaitRaw()
```

**Returns:** `JsonElement`
###  `.awaitAs<T>()`[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#await-as)
An inline extension that executes the builder and decodes the result into `T` using [`kotlinx.serialization`](https://surrealdb.com/docs/reference/kotlin/concepts/serialization). Available on every builder.
Method Syntax

```kotlin
builder.awaitAs<T>()
```

**Returns:** `T`
Example

```kotlin
val people: List<Person> = client.select(Table("person")).awaitAs()
```

###  `.compile()`[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#compile)
Compiles the builder to a `BoundQuery` without executing it — useful for inspection or composing with [`.query()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#query).
Method Syntax

```kotlin
builder.compile()
```

**Returns:** `BoundQuery`
* * *
##  `SelectQuery`[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#select-query)
Returned by [`.select(what)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#select).  
| Method  | Description  |  
| --- | --- |  
| `.fields(vararg names)`  | Selects specific fields.  |  
| `.value(field)`  | Selects a single field's value.  |  
| `.where(expr)`  |  Filters with an [expression](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#expressions).  |  
| `.start(n)`  |  Skips the first `n`records.  |  
| `.limit(n)`  | Limits the number of records.  |  
| `.fetch(vararg fields)`  | Fetches related records.  |  
| `.timeout(seconds)`  | Sets a query timeout.  |  
| `.version(literal)`  | Reads at a specific version.  |  
Example

```kotlin
val adults: List<Person> = client
    .select(Table("person"))
    .where(field("age") gte 18)
    .limit(50)
    .awaitAs()
```

##  Content builders[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#content-builders)
[`CreateQuery`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#create), [`UpdateQuery`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#update), [`UpsertQuery`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#upsert), and [`RelateQuery`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#relate) accept content and a return mode.  
| Method  | Description  |  
| --- | --- |  
| `.content(data)`  |  Sets the record content (a `JsonElement`).  |  
| `.where(expr)`  | Filters affected records (update, upsert, merge, patch, delete).  |  
| `.returnMode(mode)`  |  Controls the returned payload (see [ReturnMode](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#return-mode-type)).  |  
##  `ReturnMode`[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#return-mode-type)
Import

```kotlin
import com.surrealdb.kotlin.query.ReturnMode
```
  
| Value  | Description  |  
| --- | --- |  
| `ReturnMode.None`  | Returns nothing.  |  
| `ReturnMode.Before`  | Returns records as they were before the change.  |  
| `ReturnMode.After`  | Returns records after the change.  |  
| `ReturnMode.Diff`  | Returns a JSON Patch diff.  |  
| `ReturnMode.Fields(names)`  | Returns only the named fields.  |  
##  `RunQuery`[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#run-query)
Returned by [`.run(function)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#run).  
| Method  | Description  |  
| --- | --- |  
| `.args(vararg args)`  | Sets the function arguments.  |  
| `.version(version)`  | Selects a function version.  |  
* * *
##  Expression helpers[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#expressions)
Build `WHERE` expressions with the helper functions and infix operators from `com.surrealdb.kotlin.query`.
Import

```kotlin
import com.surrealdb.kotlin.query.field
import com.surrealdb.kotlin.query.value
import com.surrealdb.kotlin.query.gte
import com.surrealdb.kotlin.query.and
```
  
| Helper  | SurrealQL  |  
| --- | --- |  
| `field(name)`  | A validated field reference.  |  
| `value(any)`  | A literal value.  |  
| `raw(boundQuery)`  | A raw fragment.  |  
| `a eq b`  | `=`  |  
| `a neq b`  | `!=`  |  
| `a lt b`  | `<`  |  
| `a lte b`  | `<=`  |  
| `a gt b`  | `>`  |  
| `a gte b`  | `>=`  |  
| `a contains b`  | `CONTAINS`  |  
| `a inside b`  | `IN`  |  
| `a and b`  | `AND`  |  
| `a or b`  | `OR`  |  
| `not(expr)`  | `!`  |  
Note
Inequality is `neq` (not `ne`) and membership is `inside` (not `in`, which is a reserved Kotlin keyword).
Example

```kotlin
import com.surrealdb.kotlin.query.field
import com.surrealdb.kotlin.query.gte
import com.surrealdb.kotlin.query.eq
import com.surrealdb.kotlin.query.and

val expr = (field("age") gte 18) and (field("active") eq true)
val results = client.select(Table("person")).where(expr).awaitAs<List<Person>>()
```

* * *
##  `surql` DSL[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#surql)
The `surql` helpers build a parameterised `BoundQuery` with automatic, injection-safe binding of values and record identifiers.
Import

```kotlin
import com.surrealdb.kotlin.query.surql
```

Example

```kotlin
// Vararg bindings
val a = surql("SELECT * FROM person WHERE age > \$min", "min" to 25)

// Builder block
val b = surql {
    +"SELECT * FROM person WHERE age > "
    param("min", 25)
}

val result = client.query(a)
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#learn-more)
  * •
[SurrealClient API reference](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) for the CRUD methods
  * •
[Data manipulation](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation) for the concepts
  * •
[Serialization](https://surrealdb.com/docs/reference/kotlin/concepts/serialization) for `awaitAs`
