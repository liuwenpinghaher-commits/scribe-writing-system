---
title: "https://surrealdb.com/docs/reference/mojo/methods/health"
url: "https://surrealdb.com/docs/reference/mojo/methods/health"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/health

Source: https://surrealdb.com/docs/reference/mojo/methods/health

Runs a health check to verify that the server is reachable and accepting commands.
Method Syntax

```python
client.health()
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/health#arguments)
This method takes no arguments.
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/health#example-usage)

```python
client.health()
```

If the server is unreachable, the call raises a `ConnectionError`.
