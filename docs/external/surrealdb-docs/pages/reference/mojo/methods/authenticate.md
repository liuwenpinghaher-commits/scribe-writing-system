---
title: "https://surrealdb.com/docs/reference/mojo/methods/authenticate"
url: "https://surrealdb.com/docs/reference/mojo/methods/authenticate"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/authenticate

Source: https://surrealdb.com/docs/reference/mojo/methods/authenticate

Authenticates the current connection with a token, and stores it on the client for subsequent requests.
Method Syntax

```python
client.authenticate(token, session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/authenticate#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `token`  | The JWT to authenticate with.  |  
| `session`  | An optional session id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/authenticate#example-usage)

```python
client.authenticate("eyJhbGciOi...")
```

###  See also[](https://surrealdb.com/docs/reference/mojo/methods/authenticate#see-also)
  * •
[Authentication](https://surrealdb.com/docs/reference/mojo/concepts/authentication)
  * •
[`invalidate()`](https://surrealdb.com/docs/reference/mojo/methods/invalidate)
