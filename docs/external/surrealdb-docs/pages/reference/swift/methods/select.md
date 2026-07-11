---
title: "https://surrealdb.com/docs/reference/swift/methods/select"
url: "https://surrealdb.com/docs/reference/swift/methods/select"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/select

Source: https://surrealdb.com/docs/reference/swift/methods/select

Selects all records of a model's table, a filtered subset, or a single record by id.
Method Syntax

```swift
try await client.select(Model.self, where: predicate, limit: limit,
    start: start)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/select#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `model`  |  The model type to select, e.g. `Person.self`.  |  
| `where`  | A [predicate](https://surrealdb.com/docs/reference/swift/concepts/predicates) restricting which records are returned.  |  
|  `limit`/ `start`  | Paginate the results by limiting the count and offsetting the start.  |  
| `recordID`  | Select a single record by its [`SurrealRecordID`](https://surrealdb.com/docs/reference/swift/data-types#surrealrecordid) instead of a table.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/select#example-usage)

```swift
// Select all records
let people = try await client.select(Person.self)

// Select a filtered, paginated subset
let adults = try await client.select(
    Person.self,
    where: Person.Fields.age >= 18,
    limit: 20,
    start: 0
)

// Select a single record by id
let id = SurrealRecordID(table: "person", id: .string("ada"))
let person: Person? = try await client.select(recordID: id,
    as: Person.self)
```
