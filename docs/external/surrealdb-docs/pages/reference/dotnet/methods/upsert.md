---
title: "https://surrealdb.com/docs/reference/dotnet/methods/upsert"
url: "https://surrealdb.com/docs/reference/dotnet/methods/upsert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/upsert

Source: https://surrealdb.com/docs/reference/dotnet/methods/upsert

Creates or updates a specific record.
Method Syntax

```csharp
await db.Upsert<T>(data)
```

Note
This function creates a new document / record or replaces the current one with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/upsert#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `data`  | The document / record data to insert.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/upsert#example-usage)

```csharp
var person = new Person
{
        Id = ("person", "tobie"),
        // Id is mandatory to apply create or update
    Name = "Tobie",
    Settings = new Settings
    {
        Active = true,
        Marketing = true,
    },
};

// Create a new record when it doesn't exist
var created = await db.Upsert(person);

// Update an existing record when it does exist
var updated = await db.Upsert(person);
```
