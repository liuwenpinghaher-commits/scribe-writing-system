---
title: "https://surrealdb.com/docs/reference/dotnet/methods/set"
url: "https://surrealdb.com/docs/reference/dotnet/methods/set"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/set

Source: https://surrealdb.com/docs/reference/dotnet/methods/set

Assigns a value as a parameter for this connection.
Method Syntax

```csharp
await db.Set(key, value)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/set#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `key`  | Specifies the name of the variable.  |  
| `value`  | Assigns the value to the variable name.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/set#example-usage)

```csharp
// Assign the variable on the connection
await db.Set("name", new Name { FirstName = "Tobie",
    LastName = "Morgan Hitchcock" });

// Use the variable in a subsequent query
await db.Query($"CREATE person SET name = $name");

// Use the variable in a subsequent query
await db.Query($"SELECT * FROM person WHERE name.first_name = $name.first_name");
```

You can remove the variable from the connection using the [`Unset()` method](https://surrealdb.com/docs/reference/dotnet/methods/unset).
