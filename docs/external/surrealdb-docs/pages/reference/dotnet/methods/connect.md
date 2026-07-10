---
title: "https://surrealdb.com/docs/reference/dotnet/methods/connect"
url: "https://surrealdb.com/docs/reference/dotnet/methods/connect"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/connect

Source: https://surrealdb.com/docs/reference/dotnet/methods/connect

Connects the client to the underlying endpoint, also improving performance to avoid cold starts.
Method Syntax

```csharp
await db.Connect()
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/connect#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/connect#example-usage)

```csharp
await db.Connect();
```
