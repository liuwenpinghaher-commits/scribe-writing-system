---
title: "https://surrealdb.com/docs/reference/dotnet/methods/listen_live"
url: "https://surrealdb.com/docs/reference/dotnet/methods/listen_live"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods/listen_live

Source: https://surrealdb.com/docs/reference/dotnet/methods/listen_live

Listen responses from an existing live query.
Method Syntax

```csharp
db.ListenLive<T>(queryUuid)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/methods/listen_live#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `queryUuid`  | The UUID of the live query to consume.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/methods/listen_live#example-usage)

```csharp
await using var liveQuery = db.ListenLive<Person>(queryUuid);

// Consume the live query...
```
