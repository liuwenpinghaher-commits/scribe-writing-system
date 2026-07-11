---
title: "https://surrealdb.com/docs/reference/dotnet/core/parameters"
url: "https://surrealdb.com/docs/reference/dotnet/core/parameters"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/parameters

Source: https://surrealdb.com/docs/reference/dotnet/core/parameters

Within your application, you can define parameters that can be used to store and retrieve data from SurrealDB.  
Parameters are used to store data in a structured format, and can be used to store data in a key-value pair format.
Important
Parameters allow you to define global (database-wide) parameters that are available to every client.  
| Method  | Description  |  
| --- | --- |  
| [` db.Set(key, value) `](https://surrealdb.com/docs/reference/dotnet/core/parameters#set)  | Assigns a value as a parameter for this connection  |  
| [` db.Unset(key) `](https://surrealdb.com/docs/reference/dotnet/core/parameters#unset)  | Removes a parameter for this connection  |  
##  `.Set()`[](https://surrealdb.com/docs/reference/dotnet/core/parameters#set)
Assigns a value as a parameter for this connection.
Method Syntax

```csharp
await db.Set(key, val)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/parameters#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `key`  | Specifies the name of the variable.  |  
| `value`  | Assigns the value to the variable name.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/parameters#example-usage)

```csharp
// Assign the variable on the connection
await db.Set("name", new Name { FirstName = "Tobie",
    LastName = "Morgan Hitchcock" });

// Use the variable in a subsequent query
await db.Query($"CREATE person SET name = $name");

// Use the variable in a subsequent query
await db.Query($"SELECT * FROM person WHERE name.first_name = $name.first_name");
```

  

##  `.Unset()`[](https://surrealdb.com/docs/reference/dotnet/core/parameters#unset)
Removes a parameter for this connection.
Method Syntax

```csharp
await db.Unset(key)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/parameters#arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `key`  | Specifies the SurrealQL statements.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/parameters#example-usage-1)

```csharp
await db.Unset("name");
```
