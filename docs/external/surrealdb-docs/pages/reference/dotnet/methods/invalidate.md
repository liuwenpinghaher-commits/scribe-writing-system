---
title: "https://surrealdb.com/docs/reference/dotnet/methods/invalidate"
url: "https://surrealdb.com/docs/reference/dotnet/methods/invalidate"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/invalidate

Source: https://surrealdb.com/docs/reference/dotnet/methods/invalidate

Invalidates the authentication for the current connection.
Method Syntax

```csharp
await db.Invalidate()
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/invalidate#arguments)  
| Properties  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/invalidate#example-usage)

```csharp
await db.Invalidate();
```
