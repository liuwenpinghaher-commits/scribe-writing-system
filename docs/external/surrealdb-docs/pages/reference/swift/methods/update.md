---
title: "https://surrealdb.com/docs/reference/swift/methods/update"
url: "https://surrealdb.com/docs/reference/swift/methods/update"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/update

Source: https://surrealdb.com/docs/reference/swift/methods/update

Updates matching records of a model's table, or a single record by id.
Method Syntax

```swift
try await client.update(Model.self, content: content,
    where: predicate)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/update#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `model`  |  The model type to update, e.g. `Person.self`.  |  
| `content`  | The content to write to matching records.  |  
| `where`  | A [predicate](https://surrealdb.com/docs/reference/swift/concepts/predicates) selecting which records to update.  |  
| `recordID`  | A [`SurrealRecordID`](https://surrealdb.com/docs/reference/swift/data-types#surrealrecordid) to update a single record.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/update#example-usage)

```swift
// Update matching records
let updated = try await client.update(
    Person.self,
    content: Person(id: nil, name: "Ada", age: 31),
    where: Person.Fields.name == "Ada"
)

// Update a specific record
let id = SurrealRecordID(table: "person", id: .string("ada"))
let record: Person? = try await client.update(
    recordID: id,
    content: Person(id: nil, name: "Ada", age: 31)
)
```
