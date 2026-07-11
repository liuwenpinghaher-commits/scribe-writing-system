---
title: "https://surrealdb.com/docs/reference/dotnet/methods/patch"
url: "https://surrealdb.com/docs/reference/dotnet/methods/patch"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/patch

Source: https://surrealdb.com/docs/reference/dotnet/methods/patch

Applies JSON Patch changes to all records, or a specific record, in the database.
Method Syntax

```csharp
await db.Patch<T>(resource, data)
```

Note
This function patches document / record data with the specified [JSON Patch](https://jsonpatch.com/) data.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/patch#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or the specific [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to patch.  |  
| `data`  | The JSON Patch data with which to patch the records.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/patch#example-usage)

```csharp
// Update a record with a specific ID
var result = await db.Patch(("person", "tobie"), patches);

// Update all records in a table
var result = await db.Patch("person", patches);
```
