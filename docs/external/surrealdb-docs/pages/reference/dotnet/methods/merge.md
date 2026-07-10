---
title: "https://surrealdb.com/docs/reference/dotnet/methods/merge"
url: "https://surrealdb.com/docs/reference/dotnet/methods/merge"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/merge

Source: https://surrealdb.com/docs/reference/dotnet/methods/merge

Modifies all records in a table, or a specific record.
Method Syntax

```csharp
await db.Merge<T>(resource, data)
```

Note
This function merges the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/merge#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or the specific [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to merge.  |  
| `data`  | The data with which to modify the records.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/merge#example-usage)
Merging data within a single record

```csharp
// Only changes the fields specified in the merge object
var merge = new PersonMerge
{
    Id = ("person", "tobie"),
    Settings = new Settings
    {
        Active = true,
        Marketing = false,
    },
};
var result = await db.Merge<PersonMerge, Person>(merge);

// Only changes the fields specified in the Dictionary
var data = new Dictionary<string, object>
{
    { "tags", new List<string> { "developer", "engineer" } }
};

var result = await db.Merge<Person>(("person", "tobie"), data);
```

Merging data for every record in a table

```csharp
// Only changes the fields specified in the merge object
var merge = new PersonMerge
{
    Settings = new Settings
    {
        Active = true,
        Marketing = false,
    },
};
var result = await db.Merge<PersonMerge, Person>("person", merge);

// Only changes the fields specified in the Dictionary
var data = new Dictionary<string, object>
{
    { "tags", new List<string> { "developer", "engineer" } }
};

var result = await db.Merge<Person>("person", data);
```
