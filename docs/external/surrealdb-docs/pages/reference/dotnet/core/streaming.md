---
title: "https://surrealdb.com/docs/reference/dotnet/core/streaming"
url: "https://surrealdb.com/docs/reference/dotnet/core/streaming"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/streaming

Source: https://surrealdb.com/docs/reference/dotnet/core/streaming

You can use the SurrealDB SDK to create live queries that listen for changes in the database and automatically update your application when changes occur.  
This feature is useful for building real-time applications that need to respond to changes in the database.  
| Method  | Description  |  
| --- | --- |  
| [` db.ListenLive(queryUuid) `](https://surrealdb.com/docs/reference/dotnet/core/streaming#listen-live)  | Listen responses from an existing live query  |  
| [` db.LiveQuery(sql) `](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-query)  | Initiate a live query from a SurrealQL statement  |  
| [` db.LiveRawQuery(sql, params) `](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-raw-query)  | Initiate a live query from a SurrealQL statement, based on a raw SurrealQL query  |  
| [` db.LiveTable(table, diff) `](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-table)  | Initiate a live query from a table  |  
| [` db.Kill(queryUuid) `](https://surrealdb.com/docs/reference/dotnet/core/streaming#kill)  | Kills a running live query by it's UUID  |  
##  `.ListenLive<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#listen-live)
Listen responses from an existing live query.
Method Syntax

```csharp
db.ListenLive<T>(queryUuid)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `queryUuid`  | The UUID of the live query to consume.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage)

```csharp
await using var liveQuery = db.ListenLive<Person>(queryUuid);

// Consume the live query...
```

You can then consume the live query using either an `IAsyncEnumerable` or an `Observable`.
####  Using an `IAsyncEnumerable`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#using-an-iasyncenumerable)
:::note   
_**NOTE:**_ This will block the current thread until the query is killed.  
:::
Option 1: Consume the live query via an IAsyncEnumerable

```csharp
await foreach (var response in liveQuery)
{
    // Either an Open, Create, Update, Delete or Close notification...

    if (response is SurrealDbLiveQueryOpenResponse)
    {
        // Do something...
    }
    if (response is SurrealDbLiveQueryCreateResponse<Person> create)
    {
        // Use the `Result` record
    }
    if (response is SurrealDbLiveQueryUpdateResponse<Person> update)
    {
        // Use the `Result` record
    }
    if (response is SurrealDbLiveQueryDeleteResponse<Person> delete)
    {
        // Use the `Result` record
    }
    if (response is SurrealDbLiveQueryCloseResponse)
    {
        // Do something...
    }
}
```

####  Using an `Observable`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#using-an-observable)
Option 2: Consume the live query via an Observable

```csharp
liveQuery
    .ToObservable()
    .Subscribe((response) => 
    {
        // Either an Open, Create, Update, Delete or Close notification...

        if (response is SurrealDbLiveQueryOpenResponse)
        {
            // Do something...
        }
        if (response is SurrealDbLiveQueryCreateResponse<Person> create)
        {
            // Use the `Result` record
        }
        if (response is SurrealDbLiveQueryUpdateResponse<Person> update)
        {
            // Use the `Result` record
        }
        if (response is SurrealDbLiveQueryDeleteResponse<Person> delete)
        {
            // Use the `Result` record
        }
        if (response is SurrealDbLiveQueryCloseResponse)
        {
            // Do something...
        }
    });
```

You can also use the `OfType` operator to filter the responses.

```csharp
liveQuery
    .ToObservable()
    .OfType<SurrealDbLiveQueryCreateResponse<Person>>()
    .Select(response => response.Result)
    .Subscribe((record) => 
    {
        // Use the created record
    });
```

Note that this pattern is already simplified via methods available on the `SurrealDbLiveQuery` object.  
You can learn more about these methods in the [LiveQuery methods](https://surrealdb.com/docs/reference/dotnet/core/streaming#surrealdblivequery-methods) section.
  

##  `.LiveQuery<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-query)
Initiate a live query from a SurrealQL statement.
Method Syntax

```csharp
await db.LiveQuery<T>(sql)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage-1)

```csharp
const string table = "person"; 
await using var liveQuery = await db.LiveQuery<Person>($"LIVE SELECT * FROM type::table({table});");

// Consume the live query...
```

###  `SurrealDbLiveQuery` methods[](https://surrealdb.com/docs/reference/dotnet/core/streaming#surrealdblivequery-methods)
The `SurrealDbLiveQuery` object provides the following methods:
####  `GetResults()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#get-results)
Returns an enumerator that iterates asynchronously through the collection of results  
(all actions `CREATE`, `UPDATE` and `DELETE`, except `OPEN` and `CLOSE`).
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments-2)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage-2)

```csharp
await using var liveQuery = await db.LiveRawQuery<Person>("LIVE SELECT * FROM person;");

// highlight-next-line
await foreach (var response in liveQuery.GetResults())
{
    // Either a Create, Update or Delete notification...

    if (response is SurrealDbLiveQueryCreateResponse<Person> create)
    {
        // Use the `Result` record
    }
    if (response is SurrealDbLiveQueryUpdateResponse<Person> update)
    {
        // Use the `Result` record
    }
    if (response is SurrealDbLiveQueryDeleteResponse<Person> delete)
    {
        // Use the `Result` record
    }
}
```

####  `GetCreatedRecords()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#get-created-records)
Returns an enumerator that iterates asynchronously through the collection of created records.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments-3)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage-3)

```csharp
await using var liveQuery = await db.LiveRawQuery<Person>("LIVE SELECT * FROM person;");

// highlight-next-line
await foreach (var record in liveQuery.GetCreatedRecords())
{
    // Use the created record
}
```

####  `GetUpdatedRecords()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#get-updated-records)
Returns an enumerator that iterates asynchronously through the collection of updated records.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments-4)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage-4)

```csharp
await using var liveQuery = await db.LiveRawQuery<Person>("LIVE SELECT * FROM person;");

// highlight-next-line
await foreach (var record in liveQuery.GetUpdatedRecords())
{
    // Use the updated record
}
```

####  `GetDeletedRecords()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#get-deleted-records)
Returns an enumerator that iterates asynchronously through the collection of deleted records.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments-5)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage-5)

```csharp
await using var liveQuery = await db.LiveRawQuery<Person>("LIVE SELECT * FROM person;");

// highlight-next-line
await foreach (var record in liveQuery.GetDeletedRecords())
{
    // Use the deleted record
}
```

####  `KillAsync()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#kill-async)
Kills the underlying live query.
Method Syntax

```csharp
await liveQuery.KillAsync(cancellationToken)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments-6)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage-6)

```csharp
var liveQuery = await db.LiveRawQuery<Person>("LIVE SELECT * FROM person;");

// Consume the live query...

// Manually kill the live query
// highlight-next-line
await liveQuery.KillAsync();
```

  

##  `.LiveRawQuery<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-raw-query)
Initiate a live query from a SurrealQL statement, based on a raw SurrealQL query.
Method Syntax

```csharp
await db.LiveRawQuery<T>(sql, params)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments-7)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `params`  | Assigns variables which can be used in the query.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage-7)

```csharp
await using var liveQuery = await db.LiveRawQuery<Person>("LIVE SELECT * FROM person;");

// Consume the live query...
```

  

##  `.LiveTable<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-table)
Initiate a live query from a table.
Method Syntax

```csharp
await db.LiveTable<T>(table, diff)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments-8)  
| Arguments  | Description  |  
| --- | --- |  
| `table`  | The table name to listen for changes for.  |  
| `diff`  | If set to true, live notifications will include an array of JSON Patch objects, rather than the entire record for each notification.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage-8)

```csharp
await using var liveQuery = await db.LiveTable<Person>("person");

// Consume the live query...
```

  

##  `.Kill()`[](https://surrealdb.com/docs/reference/dotnet/core/streaming#kill)
Kills a running live query by it's UUID.
Method Syntax

```csharp
await db.Kill(queryUuid)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/streaming#arguments-9)  
| Arguments  | Description  |  
| --- | --- |  
| `queryUuid`  | The UUID of the live query you wish to kill.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/streaming#example-usage-9)

```csharp
await db.Kill(queryUuid);
```

  

##  Live actions[](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-actions)
A live query event can be one of the following:  
| Action  | Result  | Description  |  
| --- | --- | --- |  
| `OPEN`  | N/A  | Emitted when the live query is opened in the server.  |  
| `CLOSE`  | `SocketClosed` or `QueryKilled`  | Emitted when the live query is closed due to it either being killed or the connection being disconnected.  |  
| `CREATE`  | `Result`  | Emitted when a record within your subscription gets created  |  
| `UPDATE`  | `Result`  | Emitted when a record within your subscription gets updated  |  
| `CREATE`  | `Result`  | Emitted when a record within your subscription gets deleted  |
