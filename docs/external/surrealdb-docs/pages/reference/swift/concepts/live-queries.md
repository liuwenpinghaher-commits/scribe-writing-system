---
title: "https://surrealdb.com/docs/reference/swift/concepts/live-queries"
url: "https://surrealdb.com/docs/reference/swift/concepts/live-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/concepts/live-queries

Source: https://surrealdb.com/docs/reference/swift/concepts/live-queries

Live queries let you subscribe to changes on a table and receive events in real time. They require the [WebSocket client](/docs/reference/swift/concepts/connecting#websocket-client) and are delivered as an `AsyncStream>`.
##  Starting a live query[](https://surrealdb.com/docs/reference/swift/concepts/live-queries#starting-a-live-query)

```swift
let client = try SurrealWebSocketClient(endpoint: "ws://localhost:8000")
try await client.connect()
_ = try await client.signin(.root(username: "root", password: "root"))
try await client.use(namespace: "myapp", database: "mydb")

let stream = try await client.live(SurrealDSL.live(Person.self))
```

##  Consuming events[](https://surrealdb.com/docs/reference/swift/concepts/live-queries#consuming-events)
Iterate the stream with `for await` and switch on the event's `action`:

```swift
for await event in stream {
    switch event.action {
    case .create:
        print("Created:", event.decoded as Any)
    case .update:
        print("Updated:", event.decoded as Any)
    case .delete:
        print("Deleted record:", event.recordID)
    case .killed:
        print("Live query was killed")
    }
}
```

##  Killing a live query[](https://surrealdb.com/docs/reference/swift/concepts/live-queries#killing-a-live-query)
To stop receiving events, kill the live query using its id:

```swift
try await client.kill(liveQueryID: event.queryID)
```

See the [`live`](https://surrealdb.com/docs/reference/swift/methods/live) and [`kill`](https://surrealdb.com/docs/reference/swift/methods/kill) method references for more detail.
