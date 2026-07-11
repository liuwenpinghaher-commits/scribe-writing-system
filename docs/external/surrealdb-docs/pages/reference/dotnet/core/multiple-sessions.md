---
title: "https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions"
url: "https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions

Source: https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions

The .NET SDK allows you to create multiple isolated sessions within a single connection. Each session maintains its own namespace, database, variables, and authentication state, while sharing the underlying connection to SurrealDB. This is useful when different parts of your application need to operate under different credentials or contexts simultaneously.  
| Method  | Description  |  
| --- | --- |  
| [` db.Sessions() `](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#sessions)  | List all active sessions on the current connection.  |  
| [` db.CreateSession() `](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#createsession)  | Create a new isolated session on the current connection.  |  
| [` session.ForkSession() `](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#forksession)  | Creates a copy of a session, inheriting its state.  |  
| [` session.CloseSession() `](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#closesession)  | Closes the current session and disposes of it. After this method is  
called, the session cannot be used again.  |  
##  `.Sessions()`[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#sessions)
Returns a list of all active sessions on the current connection.
Method Syntax

```csharp
await db.Sessions(cancellationToken)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous  
operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#example-usage)

```csharp
// List all active sessions on the current connection
IEnumerable<Guid> sessions = await db.Sessions();
```

  

##  `.CreateSession()`[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#createsession)
Creates a new isolated session on the current connection. The new session is independent and maintains its own namespace, database, variables, and authentication state.
Method Syntax

```csharp
await db.CreateSession(cancellationToken)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous  
operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#example-usage-1)

```csharp
// Create a new isolated session on the same connection
var session = await db.CreateSession();

// Use the session independently
await session.Use("my_namespace", "my_database");
await session.SignIn(new RootAuth { Username = "root",
    Password = "root" });
```

  

##  `.ForkSession()`[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#forksession)
Creates a copy of the current session, inheriting its namespace, database, variables, and authentication state. Changes made in the forked session do not affect the original.
Method Syntax

```csharp
await session.ForkSession(cancellationToken)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#arguments-2)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous  
operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#example-usage-2)

```csharp
// Fork the current session to create an independent copy
var forkedSession = await session.ForkSession();

// The forked session inherits namespace, database, and auth state
// Changes made here do not affect the original session
await forkedSession.Set("x", 42);
```

  

##  `.CloseSession()`[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#closesession)
Closes the current session and disposes of it. After this method is called, the session cannot be used again.
Note
`CloseSession()` only closes the session itself. The underlying connection shared with the parent `SurrealDbClient` remains open.
Method Syntax

```csharp
await session.CloseSession(cancellationToken)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#arguments-3)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous  
operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/multiple-sessions#example-usage-3)

```csharp
// Close and dispose of the session when done
await session.CloseSession();

// The session can no longer be used after this call
```
