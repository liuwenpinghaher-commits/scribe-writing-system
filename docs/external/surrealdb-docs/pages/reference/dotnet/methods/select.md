---
title: "https://surrealdb.com/docs/reference/dotnet/methods/select"
url: "https://surrealdb.com/docs/reference/dotnet/methods/select"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/select

Source: https://surrealdb.com/docs/reference/dotnet/methods/select

Selects all records in a table, or a specific record, from the database.
Method Syntax

```csharp
await db.Select<T>(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/select#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to select.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/select#example-usage)

```csharp
// Select all records from a table
var people = await db.Select<Person>("person");

// Select a specific record from a table
var person = await db.Select<Person>(("person",
    "h5wxrf2ewk8xjxosxtyc"));
var person = await db.Select<Person>(new StringRecordId("person:h5wxrf2ewk8xjxosxtyc"));

// Select a specific record from a table, given a non-string id
var person = await db.Select<Person>(("person",
    new Guid("8424486b-85b3-4448-ac8d-5d51083391c7")));
```
