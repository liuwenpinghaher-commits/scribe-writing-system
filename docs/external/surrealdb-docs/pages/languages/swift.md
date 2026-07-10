---
title: "https://surrealdb.com/docs/languages/swift"
url: "https://surrealdb.com/docs/languages/swift"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/languages/swift

Source: https://surrealdb.com/docs/languages/swift

The Swift SDK for SurrealDB lets you connect to a database and query it from your application. This guide covers connecting, authenticating, and running your first queries.
##  1. Install the SDK[](https://surrealdb.com/docs/languages/swift#1-install-the-sdk)
Follow the [installation guide](https://surrealdb.com/docs/reference/swift/installation) to add the SDK to your project. Once installed, import the SDK.

```swift
import SurrealDB
```

##  2. Connect to SurrealDB[](https://surrealdb.com/docs/languages/swift#2-connect-to-surrealdb)
Create a client for your endpoint and connect. The `SurrealHTTPClient` is the simplest starting point for most applications.
Supported connection protocols include:
  * •
**HTTP** (`http://`, `https://`) using [`SurrealHTTPClient`](https://surrealdb.com/docs/reference/swift/concepts/connecting) for short-lived stateless connections, the simplest way to get started
  * •
**WebSocket** (`ws://`, `wss://`) using the WebSocket client for long-lived stateful connections, required for [live queries](https://surrealdb.com/docs/reference/swift/concepts/live-queries)

```swift
let client = try SurrealHTTPClient(endpoint: "http://localhost:8000")
try await client.connect()
defer { Task { await client.close() } }
```

After connecting, use [`signin`](https://surrealdb.com/docs/reference/swift/concepts/authentication) to authenticate and [`use`](https://surrealdb.com/docs/reference/swift/concepts/connecting) to select the namespace and database you want to work with. Most operations require both.

```swift
let tokens = try await client.signin(.root(username: "root", password: "root"))
try await client.use(namespace: "myapp", database: "mydb")
```

##  3. Inserting data into SurrealDB[](https://surrealdb.com/docs/languages/swift#3-inserting-data-into-surrealdb)
The Swift SDK is model-first. The `@SurrealModel` macro generates `SurrealModel` conformance, the `surrealTable` name, and a type-safe `Fields` namespace used to build [predicates](https://surrealdb.com/docs/reference/swift/concepts/predicates).

```swift
@SurrealModel("person")
struct Person: Codable, Sendable {
    let id: String?
    let name: String
    let age: Int
}
```

Once you have a model, use [`create`](https://surrealdb.com/docs/reference/swift/methods/create) to insert a record.

```swift
let created: [Person] = try await client.create(
    Person(id: nil, name: "Ada", age: 30)
)
```

##  4. Retrieving data from SurrealDB[](https://surrealdb.com/docs/languages/swift#4-retrieving-data-from-surrealdb)
###  Selecting records[](https://surrealdb.com/docs/languages/swift#selecting-records)
Use [`select`](https://surrealdb.com/docs/reference/swift/methods/select) to retrieve all records of a table, or narrow the results with a type-safe predicate built from the model's `Fields` namespace.

```swift
// Select all records of a table
let people = try await client.select(Person.self)

// Select with a type-safe predicate
let adults = try await client.select(
    Person.self,
    where: Person.Fields.age >= 18,
    limit: 20,
    start: 0
)
```

###  Running SurrealQL queries[](https://surrealdb.com/docs/languages/swift#running-surrealql-queries)
For more advanced use cases, use [`queryRaw`](https://surrealdb.com/docs/reference/swift/methods/query-raw) to run [SurrealQL](https://surrealdb.com/docs/reference/query-language) statements directly. Use bound parameters to safely pass dynamic values.

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

##  5. Closing the connection[](https://surrealdb.com/docs/languages/swift#5-closing-the-connection)
Always close the connection when you are done to release resources. The idiomatic Swift pattern is to `defer` the close immediately after connecting, as shown in step 2.

```swift
await client.close()
```

##  Next steps[](https://surrealdb.com/docs/languages/swift#next-steps)
You have learned how to install the SDK, connect to SurrealDB, create records, and retrieve data. There is a lot more you can do with the SDK, including updating and deleting records, authentication, live queries, and transactions.
[Connecting to SurrealDB Learn how to manage your database connections, including protocols and configuration.](https://surrealdb.com/docs/reference/swift/concepts/connecting)[Authentication Read more about authentication levels and how to integrate them into your application.](https://surrealdb.com/docs/reference/swift/concepts/authentication)[Models Learn how to define models with the @SurrealModel macro and build type-safe queries.](https://surrealdb.com/docs/reference/swift/concepts/models)[API Reference Complete reference for all methods, types, and errors.](https://surrealdb.com/docs/reference/swift/methods)
Note
This getting-started guide covers the essentials. For the complete methods, API, and concept reference, see the [Swift SDK reference](https://surrealdb.com/docs/reference/swift).
