---
title: "https://surrealdb.com/docs/reference/swift/methods/use"
url: "https://surrealdb.com/docs/reference/swift/methods/use"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/use

Source: https://surrealdb.com/docs/reference/swift/methods/use

Switches the connection to a specific namespace and database.
Method Syntax

```swift
try await client.use(namespace: ns, database: db)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/use#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `namespace`  | The namespace to switch to.  |  
| `database`  | The database to switch to.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/use#example-usage)

```swift
try await client.use(namespace: "myapp", database: "mydb")
```
