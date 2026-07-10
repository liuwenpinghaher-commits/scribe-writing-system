---
title: "https://surrealdb.com/docs/reference/dotnet/methods/insert"
url: "https://surrealdb.com/docs/reference/dotnet/methods/insert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/insert

Source: https://surrealdb.com/docs/reference/dotnet/methods/insert

Inserts one or multiple records in the database.
Method Syntax

```csharp
await db.Insert<T>(table, data)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/insert#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `table`  | Optionally pass along a table to insert into.  |  
| `data`  | Either a single document/record or an array of documents/records to insert  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/insert#example-usage)

```csharp
var posts = new List<Post>
{
    new Post
    {
        Id = ("post", "First"),
        Title = "An article",
        Content = "This is the first article"
    },
    new Post
    {
        Id = ("post", "Second"),
        Title = "An article",
        Content = "This is the second article"
    }
};

await db.Insert("post", posts);
```
