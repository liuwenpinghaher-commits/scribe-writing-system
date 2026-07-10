---
title: "https://surrealdb.com/docs/reference/swift/methods/live"
url: "https://surrealdb.com/docs/reference/swift/methods/live"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/live

Source: https://surrealdb.com/docs/reference/swift/methods/live

Subscribes to changes on a table and returns an `AsyncStream>` of events.
Important
Live queries require the [WebSocket client](https://surrealdb.com/docs/reference/swift/concepts/connecting#websocket-client).
Method Syntax

```swift
try await client.live(query)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/live#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `query`  |  A live query built with `SurrealDSL.live(_:)`or the `#live`macro.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/live#example-usage)

```swift
let stream = try await client.live(SurrealDSL.live(Person.self))

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

See [Live queries](https://surrealdb.com/docs/reference/swift/concepts/live-queries) for a full walkthrough, and [`kill`](https://surrealdb.com/docs/reference/swift/methods/kill) to stop a subscription.
