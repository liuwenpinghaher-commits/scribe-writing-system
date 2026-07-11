---
title: "https://surrealdb.com/docs/reference/mojo/methods/unset"
url: "https://surrealdb.com/docs/reference/mojo/methods/unset"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/unset

Source: https://surrealdb.com/docs/reference/mojo/methods/unset

Removes a parameter previously assigned with [`set()`](https://surrealdb.com/docs/reference/mojo/methods/set).
Method Syntax

```python
client.unset(name, session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/unset#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `name`  | The parameter name to remove.  |  
| `session`  | An optional session id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/unset#example-usage)

```python
client.unset("name")
```
