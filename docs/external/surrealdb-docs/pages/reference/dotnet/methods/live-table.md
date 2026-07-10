---
title: "https://surrealdb.com/docs/reference/dotnet/methods/live-table"
url: "https://surrealdb.com/docs/reference/dotnet/methods/live-table"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/live-table

Source: https://surrealdb.com/docs/reference/dotnet/methods/live-table

Initiate a live query from a table.
Method Syntax

```csharp
await db.LiveTable<T>(table, diff)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/live-table#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `table`  | The table name to listen for changes for.  |  
| `diff`  | If set to true, live notifications will include an array of JSON Patch objects, rather than the entire record for each notification.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/live-table#example-usage)

```csharp
await using var liveQuery = await db.LiveTable<Person>("person");

// Consume the live query...
```
