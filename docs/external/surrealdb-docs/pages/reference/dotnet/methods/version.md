---
title: "https://surrealdb.com/docs/reference/dotnet/methods/version"
url: "https://surrealdb.com/docs/reference/dotnet/methods/version"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/version

Source: https://surrealdb.com/docs/reference/dotnet/methods/version

Retrieves the version of the SurrealDB instance.
Method Syntax

```csharp
await db.Version()
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/version#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/version#example-usage)

```csharp
string version = await db.Version(); // Will return "surrealdb-1.1.1"
```
