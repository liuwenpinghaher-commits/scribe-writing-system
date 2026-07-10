---
title: "https://surrealdb.com/docs/reference/dotnet/methods/delete"
url: "https://surrealdb.com/docs/reference/dotnet/methods/delete"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/delete

Source: https://surrealdb.com/docs/reference/dotnet/methods/delete

Method Syntax

```csharp
await db.Delete(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/delete#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to delete.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/delete#example-usage)

```csharp
// Delete all records from a table
await db.Delete("person");

// Delete a specific record from a table
await db.Delete(("person", "h5wxrf2ewk8xjxosxtyc"));
```
