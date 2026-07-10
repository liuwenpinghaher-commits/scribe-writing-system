---
title: "https://surrealdb.com/docs/reference/dotnet/methods/create"
url: "https://surrealdb.com/docs/reference/dotnet/methods/create"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/create

Source: https://surrealdb.com/docs/reference/dotnet/methods/create

Creates a record in the database.
Method Syntax

```csharp
await db.Create<T>(resource, data)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/create#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to create.  |  
| `data`  | The document / record data to insert.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/create#example-usage)

```csharp
// Create a record with a random ID
var person = await db.Create<Person>("person");

// Create a record with a random ID & specific fields
var person = await db.Create("person", new Person { Name = "Tobie" });

// Create a record with a specific ID
var personToCreate = new Person
{
    Id = ("person", "tobie"),
    Name = "Tobie",
    Settings = new Settings
    {
        Active = true,
        Marketing = true,
    },
};
var result = await db.Create(personToCreate);
```
