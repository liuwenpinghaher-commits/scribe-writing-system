---
title: "https://surrealdb.com/docs/reference/swift/methods/connect"
url: "https://surrealdb.com/docs/reference/swift/methods/connect"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/connect

Source: https://surrealdb.com/docs/reference/swift/methods/connect

Connects the client to the endpoint it was configured with.
Method Syntax

```swift
try await client.connect()
```

###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/connect#example-usage)

```swift
let client = try SurrealHTTPClient(endpoint: "http://localhost:8000")
try await client.connect()
defer { Task { await client.close() } }
```

See [Connecting to SurrealDB](https://surrealdb.com/docs/reference/swift/concepts/connecting) for the available client types and configuration options.
