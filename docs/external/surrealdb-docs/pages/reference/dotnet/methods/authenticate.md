---
title: "https://surrealdb.com/docs/reference/dotnet/methods/authenticate"
url: "https://surrealdb.com/docs/reference/dotnet/methods/authenticate"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/authenticate

Source: https://surrealdb.com/docs/reference/dotnet/methods/authenticate

Authenticates the current connection with a JWT token.
Method Syntax

```csharp
await db.Authenticate(jwt)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/authenticate#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `jwt`  | The JWT object holder of the authentication token.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/authenticate#example-usage)

```csharp
Jwt jwt = new JWT("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJTdXJyZWFsREIiLCJpYXQiOjE1MTYyMzkwMjIsIm5iZiI6MTUxNjIzOTAyMiwiZXhwIjoxODM2NDM5MDIyLCJOUyI6InRlc3QiLCJEQiI6InRlc3QiLCJTQyI6InVzZXIiLCJJRCI6InVzZXI6dG9iaWUifQ.N22Gp9ze0rdR06McGj1G-h2vu6a6n9IVqUbMFJlOxxA");
await db.Authenticate(jwt);
```

You can invalidate the authentication for the current connection using the [`Invalidate()` method](https://surrealdb.com/docs/reference/dotnet/methods/invalidate).
