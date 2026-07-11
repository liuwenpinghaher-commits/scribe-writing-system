---
title: "https://surrealdb.com/docs/reference/mojo/methods/connect"
url: "https://surrealdb.com/docs/reference/mojo/methods/connect"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/connect

Source: https://surrealdb.com/docs/reference/mojo/methods/connect

Connects to a database endpoint. The URL scheme selects the transport (`http`, `https`, `ws`, or `wss`).
Method Syntax

```python
client.connect(endpoint, connect_options)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/connect#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `endpoint`  |  The database endpoint to connect to, ending in `/rpc`.  |  
| `connect_options`  |  An optional `ConnectOptions`carrying the namespace, database, credentials, TLS setting, and wire format.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/connect#example-usage)

```python
from surrealdb import AsyncSurrealClient, ConnectOptions
from std.collections import Optional

def main():
    var client = AsyncSurrealClient()
    _ = client.connect(
        "http://localhost:8000/rpc",
        ConnectOptions(
            namespace=Optional(String("test")),
            database=Optional(String("test")),
            access_token=Optional(String("Basic cm9vdDpyb290")),
        ),
    )
```

`connect()` returns a `Bool`.
###  See also[](https://surrealdb.com/docs/reference/mojo/methods/connect#see-also)
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb)
