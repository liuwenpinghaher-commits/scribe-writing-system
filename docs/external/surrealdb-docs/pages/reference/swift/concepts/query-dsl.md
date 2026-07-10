---
title: "https://surrealdb.com/docs/reference/swift/concepts/query-dsl"
url: "https://surrealdb.com/docs/reference/swift/concepts/query-dsl"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/concepts/query-dsl

Source: https://surrealdb.com/docs/reference/swift/concepts/query-dsl

In addition to the high-level CRUD methods, the Swift SDK lets you build queries with a type-safe DSL. You can use either compile-time expression macros or the programmatic `SurrealDSL` builder, then run the result with [`query`](https://surrealdb.com/docs/reference/swift/methods/query).
##  Query macros[](https://surrealdb.com/docs/reference/swift/concepts/query-dsl#query-macros)
Expression macros resolve to `SurrealDSL` calls at compile time. They are the most concise way to express a query:

```swift
let selectQuery = #select(Person.self, where: Person.Fields.age > 18, limit: 10)
let createQuery = #create(Person.self)
let updateQuery = #update(Person.self, where: Person.Fields.name == "Ada")
let upsertQuery = #upsert(Person.self)
let deleteQuery = #delete(Person.self, where: Person.Fields.age < 18)
let liveQuery = #live(Person.self)
```

Run a query with the [`query`](https://surrealdb.com/docs/reference/swift/methods/query) method:

```swift
let people = try await client.query(selectQuery)
```

##  Programmatic `SurrealDSL` builder[](https://surrealdb.com/docs/reference/swift/concepts/query-dsl#programmatic-surrealdsl-builder)
`SurrealDSL` exposes the same operations as plain functions, which is useful when a query is built dynamically:

```swift
let query = SurrealDSL.select(
    Person.self,
    where: Person.Fields.age >= 21,
    limit: 50,
    start: 0
)
let people = try await client.query(query)
```

When creating records through the DSL, pass the content as a binding:

```swift
let createQuery = SurrealDSL.create(
    Person.self,
    contentBinding: "content",
    bindings: ["content": try .fromEncodable(newPerson)]
)
let created = try await client.query(createQuery)
```

##  When to use raw queries instead[](https://surrealdb.com/docs/reference/swift/concepts/query-dsl#when-to-use-raw-queries-instead)
For arbitrary SurrealQL that the DSL does not model, use [`queryRaw`](https://surrealdb.com/docs/reference/swift/methods/query-raw) with bound parameters.
