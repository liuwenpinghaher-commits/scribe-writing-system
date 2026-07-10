---
title: "https://surrealdb.com/docs/reference/mojo/methods/kill"
url: "https://surrealdb.com/docs/reference/mojo/methods/kill"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/kill

Source: https://surrealdb.com/docs/reference/mojo/methods/kill

Stops a running live query, using the query id returned by [`live_query()`](https://surrealdb.com/docs/reference/mojo/methods/live).
Method Syntax

```python
client.kill(query_id, session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/kill#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `query_id`  | The id of the live query to stop.  |  
| `session`  | An optional session id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/kill#example-usage)

```python
var query_id = client.live_query("person")
# ... later ...
client.kill(query_id)
```

Note
Live queries run over a stateful WebSocket session. WebSocket support is rolling out. On the HTTP transport, the SDK raises an `UnsupportedFeatureError`.
###  See also[](https://surrealdb.com/docs/reference/mojo/methods/kill#see-also)
  * •
[Live queries](https://surrealdb.com/docs/reference/mojo/concepts/live-queries)
  * •
[`live_query()`](https://surrealdb.com/docs/reference/mojo/methods/live)
