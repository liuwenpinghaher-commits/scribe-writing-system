---
title: "https://surrealdb.com/docs/reference/swift/methods/query"
url: "https://surrealdb.com/docs/reference/swift/methods/query"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/query

Source: https://surrealdb.com/docs/reference/swift/methods/query

Runs a query built with the [query DSL](https://surrealdb.com/docs/reference/swift/concepts/query-dsl), either a query macro such as `#select` or a `SurrealDSL` builder call.
Method Syntax

```swift
try await client.query(query)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/query#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `query`  |  A query produced by a query macro or a `SurrealDSL`builder call.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/query#example-usage)

```swift
// Using a query macro
let selectQuery = #select(Person.self, where: Person.Fields.age > 18, limit: 10)
let people = try await client.query(selectQuery)

// Using the SurrealDSL builder
let query = SurrealDSL.select(Person.self, where: Person.Fields.age >= 21, limit: 50)
let result = try await client.query(query)
```

For arbitrary SurrealQL, see [`queryRaw`](https://surrealdb.com/docs/reference/swift/methods/query-raw).
