---
title: "https://surrealdb.com/docs/reference/dotnet/methods/signup"
url: "https://surrealdb.com/docs/reference/dotnet/methods/signup"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/signup

Source: https://surrealdb.com/docs/reference/dotnet/methods/signup

Signs up to a specific authentication scope / access method.
Method Syntax

```csharp
await db.SignUp(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/signup#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `credentials`  | Credentials to sign up as a scoped user.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/signup#example-usage)

```csharp
// With Record Access
var authParams = new AuthParams
{
    Namespace = "main",
    Database = "main",
    Access = "user",
	// Also pass any properties required by the access definition
    Email = "info@surrealdb.com",
    Password = "123456"
};

Jwt jwt = await db.SignUp(authParams);

public class AuthParams : ScopeAuth
{
	public string? Username { get; set; }
	public string? Email { get; set; }
	public string? Password { get; set; }
}
```

You can invalidate the authentication for the current connection using the [`Invalidate()` method](https://surrealdb.com/docs/reference/dotnet/methods/invalidate).
