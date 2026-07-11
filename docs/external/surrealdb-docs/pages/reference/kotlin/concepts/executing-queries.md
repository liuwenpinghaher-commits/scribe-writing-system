---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries

Source: https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries

The [`.query()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#query) family runs raw [SurrealQL](https://surrealdb.com/docs/reference/query-language) and is the foundation of the SDK — the [CRUD builders](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation) compile to SurrealQL and dispatch through it. Queries can be supplied as a string with a [`JsonObject`](https://surrealdb.com/docs/reference/kotlin/concepts/value-types) of bound parameters, or built with the [`surql`](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#building-queries) DSL.
##  API references[](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`client.query(sql, vars)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#query)  | Runs SurrealQL and returns the raw result  |  
| [`client.queryAs<T>(sql, vars)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#query-as)  |  Runs SurrealQL and decodes the result to `T`  |  
| [`client.queryResult(sql, vars)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#query-result)  |  Runs SurrealQL and returns a `Result`  |  
| [`client.let(key, value)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#let)  | Defines a session parameter  |  
| [`client.unset(key)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#unset)  | Removes a session parameter  |  
##  Running a query[](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#running-a-query)
Pass SurrealQL and, optionally, a [`JsonObject`](https://surrealdb.com/docs/reference/kotlin/concepts/value-types) of bound parameters. The result is returned as a [`JsonElement`](https://surrealdb.com/docs/reference/kotlin/concepts/value-types).

```kotlin
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

val result = client.query(
    "SELECT * FROM person WHERE age > \$min_age",
    buildJsonObject { put("min_age", 25) },
)
```

Note
Always bind variables with the `vars` argument rather than interpolating values into the query string. This avoids SurrealQL injection and lets the server cache query plans.
##  Decoding results[](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#decoding-results)
To decode a query result straight into your own types, use the inline [`.queryAs()`](/docs/reference/kotlin/api/core/surreal-client#query-as) helper with a [`@Serializable`](/docs/reference/kotlin/concepts/serialization) type.

```kotlin
import kotlinx.serialization.Serializable

@Serializable
data class Person(val name: String, val age: Int)

val people: List<Person> = client.queryAs(
    "SELECT * FROM person WHERE age > \$min_age",
    buildJsonObject { put("min_age", 25) },
)
```

You can also decode an arbitrary [`JsonElement`](/docs/reference/kotlin/concepts/value-types) yourself with [`.decode()`](/docs/reference/kotlin/api/core/surreal-client#decode).
##  Result variants[](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#result-variants)
Every networked call has a `...Result` companion that returns a [`Result`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/-result/) instead of throwing, which is useful when you prefer to handle failures functionally.

```kotlin
val outcome = client.queryResult("SELECT * FROM person")
outcome
    .onSuccess { println("got $it") }
    .onFailure { println("query failed: ${it.message}") }
```

See [Error handling](https://surrealdb.com/docs/reference/kotlin/concepts/error-handling) for the exception hierarchy thrown by the non-`Result` variants.
##  Session parameters[](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#session-parameters)
Define parameters that persist for the session with [`.let()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#let), and remove them with [`.unset()`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#unset). These are referenced as `$name` in subsequent queries.

```kotlin
import kotlinx.serialization.json.JsonPrimitive

client.let("min_age", JsonPrimitive(18))
client.query("SELECT * FROM person WHERE age > \$min_age")
client.unset("min_age")
```

##  Building queries[](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#building-queries)
The [`surql`](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder#surql) DSL builds a parameterised `BoundQuery` with automatic binding of values and record identifiers.

```kotlin
import com.surrealdb.kotlin.query.surql

val bound = surql("SELECT * FROM person WHERE age > \$min", "min" to 25)
val result = client.query(bound)
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/executing-queries#learn-more)
  * •
[SurrealClient API reference](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client) for complete method signatures
  * •
[Query builder reference](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder) for the fluent builders and `surql` DSL
  * •
[Data manipulation](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation) for CRUD with the builders
  * •
[Serialization](https://surrealdb.com/docs/reference/kotlin/concepts/serialization) for working with `@Serializable` types
