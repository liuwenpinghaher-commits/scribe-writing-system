---
title: "https://surrealdb.com/docs/reference/swift/methods/delete"
url: "https://surrealdb.com/docs/reference/swift/methods/delete"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/delete

Source: https://surrealdb.com/docs/reference/swift/methods/delete

Deletes matching records of a model's table, or a single record by id.
Method Syntax

```swift
try await client.delete(Model.self, where: predicate)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/delete#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `model`  |  The model type to delete from, e.g. `Person.self`.  |  
| `where`  | A [predicate](https://surrealdb.com/docs/reference/swift/concepts/predicates) selecting which records to delete.  |  
| `recordID`  | A [`SurrealRecordID`](https://surrealdb.com/docs/reference/swift/data-types#surrealrecordid) to delete a single record.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/delete#example-usage)

```swift
// Delete matching records
let deleted = try await client.delete(Person.self, where: Person.Fields.age < 18)

// Delete a specific record
let id = SurrealRecordID(table: "person", id: .string("ada"))
let record: Person? = try await client.delete(recordID: id, as: Person.self)
```
