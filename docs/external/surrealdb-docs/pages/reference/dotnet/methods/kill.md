---
title: "https://surrealdb.com/docs/reference/dotnet/methods/kill"
url: "https://surrealdb.com/docs/reference/dotnet/methods/kill"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/kill

Source: https://surrealdb.com/docs/reference/dotnet/methods/kill

Kills a running live query by it's UUID.
Method Syntax

```csharp
await db.Kill(queryUuid)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/kill#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `queryUuid`  | The UUID of the live query you wish to kill.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/kill#example-usage)

```csharp
await db.Kill(queryUuid);
```
