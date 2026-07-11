---
title: "https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection"
url: "https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection

Source: https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection

After [installing the SDK](https://surrealdb.com/docs/reference/dotnet/installation), you can initialize a new instance of a SurrealDB client.  
When creating a new connection to a SurrealDB instance, you can choose to connect to a local or remote endpoint.

```csharp
using SurrealDb.Net;

using var db = new SurrealDbClient("ws://127.0.0.1:8000/rpc");

await db.Connect();
await db.Use("main", "main");
```

From the code snippet above, you can see that the .NET SDK has a couple of methods that you can use to initialize a new project with SurrealDB. 
##  `SurrealDbClient`[](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection#surrealdbclient)
Creates a new client, detecting the right protocol from the provided endpoint.
Method Syntax

```csharp
new SurrealDbClient(endpoint)
```

###  Connection options[](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection#connection-options)
You can specify your connection protocol either as `http`, `https`, `ws`, or `wss`.  
Since SurrealDB also supports RPC over WebSocket, by default, it is specified with a `/rpc` suffix. 
Local endpointRemote endpointNamespace and databaseTokenCredentials

```csharp
// Creates a new client using a local endpoint
using var db = new SurrealDbClient("http://127.0.0.1:8000");
```

```csharp
// Creates a new client using a remote endpoint
using var db = new SurrealDbClient("wss://cloud.surrealdb.com/rpc");
```

```csharp
var options = new SurrealDbOptions
{
    Endpoint = "wss://cloud.surrealdb.com/rpc",
    Namespace = "surrealdb",
    Database = "docs",
};

// Specify a namespace and database pair to use
using var db = new SurrealDbClient(options);
```

```csharp
var options = new SurrealDbOptions
{
    Endpoint = "wss://cloud.surrealdb.com/rpc",
    Token = "......",
};

// Authenticate with an existing token
using var db = new SurrealDbClient(options);
```

```csharp
var options = new SurrealDbOptions
{
    Endpoint = "wss://cloud.surrealdb.com/rpc",
    Username = "root",
    Password = "surrealdb",
};

// Authenticate using a pair of credentials
using var db = new SurrealDbClient(options);
```

Note
Having to manually set all these options into a `SurrealDbOptions` object can be cumbersome.  
If you are familiar with the concept of Connection Strings, you can simply pass a connection string to the `SurrealDbClient` constructor.  
See the [Connection Strings](https://surrealdb.com/docs/reference/dotnet/core/connection-strings) section for more information.
  

###  Effect of connection protocol on token & session duration[](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection#effect-of-connection-protocol-on-token--session-duration)
The connection protocol you choose affects how authentication tokens and sessions work:
With websockets connections (`ws://`, `wss://`) you open a single long-lived stateful connection where after the initial authentication, the session duration applies and if not specified, defaults to `NONE` meaning that the session never expires unless otherwise specified. 
When you connect with a HTTP connection (`http://`, `https://`), every request you make is short-lived and stateless, requiring you to authenticate every request individually for which the token is used, creating a short lived session. Hence, the token duration which defaults to 1 hour applies.
You can extend the session duration of a token or a session by setting the `DURATION` clause when creating a new access method with the [`DEFINE ACCESS METHOD`](https://surrealdb.com/docs/reference/query-language/statements/define/access) statement or when defining a new user with the [`DEFINE USER`](https://surrealdb.com/docs/reference/query-language/statements/define/user) statement. 
Learn more about token and session duration in our [security best practices](https://surrealdb.com/docs/learn/security/best-practices/security-best-practices#expiration) documentation.
  

##  `.Connect()`[](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection#connect)
The `.Connect()` executes a connection attempt to the underlying endpoint using the provided connection options.
Note
This method is automatically called before executing any other call to the SurrealDB instance.  
It means that you do not have to explicitely call this method.  
Just note that in some contexts, calling this method before hand can improve performance by avoiding cold starts.
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection#example-usage)

```csharp
await db.Connect();
```

  

##  `.Use()`[](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection#use)
Depending on the complexity of your use case, you can switch to a specific namespace and database using the `.Use()` method.  
This is particularly useful if you want to switch to a different setup after connecting.
Learn more about the `.Use()` method [in the methods section](https://surrealdb.com/docs/reference/dotnet/methods/use).
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection#example-usage-1)

```csharp
await db.Use("main", "main");
```
