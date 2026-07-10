---
title: "https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql"
url: "https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql

Source: https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql

The methods below are used to interact with the database and perform CRUD operations. You can also use the `query` method to run [SurrealQL statements](https://surrealdb.com/docs/reference/query-language/statements/overview) against the database.  
| Method  | Description  |  
| --- | --- |  
| [` db.Query() `](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql#query)  | Runs a set of SurrealQL statements against the database  |  
| [` db.RawQuery() `](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql#raw_query)  | Runs a set of SurrealQL statements against the database, based on a raw SurrealQL query  |  
##  `.Query()`[](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql#query)
Runs a set of SurrealQL statements against the database.
Method Syntax

```csharp
await db.Query(sql)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql#example-usage)

```csharp
// Execute query with params
const string table = "person";
var result = await db.Query($"CREATE person; SELECT * FROM type::table({table});");

// Get the first result from the first query
var created = result.GetValue<Person>(0);

// Get all of the results from the second query
var people = result.GetValue<List<Person>>(1);
```

  

##  `.RawQuery()`[](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql#raw_query)
Runs a set of SurrealQL statements against the database, based on a raw SurrealQL query.
Method Syntax

```csharp
await db.RawQuery(sql, params)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql#arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `params`  | Assigns variables which can be used in the query.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql#example-usage-1)

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
