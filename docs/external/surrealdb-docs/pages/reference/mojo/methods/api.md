---
title: "https://surrealdb.com/docs/reference/mojo/methods/api"
url: "https://surrealdb.com/docs/reference/mojo/methods/api"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/api

Source: https://surrealdb.com/docs/reference/mojo/methods/api

Calls a custom API handler defined on the database with [`DEFINE API`](https://surrealdb.com/docs/surrealql/statements/define/api).
Method Syntax

```python
client.api(path, method, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/api#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `path`  | The API path to call.  |  
| `method`  |  The HTTP method. Defaults to `"GET"`.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/api#example-usage)

```python
var resp = client.api("/users", "GET")
```

Note
The API endpoint is checked against the active transport's capabilities. If the transport does not support it, the SDK raises an `UnsupportedFeatureError`.
