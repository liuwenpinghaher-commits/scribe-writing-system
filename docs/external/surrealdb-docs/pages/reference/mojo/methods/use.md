---
title: "https://surrealdb.com/docs/reference/mojo/methods/use"
url: "https://surrealdb.com/docs/reference/mojo/methods/use"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/use

Source: https://surrealdb.com/docs/reference/mojo/methods/use

Switches the connection to a specific namespace and database.
Method Syntax

```python
client.use(namespace, database, session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/use#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `namespace`  | The namespace to switch to.  |  
| `database`  | The database to switch to.  |  
| `session`  | An optional session id to scope the change to a specific session.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/use#example-usage)

```python
client.use("test", "test")
```
