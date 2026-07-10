---
title: "https://surrealdb.com/docs/reference/dotnet/core/authentication"
url: "https://surrealdb.com/docs/reference/dotnet/core/authentication"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/authentication

Source: https://surrealdb.com/docs/reference/dotnet/core/authentication

Since SurrealDB is a database that is designed to be used in a distributed environment, it is important to secure the database and the data that is stored in it.  
SurrealDB provides a number of methods for authenticating users and securing the database.
In your SurrealDB database, you can create authentication login using the [`DEFINE ACCESS`](https://surrealdb.com/docs/reference/query-language/statements/define/access) statement which supports [JWT](https://surrealdb.com/docs/reference/query-language/statements/define/access/jwt) and [Record](https://surrealdb.com/docs/reference/query-language/statements/define/access/record) Access methods.
The access method used will inform the input for `Access` in the `.SignUp()` and `.SignIn()` methods.
Important
If you are not on Version `v3.2.0` of SurrealDB, you will use the `Scope` property instead of `Access`.  
| Method  | Description  |  
| --- | --- |  
| [` db.SignUp() `](https://surrealdb.com/docs/reference/dotnet/core/authentication#signup)  | Connects to a local or remote database endpoint  |  
| [` db.SignIn() `](https://surrealdb.com/docs/reference/dotnet/core/authentication#signin)  | Signs in to a root, namespace, database or scope user  |  
| [` db.Invalidate() `](https://surrealdb.com/docs/reference/dotnet/core/authentication#invalidate)  | Invalidates the current session  |  
| [` db.Authenticate() `](https://surrealdb.com/docs/reference/dotnet/core/authentication#authenticate)  | Authenticates a user with a token  |  
##  Defining access in your application[](https://surrealdb.com/docs/reference/dotnet/core/authentication#defining-access-in-your-application)
The .NET SDK has a [`.Query()` method](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql) which allows you to write secure SurrealQL statements from within your application. Using this method, you can define access for your users and securely manage authentication. See the code example below:

```csharp
await db.Query(
    $"""
    DEFINE ACCESS account ON DATABASE TYPE RECORD
		SIGNUP ( CREATE user SET email = $email,
	    pass = crypto::argon2::generate($pass) )
	SIGNIN ( SELECT * FROM user WHERE email = $email AND crypto::argon2::compare(pass, $pass) )
	DURATION FOR TOKEN 15m, FOR SESSION 12h;
    """
);
```

Note
Depending on the connection protocol you choose, authentication tokens and sessions lifetime work differently. Refer to the [connection options](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection#connection-options) documentation for more information.
##  User authentication[](https://surrealdb.com/docs/reference/dotnet/core/authentication#user-authentication)
After you have defined your authentication login, you can use the following methods to authenticate users:
##  `.SignUp()`[](https://surrealdb.com/docs/reference/dotnet/core/authentication#signup)
Signs up to a specific authentication scope / access method.
Method Syntax

```csharp
await db.SignUp(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/authentication#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `credentials`  | Credentials to sign up as a scoped user.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/authentication#example-usage)

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

  

##  `.SignIn()`[](https://surrealdb.com/docs/reference/dotnet/core/authentication#signin)
Signs in to a root, namespace, database or scope user.
Method Syntax

```csharp
await db.SignIn(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/authentication#arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `credentials`  | Variables used in a signin query.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/authentication#example-usage-1)
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

  

##  `.Authenticate()`[](https://surrealdb.com/docs/reference/dotnet/core/authentication#authenticate)
Authenticates the current connection with a JWT token.
Method Syntax

```csharp
await db.Authenticate(jwt)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/authentication#arguments-2)  
| Arguments  | Description  |  
| --- | --- |  
| `jwt`  | The JWT object holder of the authentication token.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/authentication#example-usage-2)

```csharp
var jwt = new Jwt("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJTdXJyZWFsREIiLCJpYXQiOjE1MTYyMzkwMjIsIm5iZiI6MTUxNjIzOTAyMiwiZXhwIjoxODM2NDM5MDIyLCJOUyI6InRlc3QiLCJEQiI6InRlc3QiLCJTQyI6InVzZXIiLCJJRCI6InVzZXI6dG9iaWUifQ.N22Gp9ze0rdR06McGj1G-h2vu6a6n9IVqUbMFJlOxxA");
await db.Authenticate(jwt);
```

  

##  `.Invalidate()`[](https://surrealdb.com/docs/reference/dotnet/core/authentication#invalidate)
Invalidates the authentication for the current connection.
Method Syntax

```csharp
await db.Invalidate()
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/authentication#arguments-3)  
| Properties  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/authentication#example-usage-3)

```csharp
await db.Invalidate();
```
