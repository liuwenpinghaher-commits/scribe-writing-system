---
title: "https://surrealdb.com/docs/reference/swift/methods/kill"
url: "https://surrealdb.com/docs/reference/swift/methods/kill"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/kill

Source: https://surrealdb.com/docs/reference/swift/methods/kill

Kills a running [live query](https://surrealdb.com/docs/reference/swift/methods/live) by its id, ending the associated `AsyncStream`.
Method Syntax

```swift
try await client.kill(liveQueryID: id)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/kill#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `liveQueryID`  |  The id of the live query to kill, available as `event.queryID`on received events.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/kill#example-usage)

```swift
try await client.kill(liveQueryID: event.queryID)
```
