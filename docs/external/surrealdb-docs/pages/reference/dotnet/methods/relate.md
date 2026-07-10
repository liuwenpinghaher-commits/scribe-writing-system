---
title: "https://surrealdb.com/docs/reference/dotnet/methods/relate"
url: "https://surrealdb.com/docs/reference/dotnet/methods/relate"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/relate

Source: https://surrealdb.com/docs/reference/dotnet/methods/relate

Creates a relation between records.
Method Syntax

```csharp
await db.Relate(table, @in, @out, data)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/relate#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to create.  |  
| `@in`  | The edge of the relation.  |  
| `@out`  | The other edge of the relation.  |  
| `data`  | The document / record data to insert.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/relate#example-usage)

```csharp
var data = new WroteRelation { CreatedAt = DateTime.UtcNow,
    NumberOfPages = 14 };

await db.Relate<WroteRelation, WroteRelation>(
    "wrote",
    ("user", "one"),
    ("post", "one"),
    data
);
```
