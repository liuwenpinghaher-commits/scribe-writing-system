---
title: "https://surrealdb.com/docs/reference/dotnet/methods/export"
url: "https://surrealdb.com/docs/reference/dotnet/methods/export"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/export

Source: https://surrealdb.com/docs/reference/dotnet/methods/export

Export the database as a SurrealQL script.  
To use this method, you need to be connected to a SurrealDB instance that is version `>= 2.1.0`.
Method Syntax

```csharp
await db.Export(options)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/export#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `options`  | Export configuration options.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/export#example-usage)
Only exporting db functions in a schema variable

```csharp
var options = new ExportOptions
{
    Users = false,
    Accesses = false,
    Params = false,
    Functions = true,
    Users = false,
    Versions = false,
    Tables = false,
    Records = false,
};

string schema = await db.Export(options);
```
