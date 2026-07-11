---
title: "https://surrealdb.com/docs/reference/dotnet/methods/signin"
url: "https://surrealdb.com/docs/reference/dotnet/methods/signin"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/signin

Source: https://surrealdb.com/docs/reference/dotnet/methods/signin

Signs in to a root, namespace, database or scope user.
Method Syntax

```csharp
await db.SignIn(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/signin#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `credentials`  | Variables used in a signin query.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/signin#example-usage)
Root userNamespace userDatabase userRecord AccessScopes

```csharp
// Sign in as root user
await db.SignIn(new RootAuth { Username = "root",
    Password = "secret" });
```

```csharp
// Sign in using namespace auth
await db.SignIn(
    new NamespaceAuth
    {
        Namespace = "main", 
        Username = "johndoe", 
        Password = "password123" 
    }
);
```

```csharp
// Sign in using database auth
await db.SignIn(
    new DatabaseAuth
    {
        Namespace = "main", 
        Database = "main", 
        Username = "johndoe", 
        Password = "password123" 
    }
);
```

```csharp
// Sign in with Record Access
var authParams = new AuthParams
{
    Namespace = "main",
    Database = "main",
    Access = "user",
    Email = "info@surrealdb.com",
    Password = "123456"
};

Jwt jwt = await db.SignIn(authParams);

public class AuthParams : ScopeAuth
{
	public string? Username { get; set; }
	public string? Email { get; set; }
	public string? Password { get; set; }
}
```

```csharp
// Sign in as a scoped user
var authParams = new AuthParams
{
    Namespace = "main",
    Database = "main",
    Scope = "user",
    Email = "info@surrealdb.com",
    Password = "123456"
};

Jwt jwt = await db.SignIn(authParams);

public class AuthParams : ScopeAuth
{
	public string? Username { get; set; }
	public string? Email { get; set; }
	public string? Password { get; set; }
}
```

You can invalidate the authentication for the current connection using the [`Invalidate()` method](https://surrealdb.com/docs/reference/dotnet/methods/invalidate).
