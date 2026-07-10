---
title: "https://surrealdb.com/docs/reference/dotnet/methods/info"
url: "https://surrealdb.com/docs/reference/dotnet/methods/info"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/info

Source: https://surrealdb.com/docs/reference/dotnet/methods/info

This method returns the record of an authenticated scope user.
Method Syntax

```csharp
await db.Info<T>()
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/info#arguments)  
| Properties  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/info#example-usage)

```csharp
var currentUser = await db.Info<User>();
```
