---
title: "https://surrealdb.com/docs/reference/dotnet/methods/use"
url: "https://surrealdb.com/docs/reference/dotnet/methods/use"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/use

Source: https://surrealdb.com/docs/reference/dotnet/methods/use

Switch to a specific namespace and database.
Method Syntax

```csharp
await db.Use(ns, db)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/use#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `namespace`  | Switches to a specific namespace.  |  
| `database`  | Switches to a specific database.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/use#example-usage)

```csharp
await db.Use("main", "main");
```
