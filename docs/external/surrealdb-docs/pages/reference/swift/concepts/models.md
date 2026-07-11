---
title: "https://surrealdb.com/docs/reference/swift/concepts/models"
url: "https://surrealdb.com/docs/reference/swift/concepts/models"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/concepts/models

Source: https://surrealdb.com/docs/reference/swift/concepts/models

Models describe the shape of your records and give the SDK the type information it needs for type-safe CRUD operations and [predicates](https://surrealdb.com/docs/reference/swift/concepts/predicates).
##  The `@SurrealModel` macro[](https://surrealdb.com/docs/reference/swift/concepts/models#the-surrealmodel-macro)
The `@SurrealModel` macro is the recommended way to declare a model. It takes the table name and generates everything the SDK needs:

```swift
import SurrealDB

@SurrealModel("person")
struct Person: Codable, Sendable {
    let id: String?
    let name: String
    let age: Int
}
```

The macro generates:
  * •
`static let surrealTable`, the table name passed to the macro.
  * •
`SurrealModel` conformance, so the type can be used directly with [`select`](https://surrealdb.com/docs/reference/swift/methods/select), [`create`](https://surrealdb.com/docs/reference/swift/methods/create), [`update`](https://surrealdb.com/docs/reference/swift/methods/update), [`upsert`](https://surrealdb.com/docs/reference/swift/methods/upsert) and [`delete`](https://surrealdb.com/docs/reference/swift/methods/delete).
  * •
A `Fields` namespace for building type-safe predicates such as `Person.Fields.age >= 18`.

##  Manual conformance[](https://surrealdb.com/docs/reference/swift/concepts/models#manual-conformance)
If you prefer not to use the macro, you can conform to `SurrealModel` manually by declaring the `surrealTable` property:

```swift
struct Article: SurrealModel, Codable, Sendable {
    static let surrealTable = "article"
    let id: String?
    let title: String
}
```

Manual conformance does not generate a `Fields` namespace, so you will need to write [raw predicates](https://surrealdb.com/docs/reference/swift/concepts/predicates#raw-predicates) for queries that filter on fields.
