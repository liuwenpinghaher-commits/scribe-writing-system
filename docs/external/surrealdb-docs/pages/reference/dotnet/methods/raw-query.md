---
title: "https://surrealdb.com/docs/reference/dotnet/methods/raw-query"
url: "https://surrealdb.com/docs/reference/dotnet/methods/raw-query"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/raw-query

Source: https://surrealdb.com/docs/reference/dotnet/methods/raw-query

Runs a set of SurrealQL statements against the database, based on a raw SurrealQL query.
Method Syntax

```csharp
await db.RawQuery(sql, params)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/raw-query#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `params`  | Assigns variables which can be used in the query.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/raw-query#example-usage)

```csharp
// Assign the variable on the connection
var @params = new Dictionary<string, object> { { "table",
    "person" } };
var result = await db.RawQuery("CREATE person; SELECT * FROM type::table($table);", @params);

// Get the first result from the first query
var created = result.GetValue<Person>(0);

// Get all of the results from the second query
var people = result.GetValue<List<Person>>(1);
```
