---
title: "https://surrealdb.com/docs/reference/swift/methods/create"
url: "https://surrealdb.com/docs/reference/swift/methods/create"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/create

Source: https://surrealdb.com/docs/reference/swift/methods/create

Creates a record in the database, either with an auto-generated id or a specific id.
Method Syntax

```swift
try await client.create(content)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/create#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `content`  | The model instance to create. The table is derived from the model.  |  
| `recordID`  | A [`SurrealRecordID`](https://surrealdb.com/docs/reference/swift/data-types#surrealrecordid) to create the record with a specific id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/create#example-usage)

```swift
// Create with an auto-generated id
let created: [Person] = try await client.create(Person(id: nil, name: "Ada", age: 30))

// Create with a specific id
let id = SurrealRecordID(table: "person", id: .string("ada"))
let record: Person? = try await client.create(
    recordID: id,
    content: Person(id: nil, name: "Ada", age: 30)
)
```
