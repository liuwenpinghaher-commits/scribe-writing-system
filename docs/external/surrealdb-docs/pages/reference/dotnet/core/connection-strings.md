---
title: "https://surrealdb.com/docs/reference/dotnet/core/connection-strings"
url: "https://surrealdb.com/docs/reference/dotnet/core/connection-strings"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/connection-strings

Source: https://surrealdb.com/docs/reference/dotnet/core/connection-strings

Connection Strings are an easy way to configure your application to connect to a SurrealDB instance.  
They are stored in the `appsettings.json` file and can be used to configure the `SurrealDbClient`.
In general, it is known as a best practice to:
  * •
set a development Connection String in `appsettings.Development.json`,
  * •
store your production Connection String in a Secret environment variable, or even better in a Vault.

  
| Keys  | Description  | Aliases  |  
| --- | --- | --- |  
| `Endpoint`  |  The database endpoint to connect to. The disctinction between `Server`and `Client`can  
help you ensure you only call a distant database (server mode) or a  
local database (client mode).  |  `Server``Client`  |  
| `Namespace`  | Switches to a specific namespace.  | `NS`  |  
| `Database`  | Switches to a specific database.  | `DB`  |  
| `Username`  | Username used to have root access.  | `User`  |  
| `Password`  | Password used to have root access.  | `Pass`  |  
| `Token`  | Token (JWT) used to have user access.  |   |  
| `AuthLevel`  |  Auth level when connecting to the SurrealDB instance. Valid options are `Root`, `Namespace`or{" "} `Database`. Defaults to `Root`.  |   |  
##  Examples[](https://surrealdb.com/docs/reference/dotnet/core/connection-strings#examples)
Here is a couple of examples of Connection Strings:

```sh
Server=http://127.0.0.1:8000;Namespace=test;Database=test;Username=root;Password=root
```

```sh
Endpoint=http://127.0.0.1:8000;NS=test;DB=test;User=root;Pass=root
```

```sh
Server=ws://127.0.0.1:8000;AuthLevel=Namespace;NS=test;DB=test;User=root;Pass=root
```

```sh
Client=mem://;Namespace=test;Database=test
```
