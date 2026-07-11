---
title: "https://surrealdb.com/docs/languages/dotnet"
url: "https://surrealdb.com/docs/languages/dotnet"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/languages/dotnet

Source: https://surrealdb.com/docs/languages/dotnet

The .NET SDK for SurrealDB lets you connect to a database and query it from your application. This guide covers connecting, authenticating, and running your first queries.
##  1. Install the SDK[](https://surrealdb.com/docs/languages/dotnet#1-install-the-sdk)
Follow the [installation guide](https://surrealdb.com/docs/reference/dotnet/installation) to add the SDK to your project. From the .NET CLI, add the `SurrealDb.Net` package:

```bash
dotnet add package SurrealDb.Net
```

Once installed, import the SDK and its models namespaces.

```csharp
using SurrealDb.Net;
using SurrealDb.Net.Models;
using SurrealDb.Net.Models.Auth;
```

The `SurrealDb.Net` namespace contains the `SurrealDbClient`, while `SurrealDb.Net.Models` and `SurrealDb.Net.Models.Auth` provide the record base types and authentication types like [`RootAuth`](https://surrealdb.com/docs/reference/dotnet/core/authentication).
##  2. Connect to SurrealDB[](https://surrealdb.com/docs/languages/dotnet#2-connect-to-surrealdb)
Create a new [`SurrealDbClient`](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection) with a connection string. The URL scheme determines the connection type.
Supported connection protocols include:
  * •
**WebSocket** (`ws://`, `wss://`) for long-lived stateful connections, required for live queries, sessions, and transactions
  * •
**HTTP** (`http://`, `https://`) for short-lived stateless connections
  * •
**Memory** (`mem://`) for [embedded instances](https://surrealdb.com/docs/reference/dotnet/embedding)

```csharp
using var db = new SurrealDbClient("ws://127.0.0.1:8000/rpc");
```

After connecting, use [`.SignIn()`](https://surrealdb.com/docs/reference/dotnet/methods/signin) to authenticate and [`.Use()`](https://surrealdb.com/docs/reference/dotnet/methods/use) to select the namespace and database you want to work with. Most operations require both.

```csharp
await db.SignIn(new RootAuth { Username = "root", Password = "secret" });
await db.Use("main", "main");
```

##  3. Inserting data into SurrealDB[](https://surrealdb.com/docs/languages/dotnet#3-inserting-data-into-surrealdb)
Once connected, you can use the [`Create`](https://surrealdb.com/docs/reference/dotnet/methods/create) method to create records. Define a class that derives from `Record` to map to your table, then pass an instance to `Create`.

```csharp
const string TABLE = "person";

var person = new Person
{
    Title = "Founder & CEO",
    Name = new() { FirstName = "Tobie", LastName = "Morgan Hitchcock" },
    Marketing = true
};
var created = await db.Create(TABLE, person);
Console.WriteLine(created);
```

The `Person` and `Name` classes describe the shape of your data. `Person` derives from `Record`, which provides the record `Id`.

```csharp
public class Person : Record
{
    public string? Title { get; set; }
    public Name? Name { get; set; }
    public bool Marketing { get; set; }
}
public class Name
{
    public string? FirstName { get; set; }
    public string? LastName { get; set; }
}
```

##  4. Retrieving data from SurrealDB[](https://surrealdb.com/docs/languages/dotnet#4-retrieving-data-from-surrealdb)
###  Selecting records[](https://surrealdb.com/docs/languages/dotnet#selecting-records)
The [`Select`](https://surrealdb.com/docs/reference/dotnet/methods/select) method retrieves all records from a table. Provide the type parameter to tell the SDK what type to deserialize the response into.

```csharp
var people = await db.Select<Person>(TABLE);
Console.WriteLine(people);
```

###  Running SurrealQL queries[](https://surrealdb.com/docs/languages/dotnet#running-surrealql-queries)
For more advanced use cases, you can use the [`Query`](https://surrealdb.com/docs/reference/dotnet/methods/query) method to run [SurrealQL](https://surrealdb.com/docs/reference/query-language) statements directly. Use [`GetValue<>`](https://surrealdb.com/docs/reference/dotnet/core/writing-surrealql) to extract a typed result from the response.

```csharp
var queryResponse = await db.Query(
  $"SELECT Marketing, count() AS Count FROM type::table({TABLE}) GROUP BY Marketing"
);
var groups = queryResponse.GetValue<List<Group>>(0);
Console.WriteLine(groups);

public class Group
{
    public bool Marketing { get; set; }
    public int Count { get; set; }
}
```

##  5. Closing the connection[](https://surrealdb.com/docs/languages/dotnet#5-closing-the-connection)
When you create the client with `using var db = ...`, the client is disposed automatically when it goes out of scope, releasing the connection and its resources. If you need to close it explicitly, call `Dispose()`.

```csharp
db.Dispose();
```

##  Next steps[](https://surrealdb.com/docs/languages/dotnet#next-steps)
You have learned how to install the SDK, connect to SurrealDB, create records, and retrieve data. There is a lot more you can do with the SDK, including updating and deleting records, authentication, live queries, and transactions.
[Connection management Learn how to create and configure a SurrealDbClient connection.](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection)[Authentication Read more about authentication levels and how to integrate them into your application.](https://surrealdb.com/docs/reference/dotnet/core/authentication)[Data manipulation Learn how to create, read, update, and delete records using the SDK.](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation)[API Reference Complete reference for all methods, types, and errors.](https://surrealdb.com/docs/reference/dotnet/methods)
Note
This getting-started guide covers the essentials. For the complete methods, API, and concept reference, see the [.NET SDK reference](https://surrealdb.com/docs/reference/dotnet).
