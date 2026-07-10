---
title: "https://surrealdb.com/docs/reference/dotnet/methods/query"
url: "https://surrealdb.com/docs/reference/dotnet/methods/query"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/query

Source: https://surrealdb.com/docs/reference/dotnet/methods/query

Runs a set of SurrealQL statements against the database.
Method Syntax

```csharp
await db.Query(sql)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/query#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/query#example-usage)

```csharp
// Execute query with params
const string table = "person";
var result = await db.Query($"CREATE person; SELECT * FROM type::table({table});");

// Get the first result from the first query
var created = result.GetValue<Person>(0);

// Get all of the results from the second query
var people = result.GetValue<List<Person>>(1);
```
