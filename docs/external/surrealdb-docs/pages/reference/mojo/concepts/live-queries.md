---
title: "https://surrealdb.com/docs/reference/mojo/concepts/live-queries"
url: "https://surrealdb.com/docs/reference/mojo/concepts/live-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/concepts/live-queries

Source: https://surrealdb.com/docs/reference/mojo/concepts/live-queries

A live query subscribes to a table and receives a notification whenever a matching record is created, updated, or deleted. Notifications arrive on the WebSocket transport out of band, and the SDK queues them as they come in.
Note
Live queries run over a stateful WebSocket session. WebSocket support is rolling out. On the HTTP transport, the engine reports `live_queries=False` and the SDK raises an `UnsupportedFeatureError`.
##  Starting a live query[](https://surrealdb.com/docs/reference/mojo/concepts/live-queries#starting-a-live-query)
`live_query()` subscribes to a table and returns the query id as a string. `live_raw()` returns the full `RpcResponse` if you need it.

```python
var query_id = client.live_query("person")
```

##  Receiving notifications[](https://surrealdb.com/docs/reference/mojo/concepts/live-queries#receiving-notifications)
The transport queues notifications as they arrive. Pull them out with `poll_notifications()`, which drains every queued notification across all live queries.

```python
var notifications = client.poll_notifications()
for ref in notifications:
    print(ref[].query_id, ref[].action)
```

Each entry is a `LiveNotificationRaw` carrying the query id, the action, and the raw record bytes.
##  Stopping a live query[](https://surrealdb.com/docs/reference/mojo/concepts/live-queries#stopping-a-live-query)
Stop a subscription with `kill()`, passing the query id returned by `live_query()`.

```python
client.kill(query_id)
```

See the method reference for [`live`](https://surrealdb.com/docs/reference/mojo/methods/live) and [`kill`](https://surrealdb.com/docs/reference/mojo/methods/kill).
