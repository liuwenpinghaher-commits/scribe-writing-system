---
title: "https://surrealdb.com/docs/reference/dotnet/core/logging"
url: "https://surrealdb.com/docs/reference/dotnet/core/logging"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/logging

Source: https://surrealdb.com/docs/reference/dotnet/core/logging

Logging is an important part of any application to understand what is happening. The .NET SDK supports the built-in logging API offered by the `Microsoft.Extensions.Logging` NuGet package.
##  Logging categories[](https://surrealdb.com/docs/reference/dotnet/core/logging#logging-categories)
The SurrealDB SDK for .NET has a set of logging categories so that you can pick what you want to display, using the respective `LogLevel`.
Example:

```json
{
  "Logging": {
    "LogLevel": {
      "SurrealDB.Connection": "Information",
      "SurrealDB.Method": "Information",
      "SurrealDB.Query": "Information",
      "SurrealDB.Serialization": "Debug"
    }
  }
}
```

This example will enable the following logging features:
  * •
`Connection` - Logger category for messages related to connection operations.
  * •
`Method` - Logger category for method execution, excluding `Connect` method.
  * •
`Query` - Logger category for messages related to written or generated queries, that can be executed within `Query` or `RawQuery`.
  * •
`Serialization` - Logger category for data serialization and deserialization, e.g. hexa CBOR format exchanged between the client and a SurrealDB instance.

Important
`Serialization` logs are only displayed when on `Debug` level to prevent data exchanges exposure. Please be sure to only enable this feature when you can guarantee that no sensitive data will be exposed.
Note
`Serialization` logs display data in a CBOR format. You might need to find tools that parses CBOR data and displays it in a more human way.
##  Sensitive data[](https://surrealdb.com/docs/reference/dotnet/core/logging#sensitive-data)
To prevent data leakage, the property `SensitiveDataLoggingEnabled` of `SurrealDbLoggingOptions` is set to `true` by default.
When the feature is enabled, any data that is passed to a SurrealDB method is replaced by the placeholder value `?`. Example:
If needed, you can override this option using the `EnableSensitiveDataLogging` when building a new `SurrealDbOptions` instance.

```csharp
services.AddSurreal(
  SurrealDbOptions
    .Create()
    .FromConnectionString(configuration.GetConnectionString("SurrealDB")!)
    .EnableSensitiveDataLogging(false)
    .Build()
);
```

Important
Please be sure to only enable this feature when you can guarantee that no sensitive data will be exposed.
