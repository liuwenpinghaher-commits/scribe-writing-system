---
title: "https://surrealdb.com/docs/reference/python/concepts/embedded-databases"
url: "https://surrealdb.com/docs/reference/python/concepts/embedded-databases"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/concepts/embedded-databases

Source: https://surrealdb.com/docs/reference/python/concepts/embedded-databases

The Python SDK can run SurrealDB directly within your application process, eliminating the need for a separate server. Embedded databases are useful for testing, development, desktop applications, and scenarios where a standalone database server is impractical.
To use an embedded database, pass a `mem://`, `file://`, or `surrealkv://` URL to the `Surreal` or `AsyncSurreal` factory function.
##  API references[](https://surrealdb.com/docs/reference/python/concepts/embedded-databases#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`Surreal(url)`](https://surrealdb.com/docs/reference/python/api/core/surreal#surreal)  | Creates a synchronous embedded connection based on the URL scheme  |  
| [`AsyncSurreal(url)`](https://surrealdb.com/docs/reference/python/api/core/surreal#surreal)  | Creates an asynchronous embedded connection based on the URL scheme  |  
##  Connection URL schemes[](https://surrealdb.com/docs/reference/python/concepts/embedded-databases#connection-url-schemes)
The URL scheme determines whether the embedded database stores data in memory or on disk.  
| Scheme  | Storage  | Persistence  |  
| --- | --- | --- |  
| `mem://`  | In-memory  | Data is lost when the process exits  |  
| `file://path`  | On-disk (SurrealKV)  | Data persists to the specified directory  |  
| `surrealkv://path`  | On-disk (SurrealKV)  | Data persists to the specified directory  |  
See the [UrlScheme](https://surrealdb.com/docs/reference/python/api/types/#urlscheme) type reference for the full list of supported schemes.
##  In-memory databases[](https://surrealdb.com/docs/reference/python/concepts/embedded-databases#in-memory-databases)
An in-memory database runs entirely in RAM and does not persist data between process restarts. This is well suited for unit tests, temporary workloads, and prototyping where durability is not required.
SynchronousAsynchronous

```python
from surrealdb import Surreal

with Surreal("mem://") as db:
    db.use("main", "main")
    db.signin({"username": "root", "password": "root"})
    db.create("users", {"name": "Alice", "age": 30})
    print(db.select("users"))
```

```python
from surrealdb import AsyncSurreal

async with AsyncSurreal("mem://") as db:
    await db.use("main", "main")
    await db.signin({"username": "root", "password": "root"})
    await db.create("users", {"name": "Alice", "age": 30})
    print(await db.select("users"))
```

Each `mem://` connection creates an independent database instance. Data is not shared between separate connections.
##  Persistent databases[](https://surrealdb.com/docs/reference/python/concepts/embedded-databases#persistent-databases)
The `file://` and `surrealkv://` schemes persist data to a directory on disk. This is useful for desktop applications, local-first architectures, and development workflows where you want data to survive restarts.
SynchronousAsynchronous

```python
from surrealdb import Surreal

with Surreal("surrealkv://data/mydb") as db:
    db.use("app", "main")
    db.signin({"username": "root", "password": "root"})
    db.create("settings", {"theme": "dark", "lang": "en"})
```

```python
from surrealdb import AsyncSurreal

async with AsyncSurreal("file://data/mydb") as db:
    await db.use("app", "main")
    await db.signin({"username": "root", "password": "root"})
    await db.create("settings", {"theme": "dark", "lang": "en"})
```

The path is relative to the working directory of your process. Use an absolute path for a fixed location on disk.
##  Feature limitations[](https://surrealdb.com/docs/reference/python/concepts/embedded-databases#feature-limitations)
Embedded connections do not support the full set of features available with WebSocket or HTTP connections. Attempting to use an unsupported feature raises an [`UnsupportedFeatureError`](https://surrealdb.com/docs/reference/python/api/errors/#unsupportedfeatureerror).
The following features are **not available** with embedded connections:
  * •
**Sessions** : `.new_session()` is not supported
  * •
**Transactions** : `.new_transaction()` is not supported
  * •
**Live queries** : `.live()` and `.subscribe_live()` are not supported

Note
If your application requires sessions, transactions, or live queries, use a WebSocket connection (`ws://` or `wss://`) instead.
All other operations — queries, CRUD methods, authentication, and parameter binding — work as expected with embedded connections.
##  Learn more[](https://surrealdb.com/docs/reference/python/concepts/embedded-databases#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/python/api/core/surreal) for complete method signatures and parameters
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb) for an overview of all connection protocols
  * •
[UrlScheme type reference](https://surrealdb.com/docs/reference/python/api/types/#urlscheme) for the full list of URL schemes
