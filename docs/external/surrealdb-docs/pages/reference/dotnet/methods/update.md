---
title: "https://surrealdb.com/docs/reference/dotnet/methods/update"
url: "https://surrealdb.com/docs/reference/dotnet/methods/update"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/update

Source: https://surrealdb.com/docs/reference/dotnet/methods/update

Updates all records in a table, or a specific record, in the database.
Method Syntax

```csharp
await db.Update<T>(thing, data)
```

Note
This function replaces the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/update#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or the specific [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to update.  |  
| `data`  | The document / record data to update.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/update#example-usage)

```csharp
var post = new Post
{
    Id = ("post", "another"),
    Title = "A new article",
    Content = "This is a new article created using the .NET SDK"
};

// Updates a single record
await db.Update(post);

var data = new Person
{
    Name = "Tobie",
    Settings = new Settings
    {
        Active = true,
        Marketing = true,
    },
};

// Updates all records inside the "person" table
await db.Update("person", data);
```
