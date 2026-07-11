---
title: "https://surrealdb.com/docs/reference/dotnet/methods/insert-relation"
url: "https://surrealdb.com/docs/reference/dotnet/methods/insert-relation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/insert-relation

Source: https://surrealdb.com/docs/reference/dotnet/methods/insert-relation

Inserts one or multiple relations in the database.
Method Syntax

```csharp
await db.InsertRelation<T>(table, data)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/insert-relation#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `table`  | Optionally pass along a table to insert into.  |  
| `data`  | Either a single document/record or an array of documents/records to insert  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/insert-relation#example-usage)

```csharp
await db.InsertRelation(
    new WroteRelation
    {
        In = ("user", "u1"),
        Out = ("post", "p1"),
        CreatedAt = now,
        NumberOfPages = 144
    }
);
```
