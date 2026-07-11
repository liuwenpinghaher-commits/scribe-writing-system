---
title: "https://surrealdb.com/docs/reference/mojo/methods/version"
url: "https://surrealdb.com/docs/reference/mojo/methods/version"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/version

Source: https://surrealdb.com/docs/reference/mojo/methods/version

Returns the version of the connected SurrealDB server as an `RpcResponse`.
Method Syntax

```python
client.version()
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/version#arguments)
This method takes no arguments.
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/version#example-usage)

```python
var resp = client.version()
if resp.is_ok() and resp.result:
    print(resp.result.value())
```
