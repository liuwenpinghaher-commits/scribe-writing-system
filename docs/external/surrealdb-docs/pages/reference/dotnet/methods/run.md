---
title: "https://surrealdb.com/docs/reference/dotnet/methods/run"
url: "https://surrealdb.com/docs/reference/dotnet/methods/run"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/run

Source: https://surrealdb.com/docs/reference/dotnet/methods/run

Runs a [SurrealQL function](https://surrealdb.com/docs/reference/query-language/functions/database-functions).
Method Syntax

```csharp
await db.Run(name, version, args)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/run#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `name`  | The name of the [SurrealQL function](https://surrealdb.com/docs/reference/query-language/functions/database-functions).  |  
| `version`  | The version of the [SurrealQL function](https://surrealdb.com/docs/reference/query-language/functions/database-functions).  |  
| `args`  | The arguments used by the [SurrealQL function](https://surrealdb.com/docs/reference/query-language/functions/database-functions).  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/run#example-usage)

```csharp
DateTime now = await db.Run<DateTime>("time::now");

string result = await db.Run<string>("string::repeat", ["test", 3]);
```
