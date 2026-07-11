---
title: "https://surrealdb.com/docs/reference/dotnet/methods/unset"
url: "https://surrealdb.com/docs/reference/dotnet/methods/unset"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/unset

Source: https://surrealdb.com/docs/reference/dotnet/methods/unset

Removes a parameter for this connection.
Method Syntax

```csharp
await db.Unset(key)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/unset#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `key`  | Specifies the SurrealQL statements.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/unset#example-usage)

```csharp
await db.Unset("name");
```
