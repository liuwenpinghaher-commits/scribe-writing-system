---
title: "https://surrealdb.com/docs/reference/php/v1/methods/authenticate"
url: "https://surrealdb.com/docs/reference/php/v1/methods/authenticate"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/authenticate

Source: https://surrealdb.com/docs/reference/php/v1/methods/authenticate

Authenticates the current connection with a JWT token.
Method Syntax

```php
$db->authenticate($token)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/authenticate#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `token`  | `string`  | The JWT authentication token.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/authenticate#example-usage)

```php
$db->authenticate('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJTdXJyZWFsREIiLCJpYXQiOjE1MTYyMzkwMjIsIm5iZiI6MTUxNjIzOTAyMiwiZXhwIjoxODM2NDM5MDIyLCJOUyI6InRlc3QiLCJEQiI6InRlc3QiLCJTQyI6InVzZXIiLCJJRCI6InVzZXI6dG9iaWUifQ.N22Gp9ze0rdR06McGj1G-h2vu6a6n9IVqUbMFJlOxxA');
```

You can invalidate the authentication for the current connection using the [`invalidate()` method](https://surrealdb.com/docs/reference/php/v1/methods/invalidate).
