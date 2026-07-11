---
title: "https://surrealdb.com/docs/reference/dotnet/methods/health"
url: "https://surrealdb.com/docs/reference/dotnet/methods/health"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/health

Source: https://surrealdb.com/docs/reference/dotnet/methods/health

Checks the status of the database server and storage engine.
Method Syntax

```csharp
await db.Health()
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/health#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/health#example-usage)

```csharp
bool status = await db.Health();
```
