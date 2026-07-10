---
title: "https://surrealdb.com/docs/reference/dotnet/methods/live-query"
url: "https://surrealdb.com/docs/reference/dotnet/methods/live-query"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/live-query

Source: https://surrealdb.com/docs/reference/dotnet/methods/live-query

Initiate a live query from a SurrealQL statement.
Method Syntax

```csharp
await db.LiveQuery<T>(sql)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/live-query#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/live-query#example-usage)

```csharp
const string table = "person"; 
await using var liveQuery = await db.LiveQuery<Person>($"LIVE SELECT * FROM type::table({table});");

// Consume the live query...
```
