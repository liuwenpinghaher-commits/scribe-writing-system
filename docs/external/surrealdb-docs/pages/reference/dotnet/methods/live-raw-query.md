---
title: "https://surrealdb.com/docs/reference/dotnet/methods/live-raw-query"
url: "https://surrealdb.com/docs/reference/dotnet/methods/live-raw-query"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/live-raw-query

Source: https://surrealdb.com/docs/reference/dotnet/methods/live-raw-query

Initiate a live query from a SurrealQL statement, based on a raw SurrealQL query.
Method Syntax

```csharp
await db.LiveRawQuery<T>(sql, params)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/live-raw-query#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `params`  | Assigns variables which can be used in the query.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/live-raw-query#example-usage)

```csharp
await using var liveQuery = await db.LiveRawQuery<Person>("LIVE SELECT * FROM person;");

// Consume the live query...
```
