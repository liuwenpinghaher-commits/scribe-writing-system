---
title: "https://surrealdb.com/docs/reference/swift/methods/query-raw"
url: "https://surrealdb.com/docs/reference/swift/methods/query-raw"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/query-raw

Source: https://surrealdb.com/docs/reference/swift/methods/query-raw

Executes a raw SurrealQL string with bound parameters and returns one [`RPCQueryResult`](https://surrealdb.com/docs/reference/swift/data-types#rpcqueryresult) per statement.
Method Syntax

```swift
try await client.queryRaw(sql, bindings: bindings)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/query-raw#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | The raw SurrealQL query to execute.  |  
| `bindings`  | A dictionary of [`SurrealValue`](https://surrealdb.com/docs/reference/swift/data-types#surrealvalue) parameters referenced in the query.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/query-raw#example-usage)

```swift
let results: [RPCQueryResult] = try await client.queryRaw(
    "SELECT * FROM person WHERE age > $minAge LIMIT $limit;",
    bindings: [
        "minAge": .int(18),
        "limit": .int(50)
    ]
)

for row in results {
    if row.status == .ok {
        print(row.result)
    }
}
```
