---
title: "https://surrealdb.com/docs/reference/mojo/methods/live"
url: "https://surrealdb.com/docs/reference/mojo/methods/live"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/live

Source: https://surrealdb.com/docs/reference/mojo/methods/live

Starts a live query on a table and returns the query id as a string. Notifications arrive out of band and are queued by the transport; pull them out with `poll_notifications()`.
Method Syntax

```python
client.live_query(table, session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/live#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `table`  | The table to subscribe to.  |  
| `session`  | An optional session id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/live#example-usage)

```python
var query_id = client.live_query("person")

var notifications = client.poll_notifications()
for ref in notifications:
    print(ref[].query_id, ref[].action)
```

To get the full `RpcResponse` instead of just the query id, use `live_raw(table, session)`.
Note
Live queries run over a stateful WebSocket session. WebSocket support is rolling out. On the HTTP transport, the engine reports `live_queries=False` and the SDK raises an `UnsupportedFeatureError`.
###  See also[](https://surrealdb.com/docs/reference/mojo/methods/live#see-also)
  * •
[Live queries](https://surrealdb.com/docs/reference/mojo/concepts/live-queries)
  * •
[`kill()`](https://surrealdb.com/docs/reference/mojo/methods/kill)
