---
title: "https://surrealdb.com/docs/reference/swift/data-types"
url: "https://surrealdb.com/docs/reference/swift/data-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/data-types

Source: https://surrealdb.com/docs/reference/swift/data-types

This page describes the core data types used throughout the Swift SDK when working with records and raw queries.
##  `SurrealValue`[](https://surrealdb.com/docs/reference/swift/data-types#surrealvalue)
`SurrealValue` is the universal value type used to represent any data that can be sent to or received from SurrealDB. It is most often used when binding parameters to [raw queries](https://surrealdb.com/docs/reference/swift/methods/query-raw) or when working with dynamically typed data.

```swift
let string: SurrealValue = .string("hello")
let int: SurrealValue = .int(42)
let double: SurrealValue = .double(3.14)
let bool: SurrealValue = .bool(true)
let null: SurrealValue = .null
let array: SurrealValue = .array([.string("a"), .int(1)])
let object: SurrealValue = .object(["name": .string("Ada"), "age": .int(30)])
let uuid: SurrealValue = .uuid(UUID())
let datetime: SurrealValue = .datetime(Date())
let record: SurrealValue = .recordID(SurrealRecordID(table: "person", id: .string("ada")))
```

You can convert between `SurrealValue` and your own `Codable` types:

```swift
// Encode a Codable value into a SurrealValue
let value = try SurrealValue.fromEncodable(myStruct)

// Decode a SurrealValue back into a concrete type
let person = try value.decode(Person.self)
```

##  `SurrealRecordID`[](https://surrealdb.com/docs/reference/swift/data-types#surrealrecordid)
A `SurrealRecordID` identifies a single record by its table and id. It is used by the record-targeted overloads of [`select`](https://surrealdb.com/docs/reference/swift/methods/select), [`create`](https://surrealdb.com/docs/reference/swift/methods/create), [`update`](https://surrealdb.com/docs/reference/swift/methods/update) and [`delete`](https://surrealdb.com/docs/reference/swift/methods/delete).

```swift
let id = SurrealRecordID(table: "person", id: .string("ada"))
let person: Person? = try await client.select(recordID: id, as: Person.self)
```

##  `RPCQueryResult`[](https://surrealdb.com/docs/reference/swift/data-types#rpcqueryresult)
[`queryRaw`](https://surrealdb.com/docs/reference/swift/methods/query-raw) returns an array of `RPCQueryResult`, one per statement in the query. Each result carries a `status` and a `result`.

```swift
let results: [RPCQueryResult] = try await client.queryRaw(
    "SELECT * FROM person WHERE age > $minAge;",
    bindings: ["minAge": .int(18)]
)

for row in results {
    if row.status == .ok {
        print(row.result)
    }
}
```
