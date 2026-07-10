---
title: "https://surrealdb.com/docs/reference/dotnet/embedding"
url: "https://surrealdb.com/docs/reference/dotnet/embedding"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/embedding

Source: https://surrealdb.com/docs/reference/dotnet/embedding

SurrealDB is designed to be run in many different ways and in many environments.  
Due to the [separation of the storage and compute](https://surrealdb.com/docs/architecture) layers, SurrealDB can be run in embedded mode, from within a number of different language environments.  
In .NET, SurrealDB can be run as an [in-memory database](https://surrealdb.com/docs/reference/dotnet/embedding#memory-provider), or it can persist data using a [file-based storage engine](https://surrealdb.com/docs/reference/dotnet/embedding#file-providers). 
##  Memory provider[](https://surrealdb.com/docs/reference/dotnet/embedding#memory-provider)
The memory provider is a simple in-memory database that is useful in some contexts.  
It can be extremely useful for testing scenarios, or for small applications that do not require persistence.

```bash
dotnet add package SurrealDb.Embedded.InMemory
```

###  Consume the provider as is[](https://surrealdb.com/docs/reference/dotnet/embedding#consume-the-provider-as-is)
The simplest way to use an in-memory database instance of SurrealDB is to create an instance of the `SurrealDbMemoryClient` class.

```csharp
// highlight-next-line
using var db = new SurrealDbMemoryClient();

const string TABLE = "person";

var person = new Person
{
    Title = "Founder & CEO",
    Name = new() { FirstName = "Tobie", LastName = "Morgan Hitchcock" },
    Marketing = true
};
var created = await db.Create(TABLE, person);
Console.WriteLine(ToJsonString(created));
```

###  Consume the provider via dependency injection[](https://surrealdb.com/docs/reference/dotnet/embedding#consume-the-provider-via-dependency-injection)
Following the .NET Dependency Injection pattern, you can register the in-memory provider using the `AddInMemoryProvider` extension method.  
This will allow the `SurrealDbClient` to resolve the `mem://` endpoint.

```csharp
var builder = WebApplication.CreateBuilder(args);

var services = builder.Services;
var configuration = builder.Configuration;

// highlight-start
services
  .AddSurreal("Endpoint=mem://")
  .AddInMemoryProvider();
// highlight-end
```

Learn more about [Dependency Injection with SurrealDB in .NET](https://surrealdb.com/docs/reference/dotnet/core/dependency-injection) in the SDK documentation.
Once the memory provider is configured, you can use the .NET SDK the same way you would with a remote database.  
Please refer to the [.NET client SDK](https://surrealdb.com/docs/reference/dotnet) documentation to get started with SurrealDB for .NET.
##  File providers[](https://surrealdb.com/docs/reference/dotnet/embedding#file-providers)
The file provider is a more advanced storage engine that can be used to persist data to disk.
RocksDBSurrealKV

```bash
dotnet add package SurrealDb.Embedded.RocksDb
```

```bash
dotnet add package SurrealDb.Embedded.SurrealKv
```

###  Consume the provider as is[](https://surrealdb.com/docs/reference/dotnet/embedding#consume-the-provider-as-is-1)
RocksDBSurrealKV
The simplest way to use a file-backed database instance of SurrealDB is to create an instance of the `SurrealDbRocksDbClient` class.  
Note that the `path` to the storage is mandatory.

```csharp
// highlight-next-line
using var db = new SurrealDbRocksDbClient("data.db");

const string TABLE = "person";

var person = new Person
{
    Title = "Founder & CEO",
    Name = new() { FirstName = "Tobie", LastName = "Morgan Hitchcock" },
    Marketing = true
};
var created = await db.Create(TABLE, person);
Console.WriteLine(ToJsonString(created));
```

The simplest way to use a file-backed database instance of SurrealDB is to create an instance of the `SurrealDbKvClient` class.  
Note that the `path` to the storage is mandatory.

```csharp
// highlight-next-line
using var db = new SurrealDbKvClient("data.db");

const string TABLE = "person";

var person = new Person
{
    Title = "Founder & CEO",
    Name = new() { FirstName = "Tobie", LastName = "Morgan Hitchcock" },
    Marketing = true
};
var created = await db.Create(TABLE, person);
Console.WriteLine(ToJsonString(created));
```

###  Consume the provider via dependency injection[](https://surrealdb.com/docs/reference/dotnet/embedding#consume-the-provider-via-dependency-injection-1)
RocksDBSurrealKV
Following the .NET Dependency Injection pattern, you can register the file provider using the `AddRocksDbProvider` extension method.  
This will allow the `SurrealDbClient` to resolve the `rocksdb://` endpoint.

```csharp
var builder = WebApplication.CreateBuilder(args);

var services = builder.Services;
var configuration = builder.Configuration;

// highlight-start
services
  .AddSurreal("Endpoint=rocksdb://data.db")
  .AddRocksDbProvider();
// highlight-end
```

Following the .NET Dependency Injection pattern, you can register the file provider using the `AddSurrealKvProvider` extension method.  
This will allow the `SurrealDbClient` to resolve the `surrealkv://` endpoint.

```csharp
var builder = WebApplication.CreateBuilder(args);

var services = builder.Services;
var configuration = builder.Configuration;

// highlight-start
services
  .AddSurreal("Endpoint=surrealkv://data.db")
  .AddSurrealKvProvider();
// highlight-end
```

Learn more about [Dependency Injection with SurrealDB in .NET](https://surrealdb.com/docs/reference/dotnet/core/dependency-injection) in the SDK documentation.
###  Next step[](https://surrealdb.com/docs/reference/dotnet/embedding#next-step)
Once the file provider is configured, you can use the .NET SDK the same way you would with a remote database.  
Please refer to the [.NET client SDK](https://surrealdb.com/docs/reference/dotnet) documentation to get started.
