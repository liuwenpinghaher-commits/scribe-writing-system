---
title: "https://surrealdb.com/docs/reference/dotnet/methods/import"
url: "https://surrealdb.com/docs/reference/dotnet/methods/import"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/import

Source: https://surrealdb.com/docs/reference/dotnet/methods/import

Imports data into a SurrealDB database.  
To use this method, you need to be connected to a SurrealDB instance that is version `>= 2.0.0`.
Method Syntax

```csharp
await db.Import(string)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/import#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `input`  | The SurrealQL script used to import data in the database.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/import#example-usage)

```csharp
string input = 
        """
        DEFINE TABLE foo SCHEMALESS;
        DEFINE TABLE bar SCHEMALESS;
        CREATE foo:1 CONTENT { hello: "world" };
        CREATE bar:1 CONTENT { hello: "world" };
        DEFINE FUNCTION fn::foo() {
            RETURN "bar";
        };
        """;

await db.Import(input);
```
