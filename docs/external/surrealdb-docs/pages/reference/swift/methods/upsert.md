---
title: "https://surrealdb.com/docs/reference/swift/methods/upsert"
url: "https://surrealdb.com/docs/reference/swift/methods/upsert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/upsert

Source: https://surrealdb.com/docs/reference/swift/methods/upsert

Creates matching records if they do not exist, or updates them if they do.
Method Syntax

```swift
try await client.upsert(Model.self, content: content, where: predicate)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/upsert#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `model`  |  The model type to upsert, e.g. `Person.self`.  |  
| `content`  | The content to write to matching records.  |  
| `where`  | A [predicate](https://surrealdb.com/docs/reference/swift/concepts/predicates) selecting which records to upsert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/upsert#example-usage)

```swift
let upserted = try await client.upsert(
    Person.self,
    content: Person(id: nil, name: "Ada", age: 31),
    where: Person.Fields.name == "Ada"
)
```
